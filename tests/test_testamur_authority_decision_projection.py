from __future__ import annotations

import pytest

from testamur.authority_projection import project_authority_decision


def test_decision_projection_preserves_budget_support_and_boundary_evidence():
    result = {
        "reachable_subjects": [{
            "subject_ref": "principal",
            "reachability_class": "CONTROLLED",
            "delegated_capability_budget": [{"namespace": "github", "action": "repo.read"}],
            "path_edge_ids": ["edge:delegate", "edge:auth"],
            "supporting_edge_ids": ["edge:accepts"],
            "boundary_refs": ["boundary:tenant"],
        }],
        "actionable_capabilities": [],
        "blocked_transitions": [{
            "target_ref": "repo",
            "relation_type": "HAS_CAPABILITY",
            "reasons": ["scope_mismatch"],
            "reason_groups": {"capability_or_delegation": ["scope_mismatch"]},
            "failed_constraints": ["scope"],
            "unresolved_constraints": [],
            "inherited_capability_budget": [{"namespace": "github", "action": "repo.read"}],
            "candidate_capabilities": [{"namespace": "github", "action": "repo.admin"}],
            "path_edge_ids": ["edge:delegate", "edge:auth", "edge:admin"],
            "supporting_edge_ids": ["edge:accepts"],
            "boundary_refs": ["boundary:tenant"],
        }],
        "trust_boundary_refs": ["boundary:tenant"],
        "trust_boundary_crossings": [{"edge_id": "edge:auth", "boundary_ref": "boundary:tenant"}],
        "truncated": False,
        "truncation_reasons": [],
    }
    projection = project_authority_decision(result)
    assert projection["reachable"][0]["supporting_edge_ids"] == ["edge:accepts"]
    assert projection["blocked"][0]["inherited_capability_budget"][0]["action"] == "repo.read"
    assert projection["blocked"][0]["candidate_capabilities"][0]["action"] == "repo.admin"
    assert projection["trust_boundary_refs"] == ["boundary:tenant"]
    assert projection["semantics"]["supporting_edges_do_not_expand_capability_budget"] is True


def test_decision_projection_does_not_stringify_connectivity_shaped_identity():
    with pytest.raises(ValueError, match="subject_ref"):
        project_authority_decision({
            "reachable_subjects": [{
                "subject_ref": {"ref": "principal", "connected": True},
                "path_edge_ids": [], "supporting_edge_ids": [], "boundary_refs": [],
            }],
            "actionable_capabilities": [], "blocked_transitions": [],
            "trust_boundary_refs": [], "trust_boundary_crossings": [],
            "truncation_reasons": [],
        })
