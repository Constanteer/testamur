from __future__ import annotations

from typing import Any, Mapping


_AUTHORITY_PRODUCT_SCHEMA = "testamur.product.authority-result.v1"


def _copy_capability(value: Mapping[str, Any]) -> dict[str, Any]:
    """Copy one already-authorized capability without weakening its identity."""
    return dict(value)


def project_authority_web_view(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Project the stable authority product result into a Web-safe view model.

    This function is intentionally presentation-only.  It accepts only the stable
    authority product projection and never derives authority from connectivity,
    lineage, reliance, affectedness, or UI adjacency.  In particular, blocked
    transitions remain blocked and supporting evidence remains distinct from the
    traversed authority path.
    """
    if payload.get("ok") is not True:
        return dict(payload)
    if payload.get("schema") != _AUTHORITY_PRODUCT_SCHEMA:
        raise ValueError("authority Web projection requires the stable authority product result")

    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise ValueError("authority product result is missing")

    capabilities = [
        _copy_capability(item)
        for item in result.get("actionable_capabilities", [])
        if isinstance(item, Mapping)
    ]
    blocked: list[dict[str, Any]] = []
    for item in result.get("blocked_transitions", []):
        if not isinstance(item, Mapping):
            continue
        blocked.append(
            {
                "edge_id": item.get("edge_id"),
                "source_ref": item.get("source_ref"),
                "target_ref": item.get("target_ref"),
                "relation": item.get("relation"),
                "reasons": list(item.get("reasons") or item.get("failure_reasons") or []),
                "unresolved_constraints": list(item.get("unresolved_constraints") or []),
                "path_edge_ids": list(item.get("path_edge_ids") or []),
                "supporting_edge_ids": list(item.get("supporting_edge_ids") or []),
                "evidence_state": item.get("evidence_state"),
            }
        )

    crossings = [dict(item) for item in result.get("trust_boundary_crossings", []) if isinstance(item, Mapping)]
    return {
        "ok": True,
        "schema": "testamur.web.authority-view.v1",
        "mode": result.get("mode"),
        "starting_subject_ref": result.get("starting_subject_ref"),
        "compromised_refs": list(result.get("compromised_refs") or []),
        "reachable_subjects": list(result.get("reachable_subjects") or []),
        "actionable_capabilities": capabilities,
        "blocked_transitions": blocked,
        "trust_boundary_crossings": crossings,
        "summary": dict(result.get("summary") or {}),
        "semantics": {
            "authority_is_evidence_backed": True,
            "blocked_is_not_partial_authority": True,
            "unresolved_is_not_satisfied": True,
            "supporting_evidence_is_not_path": True,
            "connectivity_is_not_authorization": True,
            "lineage_is_not_authority": True,
            "affectedness_does_not_seed_compromise": True,
        },
    }


__all__ = ["project_authority_web_view"]
