from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_boundaries import boundary_refs_from_crossings, project_trust_boundary_crossings


OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes={})


def test_crossings_are_projected_from_exact_traversed_edges_only(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "account", AuthoritySubjectKind.ACCOUNT)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)

    delegated = store.record_edge(
        "connector",
        AuthorityRelationType.DELEGATES,
        "account",
        evidence=OBSERVED,
        boundary_refs=["boundary:sso", "boundary:github"],
        capabilities=[{
            "namespace": "github",
            "action": "contents.read",
            "resource": "repo:Constanteer/testamur",
            "constraints": {"required_scopes": ["repo:read"]},
        }],
    )
    unrelated = store.record_edge(
        "account",
        AuthorityRelationType.CAN_READ,
        "repo",
        evidence=OBSERVED,
        boundary_refs=["boundary:repo"],
    )

    crossings = project_trust_boundary_crossings(store, [delegated["edge_id"]])
    assert [(item["edge_id"], item["boundary_ref"]) for item in crossings] == [
        (delegated["edge_id"], "boundary:sso"),
        (delegated["edge_id"], "boundary:github"),
    ]
    assert boundary_refs_from_crossings(crossings) == ["boundary:github", "boundary:sso"]
    assert "boundary:repo" not in boundary_refs_from_crossings(crossings)
    assert unrelated["edge_id"] not in {item["edge_id"] for item in crossings}


def test_connectivity_does_not_create_a_boundary_crossing_without_edge_evidence(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "client", AuthoritySubjectKind.WORKLOAD)
    _subject(store, "service", AuthoritySubjectKind.SERVICE)
    edge = store.record_edge(
        "client",
        AuthorityRelationType.CAN_CONNECT,
        "service",
        evidence=OBSERVED,
    )

    assert project_trust_boundary_crossings(store, [edge["edge_id"]]) == []
