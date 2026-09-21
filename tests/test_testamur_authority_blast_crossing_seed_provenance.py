from testamur.authority_blast_provenance import aggregate_seeded_blast_results


def _result(seed: str, *, crossing: dict | None = None) -> dict:
    return {
        "starting_subject_ref": seed,
        "reachable_subjects": [],
        "actionable_capabilities": [],
        "blocked_transitions": [],
        "trust_boundary_crossings": [] if crossing is None else [crossing],
        "truncation_reasons": [],
    }


def test_same_recorded_crossing_unions_only_actual_seed_provenance() -> None:
    crossing = {
        "edge_id": "edge:connector-to-provider",
        "boundary_ref": "boundary:provider",
        "path_position": 1,
        "source_ref": "connector:github",
        "target_ref": "service:github",
    }
    aggregated = aggregate_seeded_blast_results([
        _result("principal:a", crossing=crossing),
        _result("principal:b", crossing=crossing),
        _result("principal:c"),
    ])

    assert aggregated["trust_boundary_crossings"] == [{
        **crossing,
        "compromise_seed_refs": ["principal:a", "principal:b"],
    }]
    assert aggregated["trust_boundary_refs"] == ["boundary:provider"]
    assert "principal:c" not in aggregated["trust_boundary_crossings"][0]["compromise_seed_refs"]


def test_crossing_provenance_is_not_inferred_from_global_connectivity() -> None:
    aggregated = aggregate_seeded_blast_results([
        _result("principal:a"),
        _result("principal:b"),
    ])

    assert aggregated["trust_boundary_crossings"] == []
    assert aggregated["trust_boundary_refs"] == []
    assert aggregated["semantics"]["trust_boundary_crossing_seed_provenance_is_engine_recorded"] is True
