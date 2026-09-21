from __future__ import annotations

from testamur.authority_boundaries import trust_boundary_crossing_identity


def test_boundary_crossing_identity_includes_exact_authority_path() -> None:
    left = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:github",
        "path_position": 1,
        "path_edge_ids": ["edge:a-to-connector", "edge:provider"],
    }
    right = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:github",
        "path_position": 1,
        "path_edge_ids": ["edge:b-to-connector", "edge:provider"],
    }

    assert trust_boundary_crossing_identity(left) != trust_boundary_crossing_identity(right)


def test_boundary_crossing_identity_does_not_reconstruct_missing_path() -> None:
    crossing = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:github",
        "path_position": 0,
    }

    assert trust_boundary_crossing_identity(crossing) == (
        "edge:provider",
        "boundary:github",
        (),
        0,
    )
