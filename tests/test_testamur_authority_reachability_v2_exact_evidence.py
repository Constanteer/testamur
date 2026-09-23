import pytest

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability_v2 import CompromiseModel, authority_reachability


OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes={})


def _blocked_store(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "workload", AuthoritySubjectKind.WORKLOAD)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    edge = store.record_edge(
        "workload",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo",
        evidence=OBSERVED,
        boundary_refs=["boundary:raw-v2"],
        capabilities=[],
    )
    return store, edge


def test_raw_v2_blocked_transition_preserves_exact_boundary_provenance(tmp_path):
    store, edge = _blocked_store(tmp_path)
    result = authority_reachability(
        store,
        "workload",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        as_of="2026-09-23T00:00:00Z",
    )

    blocked = next(item for item in result["blocked_transitions"] if item["edge_id"] == edge["edge_id"])
    assert blocked["path_edge_ids"] == [edge["edge_id"]]
    assert blocked["boundary_refs"] == ["boundary:raw-v2"]
    assert [(item["edge_id"], item["boundary_ref"]) for item in blocked["trust_boundary_crossings"]] == [
        (edge["edge_id"], "boundary:raw-v2")
    ]

    # Blocked-local attempted-path evidence is not successful authority and must
    # not enter the result-global reachability/blast-radius crossing aggregate.
    assert result["trust_boundary_refs"] == []
    assert result["trust_boundary_crossings"] == []


def test_raw_v2_capability_filter_rejects_stringification_as_authority_selector(tmp_path):
    store, _ = _blocked_store(tmp_path)
    with pytest.raises(ValueError, match="namespace/action values must be non-empty strings"):
        authority_reachability(
            store,
            "workload",
            compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
            capability_filter=[(123, "read")],
            as_of="2026-09-23T00:00:00Z",
        )


def test_raw_v2_explicit_empty_filter_is_not_wildcard(tmp_path):
    store, _ = _blocked_store(tmp_path)
    result = authority_reachability(
        store,
        "workload",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        capability_filter=[],
        as_of="2026-09-23T00:00:00Z",
    )
    assert result["actionable_capabilities"] == []
