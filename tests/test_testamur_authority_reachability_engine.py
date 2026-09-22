from __future__ import annotations

from datetime import datetime

import pytest

import testamur
import testamur.authority_reachability_engine as engine


def test_package_reachability_uses_canonical_projection() -> None:
    assert testamur.authority_reachability is engine.canonical_authority_reachability


def _base_result() -> dict:
    return {
        "schema_version": "testamur.authority-reachability.v1",
        "starting_subject_ref": "principal:a",
        "compromise_model": "FULL_SUBJECT_COMPROMISE",
        "as_of": "2026-09-22T00:00:00Z",
        "reachable_subjects": [],
        "actionable_capabilities": [],
        "trust_boundary_crossings": [],
        "trust_boundary_refs": [],
        "semantics": {},
    }


def test_canonical_projection_preserves_distinct_exact_crossing_paths(monkeypatch) -> None:
    crossing_a = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:provider",
        "path_position": 1,
        "path_edge_ids": ["edge:a", "edge:provider"],
    }
    crossing_b = {
        "edge_id": "edge:provider",
        "boundary_ref": "boundary:provider",
        "path_position": 1,
        "path_edge_ids": ["edge:b", "edge:provider"],
    }

    def fake_reachability(*args, **kwargs):
        result = _base_result()
        result["reachable_subjects"] = [
            {"subject_ref": "resource:x", "path_edge_ids": crossing_a["path_edge_ids"], "trust_boundary_crossings": [crossing_a]},
            {"subject_ref": "resource:y", "path_edge_ids": crossing_b["path_edge_ids"], "trust_boundary_crossings": [crossing_b]},
        ]
        result["trust_boundary_crossings"] = [crossing_b]
        result["trust_boundary_refs"] = ["boundary:provider"]
        return result

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    result = engine.canonical_authority_reachability(
        object(), "principal:a", compromise_model="FULL_SUBJECT_COMPROMISE"
    )

    assert [item["path_edge_ids"] for item in result["trust_boundary_crossings"]] == [
        ["edge:a", "edge:provider"],
        ["edge:b", "edge:provider"],
    ]
    assert result["semantics"]["trust_boundary_crossings_preserve_exact_path_identity"] is True
    assert result["semantics"]["trust_boundary_crossings_use_canonical_aggregation"] is True
    assert result["semantics"]["trust_boundary_crossings_are_recorded_not_connectivity_inferred"] is True
    assert result["semantics"]["trust_boundary_crossings_are_bound_to_containing_exact_path"] is True
    assert result["semantics"]["reachability_result_is_bound_to_requested_seed"] is True
    assert result["semantics"]["reachability_result_is_bound_to_requested_compromise_model"] is True
    assert result["semantics"]["reachability_result_requires_canonical_schema"] is True
    assert result["semantics"]["reachability_result_records_observation_instant"] is True
    assert result["semantics"]["explicit_observation_instant_is_exactly_bound"] is True
    assert result["semantics"]["observation_instant_requires_explicit_timezone"] is True


def test_canonical_projection_does_not_invent_crossings(monkeypatch) -> None:
    def fake_reachability(*args, **kwargs):
        result = _base_result()
        result["reachable_subjects"] = [{"subject_ref": "resource:x"}]
        result["trust_boundary_crossings"] = [{"edge_id": "invented", "boundary_ref": "invented"}]
        result["trust_boundary_refs"] = ["invented"]
        return result

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    result = engine.canonical_authority_reachability(
        object(), "principal:a", compromise_model="FULL_SUBJECT_COMPROMISE"
    )

    assert result["trust_boundary_crossings"] == []
    assert result["trust_boundary_refs"] == []


