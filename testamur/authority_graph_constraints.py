from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Mapping, Sequence

from .authority_credentials import credential_constraints_satisfied


def _claim_values(value: Any) -> tuple[set[str], bool]:
    """Parse one exact graph claim without manufacturing strings from objects."""
    if value is None:
        return set(), True
    if isinstance(value, str):
        text = value.strip()
        return ({text}, True) if text else (set(), False)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        values: set[str] = set()
        if not value:
            return set(), False
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return set(), False
            values.add(item.strip())
        return values, bool(values)
    return set(), False


def _aliased_values(container: Mapping[str, Any], keys: tuple[str, ...]) -> tuple[set[str], bool]:
    """Treat aliases as alternate encodings, never additive authority grants."""
    observed: list[set[str]] = []
    for key in keys:
        if key not in container:
            continue
        values, valid = _claim_values(container.get(key))
        if not valid:
            return set(), False
        observed.append(values)
    if not observed:
        return set(), True
    first = observed[0]
    if any(values != first for values in observed[1:]):
        return set(), False
    return set(first), True


def _typed_subject_values(
    ref: str,
    subject: Mapping[str, Any],
    keys: tuple[str, ...],
) -> tuple[set[str], bool]:
    values = {str(ref).strip()} if str(ref).strip() else set()
    attributes = subject.get("attributes") if isinstance(subject.get("attributes"), Mapping) else {}
    for container in (subject, attributes):
        aliases, valid = _aliased_values(container, keys)
        if not valid:
            return values, False
        values.update(aliases)
    return values, True


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
    authorization evidence. Typed aliases are alternate encodings and must agree;
    malformed objects are never stringified into authority evidence. Runtime
    context remains unresolved until a caller supplies exact evidence for it.
    Connectivity never satisfies a permission constraint.
    """
    remaining = {str(item) for item in unresolved}
    reasons: set[str] = set()
    source = source_subject or {}
    target = target_subject or {}
    principal_keys = ("principal", "principals", "principal_ref", "principal_refs")
    resource_keys = ("resource", "resources", "resource_ref", "resource_refs")
    source_principals, source_valid = _typed_subject_values(source_ref, source, principal_keys)
    target_resources, target_valid = _typed_subject_values(target_ref, target, resource_keys)

    if not source_valid and remaining.intersection(principal_keys):
        reasons.add("principal_evidence_malformed_or_conflicting")
        remaining.difference_update(principal_keys)
    if not target_valid and remaining.intersection({"resource", "resource_pattern"}):
        reasons.add("resource_evidence_malformed_or_conflicting")
        remaining.difference_update({"resource", "resource_pattern"})

    if "resource" in remaining:
        required, valid = _claim_values(constraints.get("resource"))
        if not valid or not required:
            reasons.add("resource_constraint_malformed_or_missing")
        elif not required.intersection(target_resources):
            reasons.add("resource_mismatch")
        remaining.discard("resource")

    if "resource_pattern" in remaining:
        patterns, valid = _claim_values(constraints.get("resource_pattern"))
        if not valid or not patterns:
            reasons.add("resource_pattern_constraint_malformed_or_missing")
        elif not any(fnmatchcase(value, pattern) for value in target_resources for pattern in patterns):
            reasons.add("resource_pattern_mismatch")
        remaining.discard("resource_pattern")

    if remaining.intersection(principal_keys):
        required, valid = _aliased_values(constraints, principal_keys)
        if not valid or not required:
            reasons.add("principal_constraint_malformed_or_conflicting")
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

    ``attribute_ref`` selects whose credential metadata is evaluated (for example
    a credential accepted by a service). It never rewrites the traversed edge's
    source identity: principal/resource graph constraints are always proven from
    the exact source/target subjects on the authority edge.
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
        source_ref=source_ref,
        target_ref=target_ref,
        source_subject=source_subject,
        target_subject=target_subject,
    )


__all__ = [
    "evaluate_exact_edge_constraints",
    "graph_context_constraints_satisfied",
    "resolve_graph_context_verdict",
]
