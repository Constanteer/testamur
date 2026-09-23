from __future__ import annotations

import pytest

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_blast_radius, authority_reachability


OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _store(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    store.record_subject(AuthoritySubjectKind.WORKLOAD, label="workload", subject_ref="workload", attributes={})
    store.record_subject(AuthoritySubjectKind.REPOSITORY, label="repo", subject_ref="repo", attributes={})
    store.record_edge(
        "workload",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo",
        evidence=OBSERVED,
        capabilities=[{"namespace": "repo", "action": "write"}],
    )
    return store


def test_canonical_reachability_rejects_coerced_capability_filter(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        authority_reachability(
            store,
            "workload",
            compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
            capability_filter=[(7, "write")],
            as_of="2026-09-23T00:00:00Z",
        )


def test_canonical_blast_radius_rejects_mapping_as_filter_entry(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        authority_blast_radius(
            store,
            "workload",
            compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
            capability_filter=[{"namespace": "repo", "action": "write"}],
            as_of="2026-09-23T00:00:00Z",
        )


def test_explicit_empty_filter_remains_empty_not_wildcard(tmp_path):
    store = _store(tmp_path)
    result = authority_reachability(
        store,
        "workload",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        capability_filter=[],
        as_of="2026-09-23T00:00:00Z",
    )
    assert result["actionable_capabilities"] == []
    assert result["semantics"]["capability_filter_is_selector_not_authority_evidence"] is True
