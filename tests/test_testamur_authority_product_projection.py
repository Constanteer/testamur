import pytest

from testamur.authority_product_projection import (
    project_authority_diagnostics,
    project_authority_result,
)


def test_projection_preserves_exact_blocking_evidence_without_inference():
    projected = project_authority_diagnostics(
        {
            "blocked_transitions": [
                {
                    "edge_id": "edge:auth",
                    "source_ref": "credential:token",
                    "target_ref": "repo:private",
                    "relation_type": "CAN_AUTHENTICATE_AS",
                    "reachability_class": "BLOCKED",
                    "reasons": ["audience_outside_delegation"],
                    "failed_constraints": ["audience"],
                    "unresolved_constraints": ["device_binding"],
                    "path_edge_ids": ["edge:read", "edge:auth"],
                    "supporting_edge_ids": ["edge:accepts"],
                    "evidence_state": "CORROBORATED",
                }
            ],
            "trust_boundary_refs": ["boundary:corp"],
            "trust_boundary_crossings": [
                {
                    "edge_id": "edge:auth",
                    "boundary_ref": "boundary:corp",
                    "path_position": 2,
                }
            ],
        }
    )
    item = projected["blocked_transitions"][0]
    assert item["reasons"] == ["audience_outside_delegation"]
    assert item["failed_constraints"] == ["audience"]
    assert item["unresolved_constraints"] == ["device_binding"]
    assert item["path_edge_ids"] == ["edge:read", "edge:auth"]
    assert item["supporting_edge_ids"] == ["edge:accepts"]
    assert projected["blocked_reason_counts"] == {"audience_outside_delegation": 1}
    assert projected["failed_constraint_counts"] == {"audience": 1}
    assert projected["unresolved_constraint_counts"] == {"device_binding": 1}
    assert projected["trust_boundary_crossings"][0]["edge_id"] == "edge:auth"


def test_projection_does_not_promote_blocked_transition_to_capability():
    projected = project_authority_diagnostics(
        {
            "blocked_transitions": [
                {
                    "edge_id": "edge:connect",
                    "source_ref": "process:web",
                    "target_ref": "service:github",
                    "relation_type": "CAN_CONNECT",
                    "reasons": [],
                    "unresolved_constraints": ["network_zone"],
                }
            ]
        }
    )
    assert "actionable_capabilities" not in projected
    assert projected["semantics"]["blocked_is_not_partial_authority"] is True
    assert projected["semantics"]["connectivity_is_not_authorization"] is True
    assert projected["semantics"]["lineage_is_not_authority"] is True


def test_product_result_keeps_distinct_constrained_capabilities():
    base = {
        "schema_version": "testamur.authority-reachability.v1",
        "starting_subject_ref": "principal:alice",
        "compromise_model": "credential_compromise",
        "reachable_subjects": [],
        "blocked_transitions": [],
        "trust_boundary_crossings": [],
        "actionable_capabilities": [
            {
                "target_ref": "repo:testamur",
                "capability": {
                    "namespace": "github",
                    "action": "write",
                    "resource": "repo:testamur",
                    "constraints": {"scope": ["contents:write"], "audience": ["github.com"]},
                },
            },
            {
                "target_ref": "repo:testamur",
                "capability": {
                    "namespace": "github",
                    "action": "write",
                    "resource": "repo:testamur",
                    "constraints": {"scope": ["pull_requests:write"], "audience": ["github.com"]},
                },
            },
        ],
    }
    projected = project_authority_result(base)
    assert projected["summary"]["actionable_capability_count"] == 2
    assert len(projected["actionable_capabilities"]) == 2
    assert projected["semantics"]["capability_constraints_are_not_collapsed"] is True


def test_blast_projection_keeps_potential_authority_semantics_and_diagnostics():
    projected = project_authority_result(
        {
            "schema_version": "testamur.authority-blast-radius.v1",
            "compromised_refs": ["principal:alice", "credential:token"],
            "compromise_model": "credential_compromise",
            "reachable_subjects": [],
            "actionable_capabilities": [],
            "blocked_transitions": [
                {
                    "edge_id": "edge:auth",
                    "source_ref": "credential:token",
                    "target_ref": "service:github",
                    "relation_type": "CAN_AUTHENTICATE_AS",
                    "reasons": ["audience_mismatch"],
                    "unresolved_constraints": [],
                }
            ],
            "trust_boundary_refs": [],
            "trust_boundary_crossings": [],
            "truncated": False,
            "truncation_reasons": [],
        }
    )
    assert projected["compromised_refs"] == ["principal:alice", "credential:token"]
    assert projected["summary"]["blocked_transition_count"] == 1
    assert projected["diagnostics"]["blocked_reason_counts"] == {"audience_mismatch": 1}
    assert projected["semantics"]["blast_radius_is_potential_authority"] is True
    assert projected["semantics"]["affectedness_does_not_seed_compromise"] is True


def test_product_result_rejects_unknown_engine_schema():
    with pytest.raises(ValueError, match="unsupported authority result schema"):
        project_authority_result({"schema_version": "testamur.material-lineage.v1"})
