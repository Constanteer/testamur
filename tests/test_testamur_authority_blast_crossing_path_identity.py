from __future__ import annotations

from testamur.authority_blast_provenance import aggregate_seeded_blast_results


def _result(seed: str, path: list[str]) -> dict:
    return {
        "starting_subject_ref": seed,
        "reachable_subjects": [],
        "actionable_capabilities": [],
        "blocked_transitions": [],
        "trust_boundary_crossings": [
            {
                "edge_id": "edge:provider-call",
                "boundary_ref": "boundary:external-provider",
                "path_position": len(path) - 1,
                "path_edge_ids": path,
                "source_ref": "connector:github",
                "target_ref": "service:github",
                "relation_type": "CAN_CONNECT",
            }
        ],
        "truncation_reasons": [],
    }


def test_same_boundary_edge_on_distinct_authority_paths_is_not_merged() -> None:
    aggregated = aggregate_seeded_blast_results(
        [
            _result("principal:a", ["edge:a-to-connector", "edge:provider-call"]),
            _result("principal:b", ["edge:b-to-connector", "edge:provider-call"]),
        ]
    )

    crossings = aggregated["trust_boundary_crossings"]
    assert len(crossings) == 2
    assert {tuple(item["path_edge_ids"]) for item in crossings} == {
        ("edge:a-to-connector", "edge:provider-call"),
        ("edge:b-to-connector", "edge:provider-call"),
    }
    assert {tuple(item["compromise_seed_refs"]) for item in crossings} == {
        ("principal:a",),
        ("principal:b",),
    }
    assert aggregated["semantics"]["trust_boundary_crossings_preserve_exact_path_identity"] is True


def test_identical_crossing_path_unions_only_recorded_seed_provenance() -> None:
    path = ["edge:shared-connector", "edge:provider-call"]
    aggregated = aggregate_seeded_blast_results(
        [_result("principal:a", path), _result("principal:b", path)]
    )

    assert len(aggregated["trust_boundary_crossings"]) == 1
    crossing = aggregated["trust_boundary_crossings"][0]
    assert crossing["path_edge_ids"] == path
    assert crossing["compromise_seed_refs"] == ["principal:a", "principal:b"]
