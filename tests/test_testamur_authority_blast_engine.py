from __future__ import annotations

import pytest

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_blast_engine import canonical_authority_blast_radius


def _store(tmp_path) -> TestamurAuthorityStore:
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    for ref in ("principal:a", "principal:b"):
        store.upsert_subject(subject_ref=ref, kind=AuthoritySubjectKind.PRINCIPAL)
    store.upsert_subject(subject_ref="resource:r", kind=AuthoritySubjectKind.RESOURCE)
    store.add_edge(
        edge_id="edge:a-read",
        source_ref="principal:a",
        target_ref="resource:r",
        relation_type=AuthorityRelationType.CAN_READ,
        capabilities=[{"namespace": "resource", "action": "read"}],
        evidence=[{"evidence_class": "OBSERVED", "ref": "evidence:a"}],
    )
    store.add_edge(
        edge_id="edge:b-read",
        source_ref="principal:b",
        target_ref="resource:r",
        relation_type=AuthorityRelationType.CAN_READ,
        capabilities=[{"namespace": "resource", "action": "read"}],
        evidence=[{"evidence_class": "OBSERVED", "ref": "evidence:b"}],
    )
    return store


def test_canonical_blast_keeps_seed_provenance_bound_to_exact_path(tmp_path):
    result = canonical_authority_blast_radius(
        _store(tmp_path),
        ["principal:b", "principal:a"],
        compromise_model="FULL_SUBJECT_COMPROMISE",
    )

    assert result["compromised_refs"] == ["principal:a", "principal:b"]
    actions = [item for item in result["actionable_capabilities"] if item["target_ref"] == "resource:r"]
    assert len(actions) == 2
    by_path = {tuple(item["path_edge_ids"]): item["compromise_seed_refs"] for item in actions}
    assert by_path[("edge:a-read",)] == ["principal:a"]
    assert by_path[("edge:b-read",)] == ["principal:b"]
    assert result["semantics"]["material_lineage_does_not_create_seed_provenance"] is True


def test_canonical_blast_rejects_empty_seed_set(tmp_path):
    with pytest.raises(ValueError, match="compromised_refs"):
        canonical_authority_blast_radius(
            _store(tmp_path),
            [],
            compromise_model="FULL_SUBJECT_COMPROMISE",
        )
