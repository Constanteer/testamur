from __future__ import annotations

import pytest

from testamur.authority_blocked import blocked_transition_record


def _record(**overrides):
    values = {
        "edge_id": "edge:2",
        "source_ref": "principal:alice",
        "target_ref": "service:repo",
        "relation_type": "HAS_CAPABILITY",
        "path_edge_ids": ["edge:1", "edge:2"],
        "supporting_edge_ids": [],
        "reasons": ["missing_explicit_or_authorized_capability"],
        "unresolved_constraints": [],
        "reachability_class": "UNKNOWN",
        "evidence_state": "CORROBORATED",
        "boundary_refs": ["boundary:prod"],
        "trust_boundary_crossings": [
            {
                "edge_id": "edge:2",
                "boundary_ref": "boundary:prod",
                "path_position": 1,
                "path_edge_ids": ["edge:1", "edge:2"],
            }
        ],
    }
    values.update(overrides)
    return blocked_transition_record(**values)


def test_blocked_record_preserves_exact_attempted_path_boundary_evidence():
    item = _record()

    assert item["path_edge_ids"] == ["edge:1", "edge:2"]
    assert item["boundary_refs"] == ["boundary:prod"]
    assert item["trust_boundary_crossings"][0]["path_edge_ids"] == item["path_edge_ids"]


def test_blocked_record_rejects_crossing_from_another_connected_path():
    with pytest.raises(ValueError, match="exact attempted path"):
        _record(
            trust_boundary_crossings=[
                {
                    "edge_id": "edge:other",
                    "boundary_ref": "boundary:prod",
                    "path_position": 0,
                    "path_edge_ids": ["edge:other"],
                }
            ]
        )


def test_blocked_record_rejects_boundary_refs_not_proven_by_crossings():
    with pytest.raises(ValueError, match="exactly match"):
        _record(boundary_refs=["boundary:prod", "boundary:unrelated"])


def test_blocked_record_allows_no_boundary_without_inference():
    item = _record(boundary_refs=[], trust_boundary_crossings=[])

    assert item["boundary_refs"] == []
    assert item["trust_boundary_crossings"] == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("path_edge_ids", ["edge:1", 2]),
        ("supporting_edge_ids", [object()]),
        ("boundary_refs", [7]),
        ("path_edge_ids", "edge:1"),
    ],
)
def test_blocked_record_rejects_non_string_or_scalar_provenance(field, value):
    with pytest.raises(ValueError, match="exact string refs"):
        _record(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("edge_id", 2),
        ("source_ref", object()),
        ("target_ref", ""),
        ("relation_type", 7),
        ("reachability_class", None),
        ("evidence_state", " "),
    ],
)
def test_blocked_record_rejects_coerced_or_empty_identity_fields(field, value):
    with pytest.raises(ValueError, match="non-empty exact string ref"):
        _record(**{field: value})


def test_blocked_record_requires_terminal_edge_to_match_attempted_path():
    with pytest.raises(ValueError, match="terminal edge"):
        _record(edge_id="edge:other")


@pytest.mark.parametrize("field", ["reasons", "unresolved_constraints"])
def test_blocked_record_rejects_scalar_reason_collections(field):
    with pytest.raises(ValueError, match="sequence of exact strings"):
        _record(**{field: "not-a-sequence"})


def test_blocked_record_rejects_non_mapping_crossing_without_coercion():
    with pytest.raises(ValueError, match="mapping records"):
        _record(trust_boundary_crossings=["boundary:prod"])
