from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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

    This helper deliberately does no graph lookup.  In particular it cannot infer
    a boundary, permission, credential validity, or capability from connectivity,
    lineage, reliance, or affectedness.  Callers must pass the boundary crossings
    computed for the exact attempted ``path_edge_ids``.
    """
    path = [str(item) for item in path_edge_ids]
    boundaries = [str(item) for item in boundary_refs]
    crossings = [dict(item) for item in trust_boundary_crossings]

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

    crossing_boundaries = {str(item["boundary_ref"]) for item in crossings}
    if set(boundaries) != crossing_boundaries:
        raise ValueError("boundary_refs must exactly match trust_boundary_crossings")

    return {
        "edge_id": edge_id,
        "source_ref": source_ref,
        "target_ref": target_ref,
        "relation_type": relation_type,
        "path_edge_ids": path,
        "supporting_edge_ids": list(supporting_edge_ids),
        "reasons": list(reasons),
        "unresolved_constraints": list(unresolved_constraints),
        "reachability_class": reachability_class,
        "evidence_state": evidence_state,
        "boundary_refs": boundaries,
        "trust_boundary_crossings": crossings,
    }


__all__ = ["blocked_transition_record"]
