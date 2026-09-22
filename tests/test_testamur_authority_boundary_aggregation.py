from __future__ import annotations

import pytest

from testamur.authority_boundaries import aggregate_trust_boundary_crossings


def _crossing(path: list[str], seed: str | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:github",
        "path_position": len(path) - 1,
        "path_edge_ids": path,
        "source_ref": "connector:github",
        "target_ref": "service:github",
        "relation_type": "CAN_CONNECT",
    }
    if seed is not None:
        item["compromise_seed_refs"] = [seed]
    return item


def test_different_authority_paths_do_not_collapse_at_same_boundary_edge() -> None:
    crossings = aggregate_trust_boundary_crossings(
        [
            _crossing(["edge:a-to-connector", "edge:provider"], "principal:a"),
            _crossing(["edge:b-to-connector", "edge:provider"], "principal:b"),
        ]
    )

    assert len(crossings) == 2
    assert {tuple(item["path_edge_ids"]) for item in crossings} == {
        ("edge:a-to-connector", "edge:provider"),
        ("edge:b-to-connector", "edge:provider"),
    }


def test_identical_recorded_path_may_union_only_recorded_seed_provenance() -> None:
    path = ["edge:a-to-connector", "edge:provider"]
    crossings = aggregate_trust_boundary_crossings(
        [_crossing(path, "principal:b"), _crossing(path, "principal:a")]
    )

    assert len(crossings) == 1
    assert crossings[0]["compromise_seed_refs"] == ["principal:a", "principal:b"]


def test_missing_path_stays_missing_instead_of_being_reconstructed() -> None:
    crossing = _crossing([], "principal:a")
    crossing["path_position"] = 0
    result = aggregate_trust_boundary_crossings([crossing])

    assert result[0]["path_edge_ids"] == []


def test_malformed_seed_provenance_fails_closed() -> None:
    crossing = _crossing(["edge:provider"])
    crossing["compromise_seed_refs"] = "principal:a"

    with pytest.raises(ValueError, match="compromise_seed_refs"):
        aggregate_trust_boundary_crossings([crossing])
