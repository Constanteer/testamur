from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_blast_radius, authority_reachability


OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes={})


def _store(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "workload", AuthoritySubjectKind.WORKLOAD)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    rejected = store.record_edge(
        "workload",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo",
        evidence=OBSERVED,
        boundary_refs=["boundary:blocked-only"],
        capabilities=[],
    )
    return store, rejected


def _assert_blocked_local_but_not_global(result, edge_id):
    blocked = next(item for item in result["blocked_transitions"] if item["edge_id"] == edge_id)
    assert blocked["boundary_refs"] == ["boundary:blocked-only"]
    assert [(item["edge_id"], item["boundary_ref"]) for item in blocked["trust_boundary_crossings"]] == [
        (edge_id, "boundary:blocked-only")
    ]

    # A rejected attempted authority path keeps its own exact crossing provenance,
    # but it must not inflate the successful reachability/actionability aggregate.
    assert "boundary:blocked-only" not in result["trust_boundary_refs"]
    assert all(
        item["boundary_ref"] != "boundary:blocked-only"
        for item in result["trust_boundary_crossings"]
    )


def test_blocked_only_boundary_does_not_enter_reachability_global_crossings(tmp_path):
    store, rejected = _store(tmp_path)
    result = authority_reachability(
        store,
        "workload",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        as_of="2026-09-23T00:00:00Z",
    )
    _assert_blocked_local_but_not_global(result, rejected["edge_id"])


def test_blocked_only_boundary_does_not_inflate_blast_radius_global_crossings(tmp_path):
    store, rejected = _store(tmp_path)
    result = authority_blast_radius(
        store,
        "workload",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
        as_of="2026-09-23T00:00:00Z",
    )
    _assert_blocked_local_but_not_global(result, rejected["edge_id"])
