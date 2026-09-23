from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _exact_ref(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty exact string ref")
    return value


def _exact_refs(values: Sequence[str], *, field: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be a sequence of exact string refs")
    refs: list[str] = []
    for value in values:
        refs.append(_exact_ref(value, field=field))
    return refs


def _exact_strings(values: Sequence[str], *, field: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be a sequence of exact strings")
    result: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must contain only non-empty exact strings")
        result.append(value)
    return result


def blocked_transition_record(
    *,
    edge_id: str,
    source_ref: str,
    target_ref: str,
    relation_type: str,
    path_edge_ids: Sequence[str],
    supporting_edge_ids: Sequence[str],
    reasons: Sequence[str],
    unresolved_constraints: Sequence[str],
    reachability_class: str,
    evidence_state: str,
    boundary_refs: Sequence[str],
    trust_boundary_crossings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a blocked authority record from already-established exact evidence.

    This helper deliberately does no graph lookup. In particular it cannot infer
    a boundary, permission, credential validity, or capability from connectivity,
    lineage, reliance, or affectedness. Callers must pass the boundary crossings
    computed for the exact attempted ``path_edge_ids``.

    Provenance identifiers are fail-closed: arbitrary scalars are never coerced
    with ``str(...)`` into evidence. This keeps a malformed caller value from
    manufacturing an edge, subject, relation, or trust-boundary identity.
    """
    exact_edge_id = _exact_ref(edge_id, field="edge_id")
    exact_source_ref = _exact_ref(source_ref, field="source_ref")
    exact_target_ref = _exact_ref(target_ref, field="target_ref")
    exact_relation_type = _exact_ref(relation_type, field="relation_type")
    exact_reachability_class = _exact_ref(reachability_class, field="reachability_class")
    exact_evidence_state = _exact_ref(evidence_state, field="evidence_state")
    path = _exact_refs(path_edge_ids, field="path_edge_ids")
    supporting = _exact_refs(supporting_edge_ids, field="supporting_edge_ids")
    boundaries = _exact_refs(boundary_refs, field="boundary_refs")
    exact_reasons = _exact_strings(reasons, field="reasons")
    exact_unresolved = _exact_strings(unresolved_constraints, field="unresolved_constraints")

    if not path or path[-1] != exact_edge_id:
        raise ValueError("blocked transition edge_id must be the terminal edge of the exact attempted path")
    if isinstance(trust_boundary_crossings, (str, bytes)):
        raise ValueError("trust_boundary_crossings must be a sequence of exact crossing records")
    crossings: list[dict[str, Any]] = []
    for item in trust_boundary_crossings:
        if not isinstance(item, Mapping):
            raise ValueError("trust_boundary_crossings must contain only mapping records")
        crossings.append(dict(item))

    for crossing in crossings:
        crossing_path = crossing.get("path_edge_ids")
        if not isinstance(crossing_path, list) or crossing_path != path:
            raise ValueError("blocked transition crossing must describe the exact attempted path")
        boundary_ref = crossing.get("boundary_ref")
        if not isinstance(boundary_ref, str) or not boundary_ref.strip():
            raise ValueError("blocked transition crossing requires an exact boundary_ref")
        edge_ref = crossing.get("edge_id")
        if not isinstance(edge_ref, str) or edge_ref not in path:
            raise ValueError("blocked transition crossing edge_id must occur on the attempted path")

    crossing_boundaries = {item["boundary_ref"] for item in crossings}
    if set(boundaries) != crossing_boundaries:
        raise ValueError("boundary_refs must exactly match trust_boundary_crossings")

    return {
        "edge_id": exact_edge_id,
        "source_ref": exact_source_ref,
        "target_ref": exact_target_ref,
        "relation_type": exact_relation_type,
        "path_edge_ids": path,
        "supporting_edge_ids": supporting,
        "reasons": exact_reasons,
        "unresolved_constraints": exact_unresolved,
        "reachability_class": exact_reachability_class,
        "evidence_state": exact_evidence_state,
        "boundary_refs": boundaries,
        "trust_boundary_crossings": crossings,
    }


__all__ = ["blocked_transition_record"]
