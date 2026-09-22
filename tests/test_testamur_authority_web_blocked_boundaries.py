from __future__ import annotations

from testamur.authority_web_projection import project_authority_web_view


def _payload() -> dict:
    crossing = {
        "edge_id": "edge:denied",
        "boundary_ref": "boundary:github",
        "path_position": 0,
        "path_edge_ids": ["edge:denied"],
    }
    unrelated = {
        "edge_id": "edge:unrelated",
        "boundary_ref": "boundary:other",
        "path_position": 0,
        "path_edge_ids": ["edge:unrelated"],
    }
    return {
        "ok": True,
        "schema": "testamur.product.authority-result.v1",
        "result": {
            "schema_version": "testamur.authority-product-result.v1",
            "engine_schema_version": "testamur.authority-reachability.v1",
            "starting_subject_ref": "connector:github",
            "compromise_model": "CONNECTOR_TAKEOVER",
            "reachable_subjects": [],
            "actionable_capabilities": [],
            "diagnostics": {
                "schema_version": "testamur.authority-product-diagnostics.v1",
                "blocked_transitions": [{
                    "edge_id": "edge:denied",
                    "source_ref": "connector:github",
                    "target_ref": "repo:private",
                    "relation_type": "HAS_CAPABILITY",
                    "reachability_class": "BLOCKED",
                    "reasons": ["scope_mismatch"],
                    "path_edge_ids": ["edge:denied"],
                    "supporting_edge_ids": [],
                    "boundary_refs": ["boundary:github"],
                    "trust_boundary_crossings": [crossing],
                }],
                "trust_boundary_refs": ["boundary:github", "boundary:other"],
                "trust_boundary_crossings": [crossing, unrelated],
            },
            "summary": {"blocked_transition_count": 1},
        },
    }


def test_web_preserves_blocked_transition_exact_boundary_evidence() -> None:
    view = project_authority_web_view(_payload())
    blocked = view["blocked_transitions"][0]
    assert blocked["boundary_refs"] == ["boundary:github"]
    assert blocked["trust_boundary_crossings"] == [{
        "edge_id": "edge:denied",
        "boundary_ref": "boundary:github",
        "path_position": 0,
        "path_edge_ids": ["edge:denied"],
    }]
    assert view["semantics"]["blocked_boundary_evidence_is_canonical_not_web_inferred"] is True


def test_web_does_not_infer_blocked_boundaries_from_global_crossings() -> None:
    payload = _payload()
    payload["result"]["diagnostics"]["blocked_transitions"][0]["boundary_refs"] = []
    payload["result"]["diagnostics"]["blocked_transitions"][0]["trust_boundary_crossings"] = []
    blocked = project_authority_web_view(payload)["blocked_transitions"][0]
    assert blocked["boundary_refs"] == []
    assert blocked["trust_boundary_crossings"] == []
