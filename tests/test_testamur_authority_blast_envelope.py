from __future__ import annotations

import pytest

from testamur.authority_blast_provenance import build_blast_radius_result


def _reachability(seed: str, *, path: list[str]) -> dict:
    return {
        "starting_subject_ref": seed,
        "reachable_subjects": [
            {
                "subject_ref": "service:target",
                "depth": len(path),
                "path_edge_ids": path,
                "trust_boundary_crossings": [],
            }
        ],
        "actionable_capabilities": [
            {
                "target_ref": "repo:target",
                "capability": {"namespace": "repo", "action": "write"},
                "path_edge_ids": path,
                "trust_boundary_crossings": [],
            }
        ],
        "blocked_transitions": [],
        "trust_boundary_crossings": [],
        "truncation_reasons": [],
    }


def test_blast_envelope_preserves_exact_seed_provenance_without_connectivity_inference() -> None:
    result = build_blast_radius_result(
        [
            _reachability("principal:a", path=["edge:delegate", "edge:write"]),
            _reachability("principal:b", path=["edge:delegate", "edge:write"]),
        ],
        compromised_refs=["principal:b", "principal:a"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
    )

    assert result["schema_version"] == "testamur.authority-blast-radius.v1"
    assert result["compromised_refs"] == ["principal:a", "principal:b"]
    assert result["reachable_subjects"][0]["compromise_seed_refs"] == ["principal:a", "principal:b"]
    assert result["actionable_capabilities"][0]["compromise_seed_refs"] == ["principal:a", "principal:b"]
    assert result["semantics"]["compromise_seed_provenance_is_engine_recorded"] is True
    assert result["semantics"]["material_lineage_does_not_grant_authority"] is True
    assert result["semantics"]["blast_results_are_bound_to_explicit_compromise_seeds"] is True


def test_blast_envelope_keeps_distinct_exact_paths_separate() -> None:
    result = build_blast_radius_result(
        [
            _reachability("principal:a", path=["edge:a", "edge:write"]),
            _reachability("principal:b", path=["edge:b", "edge:write"]),
        ],
        compromised_refs=["principal:a", "principal:b"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
    )

    assert len(result["actionable_capabilities"]) == 2
    assert {tuple(item["compromise_seed_refs"]) for item in result["actionable_capabilities"]} == {
        ("principal:a",),
        ("principal:b",),
    }


def test_blast_envelope_does_not_allow_empty_assumed_seed_set() -> None:
    with pytest.raises(ValueError, match="compromised_refs"):
        build_blast_radius_result([], compromised_refs=[], compromise_model="FULL_SUBJECT_COMPROMISE")


def test_blast_envelope_rejects_result_from_unassumed_seed() -> None:
    with pytest.raises(ValueError, match="correspond exactly"):
        build_blast_radius_result(
            [_reachability("principal:other", path=["edge:write"])],
            compromised_refs=["principal:assumed"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_blast_envelope_requires_result_for_every_explicit_seed() -> None:
    with pytest.raises(ValueError, match="correspond exactly"):
        build_blast_radius_result(
            [_reachability("principal:a", path=["edge:write"])],
            compromised_refs=["principal:a", "principal:b"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )


def test_blast_envelope_rejects_duplicate_result_for_same_seed() -> None:
    with pytest.raises(ValueError, match="duplicate reachability result"):
        build_blast_radius_result(
            [
                _reachability("principal:a", path=["edge:first"]),
                _reachability("principal:a", path=["edge:second"]),
            ],
            compromised_refs=["principal:a"],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )
