from __future__ import annotations

from testamur.authority_product_projection import project_authority_result


def test_product_projection_preserves_only_engine_recorded_blast_seed_provenance():
    result = project_authority_result({
        "schema_version": "testamur.authority-blast-radius.v1",
        "compromised_refs": ["principal:a", "principal:b"],
        "compromise_model": "FULL_SUBJECT_COMPROMISE",
        "reachable_subjects": [{
            "subject_ref": "connector:github",
            "path_edge_ids": ["edge:a"],
            "compromise_seed_refs": ["principal:b", "principal:a", "principal:a"],
        }],
        "actionable_capabilities": [{
            "target_ref": "repo:exact",
            "capability": {"namespace": "github", "action": "read", "resource": "repo:exact"},
            "path_edge_ids": ["edge:a", "edge:read"],
            "compromise_seed_refs": ["principal:a"],
        }],
        "blocked_transitions": [{
            "edge_id": "edge:blocked",
            "source_ref": "connector:github",
            "target_ref": "repo:other",
            "reasons": ["scope_mismatch"],
            "compromise_seed_refs": ["principal:b"],
        }],
    })

    assert result["reachable_subjects"][0]["compromise_seed_refs"] == ["principal:a", "principal:b"]
    assert result["actionable_capabilities"][0]["compromise_seed_refs"] == ["principal:a"]
    assert result["diagnostics"]["blocked_transitions"][0]["compromise_seed_refs"] == ["principal:b"]
    assert result["semantics"]["compromise_seed_provenance_is_engine_recorded_not_product_inferred"] is True


def test_missing_seed_provenance_stays_unknown_instead_of_being_inferred_from_global_seeds():
    result = project_authority_result({
        "schema_version": "testamur.authority-blast-radius.v1",
        "compromised_refs": ["principal:a", "principal:b"],
        "compromise_model": "FULL_SUBJECT_COMPROMISE",
        "reachable_subjects": [{"subject_ref": "connector:github", "path_edge_ids": ["edge:a"]}],
        "actionable_capabilities": [],
        "blocked_transitions": [],
    })

    assert result["reachable_subjects"][0]["compromise_seed_refs"] == []
