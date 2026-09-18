from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .authority import (
    AuthorityEvidenceClass,
    AuthorityRelationType,
    AuthoritySubjectKind,
    TestamurAuthorityStore,
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _strings(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        values = list(value)
    else:
        raise ValueError(f"{field} must be a string or sequence of strings")
    return sorted({_text(item, f"{field}[]") for item in values})


def _validated_capability(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one imported permission without inventing wildcard semantics.

    Provider connector payloads are an authority boundary. A capability must name an
    exact namespace/action pair; missing or blank fields are rejected at import time
    rather than merely becoming unusable later in reachability. Resource, when
    present, is textual, and constraints must be an object so provider conditions are
    retained verbatim for fail-closed attenuation.
    """
    item = dict(raw)
    item["namespace"] = _text(item.get("namespace"), "capability.namespace")
    item["action"] = _text(item.get("action"), "capability.action")
    if item.get("resource") is not None:
        item["resource"] = _text(item.get("resource"), "capability.resource")
    constraints = item.get("constraints")
    if constraints is None:
        item["constraints"] = {}
    elif isinstance(constraints, Mapping):
        item["constraints"] = dict(constraints)
    else:
        raise ValueError("capability.constraints must be an object")
    return item


def _validated_evidence_item(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one imported authority fact's exact evidence record.

    Callers are allowed to pass hand-built evidence dictionaries, so invariants must
    be enforced here rather than relying on use of exact_evidence(). In particular,
    DERIVED authority without analyzer identity/version is not reproducible evidence.
    """
    item = dict(raw)
    item["ref"] = _text(item.get("ref"), "evidence.ref")
    item["revision"] = _text(item.get("revision"), "evidence.revision")
    try:
        klass = AuthorityEvidenceClass(str(item.get("evidence_class"))).value
    except ValueError as exc:
        raise ValueError(
            "evidence.evidence_class must be OBSERVED, DERIVED, or DECLARED"
        ) from exc
    item["evidence_class"] = klass
    if klass == AuthorityEvidenceClass.DERIVED.value:
        item["analyzer"] = _text(item.get("analyzer"), "evidence.analyzer")
        item["analyzer_version"] = _text(
            item.get("analyzer_version"), "evidence.analyzer_version"
        )
    if item.get("observed_at") is not None:
        item["observed_at"] = _text(item.get("observed_at"), "evidence.observed_at")
    return item


def _exact_evidence_items(evidence: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Reject importer evidence that is not pinned to an exact source revision."""
    result = [_validated_evidence_item(raw) for raw in evidence]
    if not result:
        raise ValueError("imported authority facts require explicit exact evidence")
    return result


def exact_evidence(
    *,
    ref: str,
    evidence_class: str | AuthorityEvidenceClass,
    revision: str,
    analyzer: str | None = None,
    analyzer_version: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Build evidence suitable for imported authority facts.

    Importers must identify the exact provider/configuration revision they parsed.
    A provider URL or account name alone is not an exact evidence basis.
    """
    raw: dict[str, Any] = {
        "ref": ref,
        "evidence_class": str(evidence_class),
        "revision": revision,
    }
    if analyzer is not None:
        raw["analyzer"] = analyzer
    if analyzer_version is not None:
        raw["analyzer_version"] = analyzer_version
    if observed_at is not None:
        raw["observed_at"] = observed_at
    return _validated_evidence_item(raw)


def record_credential_observation(
    store: TestamurAuthorityStore,
    *,
    credential_ref: str,
    label: str,
    kind: str | AuthoritySubjectKind = AuthoritySubjectKind.TOKEN,
    issuer: str | None = None,
    principal: str | None = None,
    audience: Sequence[str] | str | None = None,
    scopes: Sequence[str] | str | None = None,
    expires_at: str | None = None,
    revocation_state: str | None = None,
    bindings: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Record a credential without treating possession as usability.

    Evidence is retained on the subject as import provenance. Authentication still
    requires an explicit evidence-bearing authority edge; this function never creates
    ACCEPTS_CREDENTIAL or CAN_AUTHENTICATE_AS from issuer/audience metadata.
    """
    ev = _validated_evidence_item(evidence)
    attributes: dict[str, Any] = {
        "audience": _strings(audience, "audience"),
        "scopes": _strings(scopes, "scopes"),
        "bindings": dict(bindings or {}),
    }
    for key, value in (
        ("issuer", issuer),
        ("principal", principal),
        ("expires_at", expires_at),
        ("revocation_state", revocation_state),
    ):
        if value is not None:
            attributes[key] = _text(value, key)
    return store.record_subject(
        kind,
        label=_text(label, "label"),
        subject_ref=_text(credential_ref, "credential_ref"),
        attributes=attributes,
        metadata={"import_evidence": ev},
    )


def record_credential_acceptance(
    store: TestamurAuthorityStore,
    *,
    service_ref: str,
    credential_ref: str,
    evidence: Iterable[Mapping[str, Any]],
    audience: Sequence[str] | str | None = None,
    required_scopes: Sequence[str] | str | None = None,
    constraints: Mapping[str, Any] | None = None,
    boundary_refs: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Record service-side acceptance of one exact credential.

    Audience/scope metadata on a token is never enough to manufacture this edge. The
    importer must have exact evidence for the service-side acceptance fact itself.
    """
    merged = dict(constraints or {})
    audiences = _strings(audience, "audience")
    scopes = _strings(required_scopes, "required_scopes")
    if audiences:
        merged["audience"] = audiences
    if scopes:
        merged["required_scopes"] = scopes
    return store.record_edge(
        _text(service_ref, "service_ref"),
        AuthorityRelationType.ACCEPTS_CREDENTIAL,
        _text(credential_ref, "credential_ref"),
        constraints=merged,
        evidence=_exact_evidence_items(evidence),
        boundary_refs=boundary_refs,
        metadata={"permission_source": "explicit_service_acceptance"},
    )


def record_authentication_authority(
    store: TestamurAuthorityStore,
    *,
    credential_ref: str,
    principal_ref: str,
    service_ref: str,
    evidence: Iterable[Mapping[str, Any]],
    audience: Sequence[str] | str | None = None,
    required_scopes: Sequence[str] | str | None = None,
    constraints: Mapping[str, Any] | None = None,
    boundary_refs: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Record an explicit credential -> principal authentication authority statement.

    service_ref is mandatory so reachability can require a separate
    ACCEPTS_CREDENTIAL fact for the same credential. This intentionally prevents
    issuer/audience/scope coincidence or graph adjacency from becoming authority.
    """
    merged = dict(constraints or {})
    merged["service_ref"] = _text(service_ref, "service_ref")
    audiences = _strings(audience, "audience")
    scopes = _strings(required_scopes, "required_scopes")
    if audiences:
        merged["audience"] = audiences
    if scopes:
        merged["required_scopes"] = scopes
    return store.record_edge(
        _text(credential_ref, "credential_ref"),
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        _text(principal_ref, "principal_ref"),
        constraints=merged,
        evidence=_exact_evidence_items(evidence),
        boundary_refs=boundary_refs,
        metadata={"permission_source": "explicit_authentication_authority"},
    )


def record_connector_delegation(
    store: TestamurAuthorityStore,
    *,
    delegator_ref: str,
    connector_ref: str,
    capabilities: Iterable[Mapping[str, Any]],
    evidence: Iterable[Mapping[str, Any]],
    constraints: Mapping[str, Any] | None = None,
    boundary_refs: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Record only the exact connector permission set actually delegated.

    Empty delegation is rejected instead of being interpreted as unrestricted access.
    Provider installation/adjacency therefore never becomes permission by connectivity.
    Every imported capability must also name an explicit namespace/action pair; malformed
    provider permission records are rejected rather than stored as wildcard-like data.
    """
    caps = [_validated_capability(item) for item in capabilities]
    if not caps:
        raise ValueError("connector delegation requires an explicit non-empty capability set")
    return store.record_edge(
        _text(delegator_ref, "delegator_ref"),
        AuthorityRelationType.DELEGATES,
        _text(connector_ref, "connector_ref"),
        capabilities=caps,
        constraints=dict(constraints or {}),
        evidence=_exact_evidence_items(evidence),
        boundary_refs=boundary_refs,
        metadata={"permission_source": "explicit_delegation"},
    )
