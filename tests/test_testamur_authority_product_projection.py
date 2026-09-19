from testamur.authority_product_projection import project_authority_diagnostics


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
                    "reasons": ["audience_mismatch"],
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
    assert item["reasons"] == ["audience_mismatch"]
    assert item["unresolved_constraints"] == ["device_binding"]
    assert item["path_edge_ids"] == ["edge:read", "edge:auth"]
    assert item["supporting_edge_ids"] == ["edge:accepts"]
    assert projected["blocked_reason_counts"] == {"audience_mismatch": 1}
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
