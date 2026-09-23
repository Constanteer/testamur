import pytest

from testamur.authority import TestamurAuthorityStore
from testamur.authority_reachability import _enrich_blocked


def _result(blocked):
    return {"blocked_transitions": [blocked], "semantics": {}}


def _blocked(**overrides):
    value = {
        "edge_id": "edge:final",
        "source_ref": "subject:a",
        "target_ref": "subject:b",
        "relation_type": "HAS_CAPABILITY",
        "path_edge_ids": ["edge:final"],
        "supporting_edge_ids": ["edge:final"],
        "reasons": ["denied"],
        "boundary_refs": ["boundary:one"],
        "trust_boundary_crossings": [
            {
                "edge_id": "edge:final",
                "boundary_ref": "boundary:one",
                "path_edge_ids": ["edge:final"],
            }
        ],
    }
    value.update(overrides)
    return value


def test_canonical_facade_preserves_engine_recorded_blocked_boundary_evidence(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    result = _enrich_blocked(store, _result(_blocked()))
    blocked = result["blocked_transitions"][0]
    assert blocked["boundary_refs"] == ["boundary:one"]
    assert blocked["trust_boundary_crossings"][0]["path_edge_ids"] == ["edge:final"]
    assert result["semantics"]["blocked_boundary_evidence_is_engine_recorded_exact_path"] is True


def test_canonical_facade_does_not_reconstruct_missing_blocked_boundary_evidence(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    blocked = _blocked()
    blocked.pop("boundary_refs")
    with pytest.raises(ValueError, match="missing exact trust-boundary evidence"):
        _enrich_blocked(store, _result(blocked))


def test_canonical_facade_rejects_crossing_from_other_connected_path(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    blocked = _blocked(
        trust_boundary_crossings=[
            {
                "edge_id": "edge:other",
                "boundary_ref": "boundary:one",
                "path_edge_ids": ["edge:other"],
            }
        ]
    )
    with pytest.raises(ValueError, match="exact attempted path"):
        _enrich_blocked(store, _result(blocked))


def test_canonical_facade_rejects_unproven_boundary_ref(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    blocked = _blocked(boundary_refs=["boundary:one", "boundary:connected-only"])
    with pytest.raises(ValueError, match="boundaries proven by exact crossings"):
        _enrich_blocked(store, _result(blocked))
