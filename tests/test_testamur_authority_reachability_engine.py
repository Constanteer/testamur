from __future__ import annotations

import testamur
import testamur.authority_reachability_engine as engine


def test_package_reachability_uses_canonical_projection() -> None:
    assert testamur.authority_reachability is engine.canonical_authority_reachability


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
        return {
            "schema_version": "testamur.authority-reachability.v1",
            "starting_subject_ref": "principal:a",
            "compromise_model": "FULL_SUBJECT_COMPROMISE",
            "as_of": "2026-09-22T00:00:00Z",
            "reachable_subjects": [
                {"subject_ref": "resource:x", "trust_boundary_crossings": [crossing_a]},
                {"subject_ref": "resource:y", "trust_boundary_crossings": [crossing_b]},
            ],
            "actionable_capabilities": [],
            "trust_boundary_crossings": [crossing_b],
            "trust_boundary_refs": ["boundary:provider"],
            "semantics": {},
        }

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


def test_canonical_projection_does_not_invent_crossings(monkeypatch) -> None:
    def fake_reachability(*args, **kwargs):
        return {
            "schema_version": "testamur.authority-reachability.v1",
            "starting_subject_ref": "principal:a",
            "compromise_model": "FULL_SUBJECT_COMPROMISE",
            "as_of": "2026-09-22T00:00:00Z",
            "reachable_subjects": [{"subject_ref": "resource:x"}],
            "actionable_capabilities": [],
            "trust_boundary_crossings": [{"edge_id": "invented", "boundary_ref": "invented"}],
            "trust_boundary_refs": ["invented"],
            "semantics": {},
        }

    monkeypatch.setattr(engine.reachability_v2, "authority_reachability", fake_reachability)
    result = engine.canonical_authority_reachability(
        object(), "principal:a", compromise_model="FULL_SUBJECT_COMPROMISE"
    )

    assert result["trust_boundary_crossings"] == []
    assert result["trust_boundary_refs"] == []
