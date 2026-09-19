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

    Only typed aliases plus the canonical subject refs participate. Generic labels,
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
        if required and not required.intersection(target_resources):
            reasons.add("resource_mismatch")
        if required:
            remaining.discard("resource")

    if "resource_pattern" in remaining:
        patterns = _values(constraints.get("resource_pattern"))
        if patterns:
            if not any(fnmatchcase(value, pattern) for value in target_resources for pattern in patterns):
                reasons.add("resource_pattern_mismatch")
            remaining.discard("resource_pattern")

    principal_keys = ("principal", "principals", "principal_ref", "principal_refs")
    if remaining.intersection(principal_keys):
        required: set[str] = set()
        for key in principal_keys:
            required.update(_values(constraints.get(key)))
        if required and not required.intersection(source_principals):
            reasons.add("principal_mismatch")
        if required:
            remaining.difference_update(principal_keys)

    return not reasons and not remaining, sorted(reasons), sorted(remaining)


__all__ = ["graph_context_constraints_satisfied"]
