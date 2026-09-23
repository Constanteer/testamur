from __future__ import annotations

import pytest

from testamur.authority import TestamurAuthorityStore
from testamur.authority_reachability import (
    CompromiseModel,
    authority_blast_radius,
    authority_reachability,
)


def test_canonical_reachability_rejects_typed_seed_before_graph_lookup(tmp_path) -> None:
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    with pytest.raises(ValueError, match="starting_subject_ref must be an exact non-empty string"):
        authority_reachability(
            store,
            {"subject_ref": "subject:a", "connected": True},
            compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        )


def test_canonical_blast_radius_rejects_affectedness_shaped_seed(tmp_path) -> None:
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    with pytest.raises(ValueError):
        authority_blast_radius(
            store,
            [{"subject_ref": "subject:a", "affected": True}],
            compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        )


def test_canonical_blast_radius_preserves_explicit_seed_assumption(tmp_path) -> None:
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    result = authority_blast_radius(
        store,
        ["subject:a", "subject:a"],
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
    )
    assert result["compromised_refs"] == ["subject:a"]
    assert result["semantics"]["affectedness_does_not_automatically_seed_compromise"] is True
    assert result["semantics"]["material_lineage_does_not_grant_authority"] is True
    assert result["semantics"]["compromise_seeds_are_explicit_authority_assumptions"] is True
