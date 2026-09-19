from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Any, Mapping, Sequence


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
    pending_principal_keys = remaining.intersection(principal_keys)
    if pending_principal_keys:
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
    """Refine a credential/metadata verdict with exact graph-context evidence.

    This function is deliberately monotone: graph context may discharge only
    unresolved graph constraints. It can never erase a credential failure such as
    expiry, revocation, audience/scope mismatch, approval, or MFA. This prevents a
    matching graph target from laundering an otherwise invalid credential into
    exercisable authority.
    """
    credential_ok, credential_reasons, unresolved = credential_verdict
    graph_ok, graph_reasons, remaining = graph_context_constraints_satisfied(
        constraints,
        source_ref=source_ref,
        target_ref=target_ref,
        source_subject=source_subject,
        target_subject=target_subject,
        unresolved=unresolved,
    )
    reasons = sorted({str(item) for item in credential_reasons} | set(graph_reasons))
    return bool(credential_ok and graph_ok), reasons, remaining


__all__ = ["graph_context_constraints_satisfied", "resolve_graph_context_verdict"]
