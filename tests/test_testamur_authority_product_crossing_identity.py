from testamur.authority_product_projection import project_authority_diagnostics


def _result(crossings):
    return {
        "blocked_transitions": [],
        "trust_boundary_refs": ["boundary:provider"],
        "trust_boundary_crossings": crossings,
    }


def test_product_projection_keeps_same_boundary_edge_on_distinct_exact_paths():
    first = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:provider",
        "path_position": 1,
        "path_edge_ids": ["edge:a-delegates", "edge:provider"],
        "compromise_seed_refs": ["principal:a"],
    }
    second = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:provider",
        "path_position": 1,
        "path_edge_ids": ["edge:b-delegates", "edge:provider"],
        "compromise_seed_refs": ["principal:b"],
    }

    projected = project_authority_diagnostics(_result([second, first]))

    crossings = projected["trust_boundary_crossings"]
    assert len(crossings) == 2
    assert [item["path_edge_ids"] for item in crossings] == [
        ["edge:a-delegates", "edge:provider"],
        ["edge:b-delegates", "edge:provider"],
    ]
    assert crossings[0]["compromise_seed_refs"] == ["principal:a"]
    assert crossings[1]["compromise_seed_refs"] == ["principal:b"]
    assert projected["semantics"]["trust_boundary_crossings_preserve_exact_path_identity"] is True


def test_product_projection_does_not_reconstruct_missing_crossing_path_or_seed():
    crossing = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:provider",
        "path_position": 0,
    }

    projected = project_authority_diagnostics(_result([crossing]))
    item = projected["trust_boundary_crossings"][0]

    assert item["path_edge_ids"] == []
    assert item["compromise_seed_refs"] == []
