from __future__ import annotations

from collections import Counter
from typing import Any, Mapping


def project_authority_diagnostics(result: Mapping[str, Any]) -> dict[str, Any]:
    """Stable product projection for authority reachability diagnostics.

    This projection is deliberately descriptive. It never converts connectivity,
    lineage, reliance, or affectedness into authority and it never treats a blocked
    transition as a weaker permission. Exact path/support edge IDs and exact denied
    capability budgets are retained so clients never reconstruct permissions from
    graph adjacency.
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
                "candidate_capabilities": [dict(value) for value in item.get("candidate_capabilities") or [] if isinstance(value, Mapping)],
                "inherited_capability_budget": [dict(value) for value in item.get("inherited_capability_budget") or [] if isinstance(value, Mapping)],
            }
        )
    projected.sort(key=lambda item: (str(item["edge_id"] or ""), str(item["target_ref"] or "")))

    crossings = [dict(value) for value in result.get("trust_boundary_crossings") or []]
    crossings.sort(key=lambda item: (int(item.get("path_position") or 0), str(item.get("edge_id") or ""), str(item.get("boundary_ref") or "")))
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
            "denied_budget_is_diagnostic_not_authority": True,
        },
    }


def project_authority_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Project a canonical reachability/blast result without weakening semantics."""
    schema = str(result.get("schema_version") or "")
    if schema not in {"testamur.authority-reachability.v1", "testamur.authority-blast-radius.v1"}:
        raise ValueError(f"unsupported authority result schema: {schema or '<missing>'}")

    reachable = [dict(value) for value in result.get("reachable_subjects") or []]
    actions = [dict(value) for value in result.get("actionable_capabilities") or []]
    diagnostics = project_authority_diagnostics(result)
    return {
        "schema_version": "testamur.authority-product-result.v1",
        "engine_schema_version": schema,
        "starting_subject_ref": result.get("starting_subject_ref"),
        "compromised_refs": list(result.get("compromised_refs") or []),
        "compromise_model": result.get("compromise_model"),
        "as_of": result.get("as_of"),
        "reachable_subjects": reachable,
        "actionable_capabilities": actions,
        "diagnostics": diagnostics,
        "summary": {
            "reachable_subject_count": len(reachable),
            "actionable_capability_count": len(actions),
            "blocked_transition_count": len(diagnostics["blocked_transitions"]),
            "trust_boundary_crossing_count": len(diagnostics["trust_boundary_crossings"]),
            "truncated": bool(result.get("truncated")),
            "truncation_reasons": list(result.get("truncation_reasons") or []),
        },
        "semantics": {
            "authority_source_of_truth": "canonical_engine_result",
            "reachable_does_not_mean_exercised": True,
            "blast_radius_is_potential_authority": schema.endswith("blast-radius.v1"),
            "blocked_is_not_partial_authority": True,
            "connectivity_is_not_authorization": True,
            "lineage_is_not_authority": True,
            "affectedness_does_not_seed_compromise": True,
            "capability_constraints_are_not_collapsed": True,
        },
    }


__all__ = ["project_authority_diagnostics", "project_authority_result"]
