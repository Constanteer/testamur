from __future__ import annotations

import json
from typing import Any, Mapping

from .authority_capability import CapabilityBudget, project_budget


def capability_identity(capability: Mapping[str, Any]) -> str:
    """Return a stable identity for an exact effective capability."""
    return json.dumps(dict(capability), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def projected_budget_identity(budget: CapabilityBudget | None) -> tuple[str, ...] | None:
    """Stable path-state identity without discarding delegated constraints."""
    projected = project_budget(budget)
    if projected is None:
        return None
    return tuple(sorted(capability_identity(item) for item in projected))


def project_authority_budget(budget: CapabilityBudget | None) -> list[dict[str, Any]] | None:
    """Product/CLI/Web projection for the exact effective delegated authority."""
    return project_budget(budget)


def _records(value: Any, *, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a record list")
    result = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{field} entries must be mappings")
        result.append(dict(item))
    return result


def _strings(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an exact string list")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} entries must be non-empty exact strings")
        result.append(item)
    return result


def _compromise_seeds(result: Mapping[str, Any]) -> list[str]:
    """Project only explicit engine compromise assumptions.

    Reachability has one explicit starting subject; blast radius has an explicit
    compromised-ref list.  No lineage, reliance, affectedness, connectivity, or
    reachable-subject record is promoted into a seed by this presentation layer.
    """
    if "compromised_refs" in result:
        return _strings(result.get("compromised_refs"), field="compromised_refs")
    if "starting_subject_ref" not in result:
        return []
    seed = result.get("starting_subject_ref")
    if not isinstance(seed, str) or not seed.strip():
        raise ValueError("starting_subject_ref must be exact evidence")
    return [seed]


def project_authority_decision(result: Mapping[str, Any]) -> dict[str, Any]:
    """Stable explanation projection; never reconstructs or enlarges authority."""
    if not isinstance(result, Mapping):
        raise ValueError("authority result must be a mapping")
    compromise_seeds = _compromise_seeds(result)
    reachable = _records(result.get("reachable_subjects"), field="reachable_subjects")
    actionable = _records(result.get("actionable_capabilities"), field="actionable_capabilities")
    blocked = _records(result.get("blocked_transitions"), field="blocked_transitions")
    crossings = _records(result.get("trust_boundary_crossings"), field="trust_boundary_crossings")

    reachable_projection = []
    for item in reachable:
        subject_ref = item.get("subject_ref")
        if not isinstance(subject_ref, str) or not subject_ref.strip():
            raise ValueError("reachable subject_ref must be exact evidence")
        reachable_projection.append({
            "subject_ref": subject_ref,
            "reachability_class": item.get("reachability_class"),
            "delegated_capability_budget": item.get("delegated_capability_budget"),
            "path_edge_ids": _strings(item.get("path_edge_ids"), field="reachable.path_edge_ids"),
            "supporting_edge_ids": _strings(item.get("supporting_edge_ids"), field="reachable.supporting_edge_ids"),
            "boundary_refs": _strings(item.get("boundary_refs"), field="reachable.boundary_refs"),
        })

    blocked_projection = []
    for item in blocked:
        target_ref = item.get("target_ref")
        if not isinstance(target_ref, str) or not target_ref.strip():
            raise ValueError("blocked target_ref must be exact evidence")
        blocked_projection.append({
            "target_ref": target_ref,
            "relation_type": item.get("relation_type"),
            "reasons": _strings(item.get("reasons"), field="blocked.reasons"),
            "reason_groups": dict(item.get("reason_groups") or {}),
            "failed_constraints": item.get("failed_constraints"),
            "unresolved_constraints": item.get("unresolved_constraints"),
            "inherited_capability_budget": item.get("inherited_capability_budget"),
            "candidate_capabilities": item.get("candidate_capabilities"),
            "path_edge_ids": _strings(item.get("path_edge_ids"), field="blocked.path_edge_ids"),
            "supporting_edge_ids": _strings(item.get("supporting_edge_ids"), field="blocked.supporting_edge_ids"),
            "boundary_refs": _strings(item.get("boundary_refs"), field="blocked.boundary_refs"),
        })

    return {
        "schema_version": "testamur.authority-decision-projection.v1",
        "compromise_seeds": compromise_seeds,
        "reachable": reachable_projection,
        "actionable_capabilities": actionable,
        "blocked": blocked_projection,
        "trust_boundary_refs": _strings(result.get("trust_boundary_refs"), field="trust_boundary_refs"),
        "trust_boundary_crossings": crossings,
        "truncated": bool(result.get("truncated", False)),
        "truncation_reasons": _strings(result.get("truncation_reasons"), field="truncation_reasons"),
        "semantics": {
            "projection_is_not_authority_evidence": True,
            "compromise_seeds_are_explicit_authority_assumptions": True,
            "affectedness_does_not_seed_compromise": True,
            "material_lineage_does_not_seed_compromise": True,
            "supporting_edges_do_not_expand_capability_budget": True,
            "connectivity_is_not_authorization": True,
            "lineage_reliance_affectedness_are_not_authority_grants": True,
        },
    }


__all__ = ["capability_identity", "projected_budget_identity", "project_authority_budget", "project_authority_decision"]
