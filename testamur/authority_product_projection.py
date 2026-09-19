from __future__ import annotations

from collections import Counter
from typing import Any, Mapping


def project_authority_diagnostics(result: Mapping[str, Any]) -> dict[str, Any]:
    """Stable product projection for authority reachability diagnostics.

    This projection is deliberately descriptive.  It never converts connectivity,
    lineage, reliance, or affectedness into authority and it never treats a blocked
    transition as a weaker permission.  Exact path/support edge IDs are retained so
    a CLI or Web client can request the canonical explanation without reconstructing
    evidence from graph adjacency.
    """
    blocked = list(result.get("blocked_transitions") or [])
    reason_counts: Counter[str] = Counter()
    unresolved_counts: Counter[str] = Counter()
    projected: list[dict[str, Any]] = []
    for item in blocked:
        reasons = sorted({str(value) for value in item.get("reasons") or []})
        unresolved = sorted({str(value) for value in item.get("unresolved_constraints") or []})
        reason_counts.update(reasons)
        unresolved_counts.update(unresolved)
        projected.append(
            {
                "edge_id": item.get("edge_id"),
                "source_ref": item.get("source_ref"),
                "target_ref": item.get("target_ref"),
                "relation_type": item.get("relation_type"),
                "reachability_class": item.get("reachability_class"),
                "reasons": reasons,
                "unresolved_constraints": unresolved,
                "path_edge_ids": list(item.get("path_edge_ids") or []),
                "supporting_edge_ids": list(item.get("supporting_edge_ids") or []),
                "evidence_state": item.get("evidence_state"),
            }
        )
    projected.sort(key=lambda item: (str(item["edge_id"] or ""), str(item["target_ref"] or "")))

    crossings = [dict(value) for value in result.get("trust_boundary_crossings") or []]
    crossings.sort(
        key=lambda item: (
            int(item.get("path_position") or 0),
            str(item.get("edge_id") or ""),
            str(item.get("boundary_ref") or ""),
        )
    )
    return {
        "schema_version": "testamur.authority-product-diagnostics.v1",
        "blocked_transitions": projected,
        "blocked_reason_counts": dict(sorted(reason_counts.items())),
        "unresolved_constraint_counts": dict(sorted(unresolved_counts.items())),
        "trust_boundary_refs": sorted({str(value) for value in result.get("trust_boundary_refs") or []}),
        "trust_boundary_crossings": crossings,
        "semantics": {
            "blocked_is_not_partial_authority": True,
            "unresolved_is_not_satisfied": True,
            "supporting_evidence_is_not_path_traversal": True,
            "connectivity_is_not_authorization": True,
            "lineage_is_not_authority": True,
        },
    }


__all__ = ["project_authority_diagnostics"]
