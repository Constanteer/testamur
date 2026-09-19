from __future__ import annotations

import pytest

from testamur.authority_web_projection import project_authority_web_view


def _payload() -> dict:
    return {
        "ok": True,
        "schema": "testamur.product.authority-result.v1",
        "result": {
            "schema_version": "testamur.authority-product-result.v1",
            "engine_schema_version": "testamur.authority-reachability.v1",
            "starting_subject_ref": "svc:connector",
            "compromised_refs": [],
            "compromise_model": "credential_theft",
            "as_of": "2026-09-20T00:00:00Z",
            "reachable_subjects": [{"subject_ref": "svc:connector"}, {"subject_ref": "repo:testamur"}],
            "actionable_capabilities": [
                {
                    "namespace": "github",
                    "action": "write",
                    "resource": "repo:testamur",
                    "constraints": {
                        "audience": ["github.com"],
                        "scope": ["contents:write"],
                        "tenant": ["Constanteer"],
                    },
                }
            ],
            "diagnostics": {
                "schema_version": "testamur.authority-product-diagnostics.v1",
                "blocked_transitions": [
                    {
                        "edge_id": "edge:token-use",
                        "source_ref": "svc:connector",
                        "target_ref": "repo:other",
                        "relation_type": "CAN_ACT_AS",
                        "reachability_class": "credential_gated",
                        "reasons": ["audience_mismatch"],
                        "unresolved_constraints": ["device_binding"],
                        "path_edge_ids": ["edge:delegation"],
                        "supporting_edge_ids": ["edge:accepts-token"],
                        "evidence_state": "recorded",
                    }
                ],
                "blocked_reason_counts": {"audience_mismatch": 1},
                "unresolved_constraint_counts": {"device_binding": 1},
                "trust_boundary_refs": ["boundary:github"],
                "trust_boundary_crossings": [
                    {"edge_id": "edge:delegation", "boundary_ref": "boundary:github", "path_position": 1}
                ],
            },
            "summary": {"actionable_capability_count": 1, "blocked_transition_count": 1},
        },
    }


def test_web_projection_preserves_constrained_capability_and_exact_diagnostics() -> None:
    view = project_authority_web_view(_payload())
    assert view["schema"] == "testamur.web.authority-view.v1"
    assert view["engine_schema_version"] == "testamur.authority-reachability.v1"
    capability = view["actionable_capabilities"][0]
    assert capability["constraints"] == {
        "audience": ["github.com"],
        "scope": ["contents:write"],
        "tenant": ["Constanteer"],
    }
    blocked = view["blocked_transitions"][0]
    assert blocked["reasons"] == ["audience_mismatch"]
    assert blocked["unresolved_constraints"] == ["device_binding"]
    assert blocked["path_edge_ids"] == ["edge:delegation"]
    assert blocked["supporting_edge_ids"] == ["edge:accepts-token"]
    assert blocked["relation_type"] == "CAN_ACT_AS"
    assert view["blocked_reason_counts"] == {"audience_mismatch": 1}
    assert view["unresolved_constraint_counts"] == {"device_binding": 1}


def test_supporting_credential_evidence_is_not_promoted_to_path_or_crossing() -> None:
    view = project_authority_web_view(_payload())
    blocked = view["blocked_transitions"][0]
    assert "edge:accepts-token" not in blocked["path_edge_ids"]
    assert [item["edge_id"] for item in view["trust_boundary_crossings"]] == ["edge:delegation"]
    assert view["trust_boundary_refs"] == ["boundary:github"]
    assert view["semantics"]["supporting_evidence_is_not_path"] is True


def test_web_projection_rejects_flat_or_missing_diagnostics_instead_of_dropping_evidence() -> None:
    payload = _payload()
    diagnostics = payload["result"].pop("diagnostics")
    payload["result"]["blocked_transitions"] = diagnostics["blocked_transitions"]
    with pytest.raises(ValueError, match="diagnostics are missing"):
        project_authority_web_view(payload)


def test_web_projection_rejects_wrong_nested_diagnostics_schema() -> None:
    payload = _payload()
    payload["result"]["diagnostics"]["schema_version"] = "testamur.material-lineage.v1"
    with pytest.raises(ValueError, match="canonical authority diagnostics"):
        project_authority_web_view(payload)


def test_web_projection_rejects_raw_engine_or_lineage_payloads() -> None:
    with pytest.raises(ValueError):
        project_authority_web_view({"ok": True, "schema": "testamur.authority-reachability.v1", "result": {}})
    with pytest.raises(ValueError):
        project_authority_web_view({"ok": True, "schema": "testamur.product.impact.v1", "result": {}})


def test_error_envelope_passes_through_without_synthesizing_authority() -> None:
    error = {"ok": False, "error": {"code": "object_not_found", "message": "missing"}}
    assert project_authority_web_view(error) == error
