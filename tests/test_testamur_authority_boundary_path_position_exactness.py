from __future__ import annotations

import pytest

from testamur.authority_boundaries import trust_boundary_crossing_identity


def _crossing(**overrides):
    value = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:github",
        "path_position": 1,
        "path_edge_ids": ["edge:connector", "edge:provider"],
    }
    value.update(overrides)
    return value


def test_crossing_requires_explicit_path_position_evidence() -> None:
    crossing = _crossing()
    del crossing["path_position"]
    with pytest.raises(ValueError, match="explicitly recorded"):
        trust_boundary_crossing_identity(crossing)


def test_crossing_rejects_position_outside_exact_recorded_path() -> None:
    with pytest.raises(ValueError, match="identify an edge"):
        trust_boundary_crossing_identity(_crossing(path_position=2))


def test_crossing_rejects_edge_position_mismatch() -> None:
    with pytest.raises(ValueError, match="edge at crossing.path_position"):
        trust_boundary_crossing_identity(_crossing(path_position=0))


def test_crossing_accepts_exact_edge_at_recorded_position() -> None:
    assert trust_boundary_crossing_identity(_crossing()) == (
        "edge:provider",
        "boundary:github",
        ("edge:connector", "edge:provider"),
        1,
    )


def test_missing_path_stays_missing_without_connectivity_reconstruction() -> None:
    crossing = _crossing(path_position=0)
    del crossing["path_edge_ids"]
    assert trust_boundary_crossing_identity(crossing) == (
        "edge:provider",
        "boundary:github",
        (),
        0,
    )
