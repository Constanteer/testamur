import pytest

from testamur.authority_product_api import project_product_authority_envelope


def _reach_result():
    return {
        "schema_version": "testamur.authority-reachability.v1",
        "starting_subject_ref": "principal:alice",
        "compromise_model": "credential_compromise",
        "reachable_subjects": [],
        "actionable_capabilities": [
            {
                "target_ref": "repo:testamur",
                "capability": {
                    "namespace": "github",
                    "action": "write",
                    "resource": "repo:testamur",
                    "constraints": {
                        "scope": ["contents:write"],
                        "audience": ["github.com"],
                        "tenant": ["Constanteer"],
                    },
                },
            }
        ],
        "blocked_transitions": [
            {
                "edge_id": "edge:auth",
                "source_ref": "credential:token",
                "target_ref": "service:github",
                "relation_type": "CAN_AUTHENTICATE_AS",
                "reasons": ["audience_mismatch"],
                "unresolved_constraints": ["device_binding"],
                "path_edge_ids": ["edge:owns"],
                "supporting_edge_ids": ["edge:accepts"],
            }
        ],
        "trust_boundary_crossings": [],
        "truncated": False,
        "truncation_reasons": [],
    }


def test_product_envelope_projects_exact_authority_result_without_collapsing_constraints():
    projected = project_product_authority_envelope(
        {
            "ok": True,
            "schema": "testamur.product.authority-reachability.v1",
            "result": _reach_result(),
        }
    )
    assert projected["schema"] == "testamur.product.authority-result.v1"
    result = projected["result"]
    assert result["actionable_capabilities"][0]["capability"]["constraints"] == {
        "scope": ["contents:write"],
        "audience": ["github.com"],
        "tenant": ["Constanteer"],
    }
    blocked = result["diagnostics"]["blocked_transitions"][0]
    assert blocked["path_edge_ids"] == ["edge:owns"]
    assert blocked["supporting_edge_ids"] == ["edge:accepts"]
    assert blocked["reasons"] == ["audience_mismatch"]
    assert blocked["unresolved_constraints"] == ["device_binding"]


def test_product_envelope_preserves_error_without_inventing_authority():
    error = {
        "ok": False,
        "error": {"code": "object_not_found", "details": {"ref": "principal:missing"}},
    }
    assert project_product_authority_envelope(error) == error


def test_product_envelope_rejects_non_authority_product_schema():
    with pytest.raises(ValueError, match="unsupported product authority schema"):
        project_product_authority_envelope(
            {"ok": True, "schema": "testamur.product.impact.v1", "result": _reach_result()}
        )


def test_product_envelope_rejects_missing_engine_result_mapping():
    with pytest.raises(ValueError, match="result must be a mapping"):
        project_product_authority_envelope(
            {"ok": True, "schema": "testamur.product.authority-blast-radius.v1", "result": None}
        )
