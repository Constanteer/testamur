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
        return ({text}, True) if text else (set(), True)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        values: set[str] = set()
        if not value:
            return set(), True
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return set(), False
            values.add(item.strip())
        return values, True
    return set(), False


def _exact_diagnostic_values(values: Sequence[Any], *, field: str) -> set[str]:
    """Preserve decision-bearing constraint diagnostics without coercion."""
    result: set[str] = set()
    for index, item in enumerate(values):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field}[{index}] must be an exact non-empty string")
        result.add(item.strip())
    return result


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


def _typed_subject_values(ref: str, subject: Mapping[str, Any], keys: tuple[str, ...]) -> tuple[set[str], bool]:
    values = {ref.strip()} if isinstance(ref, str) and ref.strip() else set()
    attributes = subject.get("attributes") if isinstance(subject.get("attributes"), Mapping) else {}
    for container in (subject, attributes):
        aliases, valid = _aliased_values(container, keys)
        if not valid:
            return values, False
        values.update(aliases)
    return values, True


def graph_context_constraints_satisfied(
    constraints: Mapping[str, Any], *, source_ref: str, target_ref: str,
    source_subject: Mapping[str, Any] | None = None,
    target_subject: Mapping[str, Any] | None = None,
    unresolved: Sequence[str] = (),
) -> tuple[bool, list[str], list[str]]:
    """Resolve constraints provable from the exact traversed authority edge.

    Typed aliases plus canonical refs are the only graph evidence. Aliases are
    alternate encodings and must agree; malformed objects are never stringified.
    Connectivity alone never satisfies a permission constraint. A service_ref is
    satisfied only by the exact target identity or explicit target service aliases;
    an adjacent service elsewhere in the graph is not evidence.
    """
    remaining = _exact_diagnostic_values(unresolved, field="unresolved")
    reasons: set[str] = set()
    source = source_subject or {}
    target = target_subject or {}
    principal_keys = ("principal", "principals", "principal_ref", "principal_refs")
    resource_keys = ("resource", "resources", "resource_ref", "resource_refs")
    service_keys = ("service_ref", "service_refs")
    source_principals, source_valid = _typed_subject_values(source_ref, source, principal_keys)
    target_resources, target_valid = _typed_subject_values(target_ref, target, resource_keys)
    target_services, target_service_valid = _typed_subject_values(target_ref, target, service_keys)

    if not source_valid and remaining.intersection(principal_keys):
        reasons.add("principal_evidence_malformed_or_conflicting")
        remaining.difference_update(principal_keys)
    if not target_valid and remaining.intersection({"resource", "resource_pattern"}):
        reasons.add("resource_evidence_malformed_or_conflicting")
        remaining.difference_update({"resource", "resource_pattern"})
    if not target_service_valid and remaining.intersection(service_keys):
        reasons.add("service_evidence_malformed_or_conflicting")
        remaining.difference_update(service_keys)

    if "resource" in remaining:
        required, valid = _claim_values(constraints.get("resource"))
        if not valid:
            reasons.add("resource_constraint_malformed")
        elif not required:
            reasons.add("resource_constraint_missing_value")
        elif not required.intersection(target_resources):
            reasons.add("resource_mismatch")
        remaining.discard("resource")

    if "resource_pattern" in remaining:
        patterns, valid = _claim_values(constraints.get("resource_pattern"))
        if not valid:
            reasons.add("resource_pattern_constraint_malformed")
        elif not patterns:
            reasons.add("resource_pattern_constraint_missing_value")
        elif not any(fnmatchcase(value, pattern) for value in target_resources for pattern in patterns):
            reasons.add("resource_pattern_mismatch")
        remaining.discard("resource_pattern")

    if remaining.intersection(principal_keys):
        required, valid = _aliased_values(constraints, principal_keys)
        if not valid:
            reasons.add("principal_constraint_malformed_or_conflicting")
        elif not required:
            reasons.add("principal_constraint_missing_value")
        elif not required.intersection(source_principals):
            reasons.add("principal_mismatch")
        remaining.difference_update(principal_keys)

    if remaining.intersection(service_keys):
        required, valid = _aliased_values(constraints, service_keys)
        if not valid:
            reasons.add("service_constraint_malformed_or_conflicting")
        elif not required:
            reasons.add("service_constraint_missing_value")
        elif not required.intersection(target_services):
            reasons.add("service_mismatch")
        remaining.difference_update(service_keys)

    return not reasons and not remaining, sorted(reasons), sorted(remaining)


def resolve_graph_context_verdict(
    constraints: Mapping[str, Any], credential_verdict: tuple[bool, Sequence[str], Sequence[str]], *,
    source_ref: str, target_ref: str, source_subject: Mapping[str, Any] | None = None,
    target_subject: Mapping[str, Any] | None = None,
) -> tuple[bool, list[str], list[str]]:
    """Refine a metadata verdict using evidence from the exact traversed edge."""
    _credential_ok, credential_reasons, unresolved = credential_verdict
    exact_credential_reasons = _exact_diagnostic_values(credential_reasons, field="credential_reasons")
    _graph_ok, graph_reasons, remaining = graph_context_constraints_satisfied(
        constraints, source_ref=source_ref, target_ref=target_ref,
        source_subject=source_subject, target_subject=target_subject, unresolved=unresolved,
    )
    reasons = sorted(exact_credential_reasons | set(graph_reasons))
    return not reasons and not remaining, reasons, remaining


def evaluate_exact_edge_constraints(
    edge: Mapping[str, Any], *, credential_attributes: Mapping[str, Any],
    source_subject: Mapping[str, Any] | None = None,
    target_subject: Mapping[str, Any] | None = None,
    attribute_ref: str | None = None, as_of: Any = None,
) -> tuple[bool, list[str], list[str]]:
    """Canonical two-stage constraint evaluation for one exact authority edge.

    CAN_AUTHENTICATE_AS.service_ref is intentionally evaluated by the reachability
    engine against an explicit ACCEPTS_CREDENTIAL support edge. It is removed only
    from this local target-binding stage so an account target is not mistaken for
    the accepting service. Other relations must prove service_ref on their exact
    target and fail closed otherwise.
    """
    raw = edge.get("constraints")
    if raw is not None and not isinstance(raw, Mapping):
        return False, [], ["constraints"]
    constraints = dict(raw or {})
    local_constraints = dict(constraints)
    if edge.get("relation_type") == "CAN_AUTHENTICATE_AS" and "service_ref" in local_constraints:
        local_constraints.pop("service_ref")
    source_ref = edge.get("source_ref") if isinstance(edge.get("source_ref"), str) else ""
    target_ref = edge.get("target_ref") if isinstance(edge.get("target_ref"), str) else ""
    verdict = credential_constraints_satisfied(credential_attributes, local_constraints, as_of=as_of)
    return resolve_graph_context_verdict(
        local_constraints, verdict, source_ref=source_ref, target_ref=target_ref,
        source_subject=source_subject, target_subject=target_subject,
    )


__all__ = ["evaluate_exact_edge_constraints", "graph_context_constraints_satisfied", "resolve_graph_context_verdict"]
