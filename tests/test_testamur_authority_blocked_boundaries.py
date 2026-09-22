from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_reachability


OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes={})


def test_blocked_transition_keeps_boundary_evidence_from_exact_rejected_path(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "workload", AuthoritySubjectKind.WORKLOAD)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    _subject(store, "other", AuthoritySubjectKind.REPOSITORY)

    rejected = store.record_edge(
        "workload",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo",
        evidence=OBSERVED,
        boundary_refs=["boundary:connector", "boundary:repo"],
        capabilities=[],
    )
    unrelated = store.record_edge(
        "workload",
        AuthorityRelationType.CAN_READ,
        "other",
        evidence=OBSERVED,
        boundary_refs=["boundary:unrelated"],
    )

    result = authority_reachability(
        store,
        "workload",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        as_of="2026-09-22T14:00:00Z",
    )

    blocked = next(item for item in result["blocked_transitions"] if item["edge_id"] == rejected["edge_id"])
    assert blocked["path_edge_ids"] == [rejected["edge_id"]]
    assert blocked["boundary_refs"] == ["boundary:connector", "boundary:repo"]
    assert {(item["edge_id"], item["boundary_ref"]) for item in blocked["trust_boundary_crossings"]} == {
        (rejected["edge_id"], "boundary:connector"),
        (rejected["edge_id"], "boundary:repo"),
    }
    assert "boundary:unrelated" not in blocked["boundary_refs"]
    assert unrelated["edge_id"] not in {
        item["edge_id"] for item in blocked["trust_boundary_crossings"]
    }
    assert result["semantics"]["blocked_boundary_evidence_uses_exact_recorded_path_only"] is True
    assert result["semantics"]["blocked_transition_does_not_grant_authority"] is True