@pytest.mark.parametrize(
    ("crossing", "message"),
    [
        (
            {"edge_id": "edge:provider", "boundary_ref": "boundary:p", "path_position": 1, "path_edge_ids": ["edge:other", "edge:provider"]},
            "exact path does not match",
        ),
        (
            {"edge_id": "edge:provider", "boundary_ref": "boundary:p", "path_position": 2, "path_edge_ids": ["edge:a", "edge:provider"]},
            "path position is outside",
        ),
        (
            {"edge_id": "edge:wrong", "boundary_ref": "boundary:p", "path_position": 1, "path_edge_ids": ["edge:a", "edge:provider"]},
            "edge does not match",
        ),
    ],
)
def test_canonical_projection_rejects_crossing_not_bound_to_containing_exact_path(monkeypatch, crossing, message) -> None:
    def fake_reachability(*args, **kwargs):
        result = _base_result()
        result["reachable_subjects"] = [{
            "subject_ref": "resource:x",
            "path_edge_ids": ["edge:a", "edge:provider"],
            "trust_boundary_crossings": [crossing],
        }]
        return result

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    with pytest.raises(ValueError, match=message):
        engine.canonical_authority_reachability(object(), "principal:a", compromise_model="FULL_SUBJECT_COMPROMISE")


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("schema_version", "testamur.authority-blast-radius.v1", "unsupported schema"),
        ("starting_subject_ref", "principal:b", "starting subject"),
        ("compromise_model", "READ_ONLY_COMPROMISE", "compromise model"),
        ("as_of", "", "observation instant"),
    ],
)
def test_canonical_projection_fails_closed_on_envelope_provenance_mismatch(
    monkeypatch, field, bad_value, message
) -> None:
    def fake_reachability(*args, **kwargs):
        result = _base_result()
        result[field] = bad_value
        return result

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    with pytest.raises(ValueError, match=message):
        engine.canonical_authority_reachability(
            object(), "principal:a", compromise_model="FULL_SUBJECT_COMPROMISE"
        )


def test_canonical_projection_binds_explicit_observation_instant(monkeypatch) -> None:
    def fake_reachability(*args, **kwargs):
        result = _base_result()
        result["as_of"] = "2026-09-22T08:00:00+08:00"
        return result

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    result = engine.canonical_authority_reachability(
        object(),
        "principal:a",
        compromise_model="FULL_SUBJECT_COMPROMISE",
        as_of="2026-09-22T00:00:00Z",
    )
    assert result["as_of"] == "2026-09-22T00:00:00Z"


def test_canonical_projection_rejects_different_observation_instant(monkeypatch) -> None:
    def fake_reachability(*args, **kwargs):
        result = _base_result()
        result["as_of"] = "2026-09-22T00:00:01Z"
        return result

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    with pytest.raises(ValueError, match="requested observation instant"):
        engine.canonical_authority_reachability(
            object(),
            "principal:a",
            compromise_model="FULL_SUBJECT_COMPROMISE",
            as_of="2026-09-22T00:00:00Z",
        )


@pytest.mark.parametrize(
    "ambiguous_as_of",
    ["2026-09-22T00:00:00", datetime(2026, 9, 22, 0, 0, 0)],
)
def test_canonical_projection_rejects_timezone_ambiguous_requested_instant(
    monkeypatch, ambiguous_as_of
) -> None:
    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", lambda *args, **kwargs: _base_result())
    with pytest.raises(ValueError, match="explicit timezone offset"):
        engine.canonical_authority_reachability(
            object(),
            "principal:a",
            compromise_model="FULL_SUBJECT_COMPROMISE",
            as_of=ambiguous_as_of,
        )


def test_canonical_projection_rejects_timezone_ambiguous_returned_instant(monkeypatch) -> None:
    def fake_reachability(*args, **kwargs):
        result = _base_result()
        result["as_of"] = "2026-09-22T00:00:00"
        return result

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    with pytest.raises(ValueError, match="explicit timezone offset"):
        engine.canonical_authority_reachability(
            object(), "principal:a", compromise_model="FULL_SUBJECT_COMPROMISE"
        )
