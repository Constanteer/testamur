from __future__ import annotations

import pytest

from testamur.authority_boundaries import (
    aggregate_trust_boundary_crossings,
    boundary_refs_from_crossings,
    trust_boundary_crossing_identity,
)


def _crossing(**overrides):
    value = {
        "edge_id": "edge:1",
        "boundary_ref": "boundary:tenant",
        "path_edge_ids": ["edge:1"],
        "path_position": 0,
    }
    value.update(overrides)
    return value


def test_boundary_identity_preserves_exact_authority_path():
    assert trust_boundary_crossing_identity(_crossing()) == (
        "edge:1",
        "boundary:tenant",
        ("edge:1",),
        0,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("edge_id", 1),
        ("boundary_ref", {"ref": "boundary:tenant", "connected": True}),
        ("path_edge_ids", [7]),
        ("path_edge_ids", "edge:1"),
        ("path_edge_ids", None),
        ("path_position", "0"),
        ("path_position", True),
    ],
)
def test_boundary_identity_rejects_typed_null_or_coerced_evidence(field, value):
    with pytest.raises(ValueError):
        trust_boundary_crossing_identity(_crossing(**{field: value}))


def test_boundary_identity_allows_truly_absent_path_evidence_without_inference():
    crossing = _crossing()
    del crossing["path_edge_ids"]
    assert trust_boundary_crossing_identity(crossing) == (
        "edge:1",
        "boundary:tenant",
        (),
        0,
    )


def test_boundary_projection_rejects_connectivity_shaped_boundary_ref():
    with pytest.raises(ValueError):
        boundary_refs_from_crossings([
            {"boundary_ref": {"ref": "boundary:tenant", "connected": True}}
        ])


def test_boundary_aggregation_requires_exact_compromise_seed_provenance():
    with pytest.raises(ValueError):
        aggregate_trust_boundary_crossings([
            _crossing(compromise_seed_refs=[{"subject_ref": "actor:one", "affected": True}])
        ])


def test_boundary_aggregation_rejects_explicit_null_seed_provenance():
    with pytest.raises(ValueError):
        aggregate_trust_boundary_crossings([_crossing(compromise_seed_refs=None)])


def test_boundary_aggregation_does_not_invent_missing_seed_provenance():
    aggregated = aggregate_trust_boundary_crossings([_crossing()])
    assert "compromise_seed_refs" not in aggregated[0]


def test_boundary_aggregation_unions_only_explicit_exact_seed_refs():
    first = _crossing(compromise_seed_refs=["actor:one"])
    second = _crossing(compromise_seed_refs=["actor:two", "actor:one"])
    aggregated = aggregate_trust_boundary_crossings([first, second])
    assert aggregated[0]["compromise_seed_refs"] == ["actor:one", "actor:two"]
