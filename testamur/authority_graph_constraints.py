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


def _subject_values(ref: str, subject: Mapping[str, Any]) -> set[str]:
    values = {str(ref).strip()} if str(ref).strip() else set()
    for container in (subject, subject.get("attributes") if isinstance(subject.get("attributes"), Mapping) else {}):
        for key in ("resource", "resource_ref", "principal", "principal_ref", "name", "id"):
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
    """Resolve constraints that can be proven from the exact traversed graph edge.

    This evaluator is deliberately narrow. It resolves only resource/principal
    constraints for which the traversal has an exact source/target subject. Runtime
    context such as source IP, network zone, device/session binding, time windows,
    and provider-specific conditions remains unresolved unless a future caller can
    supply evidence for it. Connectivity never satisfies a permission constraint.
    """
    remaining = set(str(item) for item in unresolved)
    reasons: set[str] = set()
    source = source_subject or {}
    target = target_subject or {}
    source_values = _subject_values(source_ref, source)
    target_values = _subject_values(target_ref, target)

    if "resource" in remaining:
        required = _values(constraints.get("resource"))
        if required and not required.intersection(target_values):
            reasons.add("resource_mismatch")
        if required:
            remaining.discard("resource")

    if "resource_pattern" in remaining:
        patterns = _values(constraints.get("resource_pattern"))
        if patterns:
            if not any(fnmatchcase(value, pattern) for value in target_values for pattern in patterns):
                reasons.add("resource_pattern_mismatch")
            remaining.discard("resource_pattern")

    principal_keys = ("principal", "principals", "principal_ref", "principal_refs")
    if remaining.intersection(principal_keys):
        required: set[str] = set()
        for key in principal_keys:
            required.update(_values(constraints.get(key)))
        if required and not required.intersection(source_values):
            reasons.add("principal_mismatch")
        if required:
            remaining.difference_update(principal_keys)

    return not reasons and not remaining, sorted(reasons), sorted(remaining)


__all__ = ["graph_context_constraints_satisfied"]
