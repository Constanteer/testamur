from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Mapping, Sequence

from .authority_credentials import credential_constraints_satisfied


def _values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        text = value.strip()
        return {text} if text else set()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return {str(item).strip() for item in value if str(item).strip()}
    text = str(value).strip()
    return {text} if text else set()


def _typed_subject_values(ref: str, subject: Mapping[str, Any], keys: tuple[str, ...]) -> set[str]:
    values = {str(ref).strip()} if str(ref).strip() else set()
    attributes = subject.get("attributes") if isinstance(subject.get("attributes"), Mapping) else {}
    for container in (subject, attributes):
        for key in keys:
            values.update(_values(container.get(key)))
    return values


def graph_context_constraints_satisfied(
    constraints: Mapping[str, Any],
    *,
    source_ref: str,
    target_ref: str,
    source_subject: Mapping[str, Any] | None = None,
    target_subject: Mapping[str, Any] | None = None,
    unresolved: Sequence[str] = (),
) -> tuple[bool, list[str], list[str]]:
    """Resolve constraints provable from the exact traversed authority edge.

    Only typed aliases plus canonical subject refs participate. Generic labels,
    names, or IDs are deliberately excluded: coincidental metadata must not become
    authorization evidence. Runtime context (IP/zone/device/session/time/provider
    conditions) remains unresolved until a caller supplies exact evidence for it.
    Connectivity never satisfies a permission constraint.
    """
    remaining = {str(item) for item in unresolved}
    reasons: set[str] = set()
    source = source_subject or {}
    target = target_subject or {}
    source_principals = _typed_subject_values(
        source_ref, source, ("principal", "principals", "principal_ref", "principal_refs")
    )
    target_resources = _typed_subject_values(
        target_ref, target, ("resource", "resources", "resource_ref", "resource_refs")
    )

    if "resource" in remaining:
        required = _values(constraints.get("resource"))
        if not required:
            reasons.add("resource_constraint_missing_value")
        elif not required.intersection(target_resources):
            reasons.add("resource_mismatch")
        remaining.discard("resource")

    if "resource_pattern" in remaining:
        patterns = _values(constraints.get("resource_pattern"))
        if not patterns:
            reasons.add("resource_pattern_constraint_missing_value")
        elif not any(fnmatchcase(value, pattern) for value in target_resources for pattern in patterns):
            reasons.add("resource_pattern_mismatch")
        remaining.discard("resource_pattern")

    principal_keys = ("principal", "principals", "principal_ref", "principal_refs")
    if remaining.intersection(principal_keys):
        required: set[str] = set()
        for key in principal_keys:
            required.update(_values(constraints.get(key)))
        if not required:
            reasons.add("principal_constraint_missing_value")
        elif not required.intersection(source_principals):
            reasons.add("principal_mismatch")
        remaining.difference_update(principal_keys)

    return not reasons and not remaining, sorted(reasons), sorted(remaining)


def resolve_graph_context_verdict(
    constraints: Mapping[str, Any],
    credential_verdict: tuple[bool, Sequence[str], Sequence[str]],
    *,
    source_ref: str,
    target_ref: str,
    source_subject: Mapping[str, Any] | None = None,
    target_subject: Mapping[str, Any] | None = None,
) -> tuple[bool, list[str], list[str]]:
    """Refine a metadata verdict using evidence from the exact traversed edge.

    Exact graph evidence may discharge unresolved graph-only gates, but failures
    already established by credential metadata are immutable. A matching target
    can therefore never launder expiry, revocation, audience/scope mismatch,
    approval, MFA, or another established failure into exercisable authority.
    """
    _credential_ok, credential_reasons, unresolved = credential_verdict
    _graph_ok, graph_reasons, remaining = graph_context_constraints_satisfied(
        constraints,
        source_ref=source_ref,
        target_ref=target_ref,
        source_subject=source_subject,
        target_subject=target_subject,
        unresolved=unresolved,
    )
    reasons = sorted({str(item) for item in credential_reasons} | set(graph_reasons))
    return not reasons and not remaining, reasons, remaining


def evaluate_exact_edge_constraints(
    edge: Mapping[str, Any],
    *,
    credential_attributes: Mapping[str, Any],
    source_subject: Mapping[str, Any] | None = None,
    target_subject: Mapping[str, Any] | None = None,
    attribute_ref: str | None = None,
    as_of: Any = None,
) -> tuple[bool, list[str], list[str]]:
    """Canonical two-stage constraint evaluation for one exact authority edge.

    Stage one evaluates credential/token metadata (audience, scope, issuer,
    tenant, validity and explicit runtime gates). Stage two may discharge only
    graph-context keys using the exact traversed source/target identities.
    No neighboring edge, material-lineage relation, or generic object metadata
    participates in authorization.
    """
    raw = edge.get("constraints")
    if raw is not None and not isinstance(raw, Mapping):
        return False, [], ["constraints"]
    constraints = dict(raw or {})
    source_ref = str(edge.get("source_ref") or "")
    target_ref = str(edge.get("target_ref") or "")
    verdict = credential_constraints_satisfied(
        credential_attributes,
        constraints,
        as_of=as_of,
    )
    return resolve_graph_context_verdict(
        constraints,
        verdict,
        source_ref=source_ref if attribute_ref is None else str(attribute_ref),
        target_ref=target_ref,
        source_subject=source_subject,
        target_subject=target_subject,
    )


__all__ = [
    "evaluate_exact_edge_constraints",
    "graph_context_constraints_satisfied",
    "resolve_graph_context_verdict",
]
