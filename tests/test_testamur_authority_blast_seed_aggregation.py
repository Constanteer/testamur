from __future__ import annotations

from testamur.authority_blast_provenance import aggregate_seeded_blast_results


def _result(seed: str, path: list[str]) -> dict:
    return {
        "starting_subject_ref": seed,
        "reachable_subjects": [{"subject_ref": "connector:github", "depth": len(path), "path_edge_ids": path}],
        "actionable_capabilities": [{
            "target_ref": "repo:exact",
            "capability": {"namespace": "github", "action": "read", "resource": "repo:exact"},
            "path_edge_ids": [*path, "edge:read"],
        }],
        "blocked_transitions": [{
            "edge_id": "edge:blocked",
            "source_ref": "connector:github",
            "target_ref": "repo:other",
            "path_edge_ids": [*path, "edge:blocked"],
            "reasons": ["scope_mismatch"],
        }],
    }


def test_same_exact_path_unions_seed_provenance_without_overwrite():
    aggregated = aggregate_seeded_blast_results([
        _result("principal:b", ["edge:shared"]),
        _result("principal:a", ["edge:shared"]),
    ])

    assert aggregated["reachable_subjects"][0]["compromise_seed_refs"] == ["principal:a", "principal:b"]
    assert aggregated["actionable_capabilities"][0]["compromise_seed_refs"] == ["principal:a", "principal:b"]
    assert aggregated["blocked_transitions"][0]["compromise_seed_refs"] == ["principal:a", "principal:b"]


def test_common_target_does_not_collapse_distinct_authority_paths():
    aggregated = aggregate_seeded_blast_results([
        _result("principal:a", ["edge:a"]),
        _result("principal:b", ["edge:b"]),
    ])

    assert len(aggregated["reachable_subjects"]) == 2
    assert len(aggregated["actionable_capabilities"]) == 2
    assert {tuple(item["compromise_seed_refs"]) for item in aggregated["actionable_capabilities"]} == {
        ("principal:a",),
        ("principal:b",),
    }


def test_existing_recorded_seed_provenance_is_preserved_but_not_inferred_from_connectivity():
    result = _result("principal:a", ["edge:a"])
    result["reachable_subjects"][0]["compromise_seed_refs"] = ["principal:prior"]

    aggregated = aggregate_seeded_blast_results([result])

    assert aggregated["reachable_subjects"][0]["compromise_seed_refs"] == ["principal:a", "principal:prior"]
    assert aggregated["semantics"]["material_lineage_does_not_create_seed_provenance"] is True


def test_boundary_crossings_and_truncation_are_aggregated_only_from_recorded_results():
    first = _result("principal:a", ["edge:a"])
    first["trust_boundary_crossings"] = [{
        "edge_id": "edge:a",
        "boundary_ref": "boundary:tenant",
        "path_position": 0,
        "source_ref": "principal:a",
        "target_ref": "connector:github",
    }]
    first["truncation_reasons"] = ["max_depth"]

    second = _result("principal:b", ["edge:b"])
    second["trust_boundary_crossings"] = [{
        "edge_id": "edge:b",
        "boundary_ref": "boundary:provider",
        "path_position": 1,
        "source_ref": "connector:github",
        "target_ref": "repo:exact",
    }]
    second["truncation_reasons"] = ["expansion_budget", "max_depth"]

    aggregated = aggregate_seeded_blast_results([first, second])

    assert aggregated["trust_boundary_refs"] == ["boundary:provider", "boundary:tenant"]
    assert [(item["edge_id"], item["boundary_ref"]) for item in aggregated["trust_boundary_crossings"]] == [
        ("edge:a", "boundary:tenant"),
        ("edge:b", "boundary:provider"),
    ]
    assert aggregated["truncated"] is True
    assert aggregated["truncation_reasons"] == ["expansion_budget", "max_depth"]
    assert aggregated["semantics"]["trust_boundary_crossings_are_engine_recorded_not_reconstructed"] is True
    assert aggregated["semantics"]["truncation_is_union_of_per_seed_engine_results"] is True


def test_missing_boundary_and_truncation_metadata_stays_empty_not_inferred_from_paths():
    aggregated = aggregate_seeded_blast_results([_result("principal:a", ["edge:looks-cross-boundary"])])

    assert aggregated["trust_boundary_refs"] == []
    assert aggregated["trust_boundary_crossings"] == []
    assert aggregated["truncated"] is False
    assert aggregated["truncation_reasons"] == []
