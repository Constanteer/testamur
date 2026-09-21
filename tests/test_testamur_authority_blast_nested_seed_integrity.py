from __future__ import annotations

import pytest

from testamur.authority_blast_provenance import build_blast_radius_result


def _result(seed: str, *, nested_seed_refs=None):
    action = {
        "source_ref": seed,
        "target_ref": "resource:repo",
        "relation_type": "HAS_CAPABILITY",
        "capability": {"namespace": "repo", "action": "read"},
        "path_edge_ids": [f"edge:{seed}:read"],
    }
    if nested_seed_refs is not None:
        action["compromise_seed_refs"] = nested_seed_refs
    return {
        "starting_subject_ref": seed,
        "reachable_subjects": [],
        "actionable_capabilities": [action],
        "blocked_transitions": [],
        "trust_boundary_crossings": [],
        "truncation_reasons": [],
    }


def test_nested_seed_provenance_must_match_per_seed_traversal():
    with pytest.raises(ValueError, match="does not match traversal seed"):
        build_blast_radius_result(
            [_result("principal:a", nested_seed_refs=["principal:a", "principal:b"])],
            compromised_refs=["principal:a"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_nested_seed_provenance_cannot_borrow_another_explicit_seed():
    with pytest.raises(ValueError, match="does not match traversal seed"):
        build_blast_radius_result(
            [
                _result("principal:a", nested_seed_refs=["principal:b"]),
                _result("principal:b"),
            ],
            compromised_refs=["principal:a", "principal:b"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_matching_nested_seed_is_preserved_and_aggregate_union_remains_exact():
    result = build_blast_radius_result(
        [
            _result("principal:a", nested_seed_refs=["principal:a"]),
            _result("principal:b", nested_seed_refs=["principal:b"]),
        ],
        compromised_refs=["principal:a", "principal:b"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
    )
    actions = result["actionable_capabilities"]
    assert len(actions) == 2
    assert actions[0]["compromise_seed_refs"] in (["principal:a"], ["principal:b"])
    assert actions[1]["compromise_seed_refs"] in (["principal:a"], ["principal:b"])
    assert actions[0]["compromise_seed_refs"] != actions[1]["compromise_seed_refs"]
    assert result["semantics"]["nested_seed_provenance_is_bound_to_traversal_seed"] is True


def test_malformed_nested_seed_provenance_fails_closed():
    with pytest.raises(ValueError, match="must be a sequence"):
        build_blast_radius_result(
            [_result("principal:a", nested_seed_refs="principal:a")],
            compromised_refs=["principal:a"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )
