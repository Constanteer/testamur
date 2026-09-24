from __future__ import annotations

from typing import Any, Mapping


_AUTHORITY_PRODUCT_SCHEMA = "testamur.product.authority-result.v1"
_AUTHORITY_RESULT_SCHEMA = "testamur.authority-product-result.v1"
_AUTHORITY_DIAGNOSTICS_SCHEMA = "testamur.authority-product-diagnostics.v1"
_REASON_GROUPS = (
    "credential_or_token",
    "capability_or_delegation",
    "approval_or_mfa",
    "trust_boundary_policy",
    "other",
)


def _exact_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an exact non-empty string")
    return value


def _exact_string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a sequence of exact strings")
    return [_exact_string(item, field=f"{field}[]") for item in value]


def _copy_capability(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be a canonical capability mapping")
    return dict(value)


def _copy_capabilities(value: Any, *, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a sequence of canonical capability mappings")
    return [_copy_capability(item, field=f"{field}[]") for item in value]


def _copy_reason_groups(value: Any) -> dict[str, list[str]]:
    """Copy ProductService's canonical groups; Web never classifies raw reasons."""
    if not isinstance(value, Mapping):
        raise ValueError("blocked.reason_groups must be a canonical mapping")
    return {
        key: _exact_string_list(value.get(key), field=f"blocked.reason_groups.{key}")
        for key in _REASON_GROUPS
    }


def _copy_crossings(value: Any, *, field: str) -> list[dict[str, Any]]:
    """Copy engine-recorded crossing evidence without reconstructing graph paths."""
    if value is None:
        return []
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a sequence of canonical crossing mappings")
    copied: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"{field} entries must be canonical crossing mappings")
        crossing = dict(item)
        _exact_string(crossing.get("edge_id"), field=f"{field}.edge_id")
        _exact_string(crossing.get("boundary_ref"), field=f"{field}.boundary_ref")
        _exact_string_list(crossing.get("path_edge_ids"), field=f"{field}.path_edge_ids")
        copied.append(crossing)
    return copied


def project_authority_web_view(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Project the stable authority product result into a Web-safe view model.

    Presentation only: no connectivity, lineage, reliance, affectedness, or UI
    adjacency can create authority. Exact denied candidates and inherited delegation
    budgets remain diagnostic evidence and are never promoted to capabilities.
    Canonical denial groups pass through unchanged in meaning; Web does not infer
    them from raw reason strings. Engine-recorded compromise provenance and exact
    trust-boundary paths are retained rather than reconstructed from UI adjacency.
    Malformed authority evidence fails closed instead of being skipped/stringified.
    """
    if payload.get("ok") is not True:
        return dict(payload)
    if payload.get("schema") != _AUTHORITY_PRODUCT_SCHEMA:
        raise ValueError("authority Web projection requires the stable authority product result")
    result = payload.get("result")
    if not isinstance(result, Mapping) or result.get("schema_version") != _AUTHORITY_RESULT_SCHEMA:
        raise ValueError("authority Web projection requires the canonical authority product result schema")
    diagnostics = result.get("diagnostics")
    if not isinstance(diagnostics, Mapping):
        raise ValueError("authority product diagnostics are missing")
    if diagnostics.get("schema_version") != _AUTHORITY_DIAGNOSTICS_SCHEMA:
        raise ValueError("authority Web projection requires canonical authority diagnostics")

    capabilities = _copy_capabilities(result.get("actionable_capabilities"), field="actionable_capabilities")
    blocked: list[dict[str, Any]] = []
    raw_blocked = diagnostics.get("blocked_transitions")
    if raw_blocked is None:
        raw_blocked = []
    if isinstance(raw_blocked, (str, bytes, Mapping)) or not isinstance(raw_blocked, (list, tuple)):
        raise ValueError("blocked_transitions must be a sequence of canonical mappings")
    for item in raw_blocked:
        if not isinstance(item, Mapping):
            raise ValueError("blocked_transitions entries must be canonical mappings")
        blocked.append({
            "edge_id": _exact_string(item.get("edge_id"), field="blocked.edge_id"),
            "source_ref": _exact_string(item.get("source_ref"), field="blocked.source_ref"),
            "target_ref": _exact_string(item.get("target_ref"), field="blocked.target_ref"),
            "relation_type": _exact_string(item.get("relation_type"), field="blocked.relation_type"),
            "reachability_class": _exact_string(item.get("reachability_class"), field="blocked.reachability_class"),
            "reasons": _exact_string_list(item.get("reasons"), field="blocked.reasons"),
            "reason_groups": _copy_reason_groups(item.get("reason_groups")),
            "failed_constraints": _exact_string_list(item.get("failed_constraints"), field="blocked.failed_constraints"),
            "unresolved_constraints": _exact_string_list(item.get("unresolved_constraints"), field="blocked.unresolved_constraints"),
            "path_edge_ids": _exact_string_list(item.get("path_edge_ids"), field="blocked.path_edge_ids"),
            "supporting_edge_ids": _exact_string_list(item.get("supporting_edge_ids"), field="blocked.supporting_edge_ids"),
            "boundary_refs": _exact_string_list(item.get("boundary_refs"), field="blocked.boundary_refs"),
            "trust_boundary_crossings": _copy_crossings(item.get("trust_boundary_crossings"), field="blocked.trust_boundary_crossings"),
            "evidence_state": item.get("evidence_state"),
            "candidate_capabilities": _copy_capabilities(item.get("candidate_capabilities"), field="blocked.candidate_capabilities"),
            "inherited_capability_budget": _copy_capabilities(item.get("inherited_capability_budget"), field="blocked.inherited_capability_budget"),
            "compromise_seed_refs": _exact_string_list(item.get("compromise_seed_refs"), field="blocked.compromise_seed_refs"),
        })

    crossings = _copy_crossings(diagnostics.get("trust_boundary_crossings"), field="trust_boundary_crossings")
    starting_subject_ref = result.get("starting_subject_ref")
    if starting_subject_ref is not None:
        starting_subject_ref = _exact_string(starting_subject_ref, field="starting_subject_ref")
    compromised_refs = _exact_string_list(result.get("compromised_refs"), field="compromised_refs")
    return {
        "ok": True,
        "schema": "testamur.web.authority-view.v1",
        "engine_schema_version": result.get("engine_schema_version"),
        "starting_subject_ref": starting_subject_ref,
        "compromised_refs": compromised_refs,
        "compromise_model": _exact_string(result.get("compromise_model"), field="compromise_model"),
        "as_of": result.get("as_of"),
        "reachable_subjects": list(result.get("reachable_subjects") or []),
        "actionable_capabilities": capabilities,
        "blocked_transitions": blocked,
        "blocked_reason_counts": dict(diagnostics.get("blocked_reason_counts") or {}),
        "failed_constraint_counts": dict(diagnostics.get("failed_constraint_counts") or {}),
        "unresolved_constraint_counts": dict(diagnostics.get("unresolved_constraint_counts") or {}),
        "trust_boundary_refs": _exact_string_list(diagnostics.get("trust_boundary_refs"), field="trust_boundary_refs"),
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
            "reachable_does_not_mean_exercised": True,
            "denied_budget_is_diagnostic_not_authority": True,
            "reason_groups_are_canonical_not_web_inferred": True,
            "compromise_seed_provenance_is_canonical_not_web_inferred": True,
            "trust_boundary_crossings_preserve_exact_path_identity": True,
            "blocked_boundary_evidence_is_canonical_not_web_inferred": True,
            "malformed_authority_evidence_fails_closed": True,
            "web_projection_does_not_stringify_authority_identities": True,
        },
    }


__all__ = ["project_authority_web_view"]
