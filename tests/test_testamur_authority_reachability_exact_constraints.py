from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_reachability


OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind, *, attributes=None):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes=attributes or {})


def _cap():
    return {
        "namespace": "github",
        "action": "contents.read",
        "resource": "repo:Constanteer/testamur",
        "constraints": {},
    }


def test_exact_resource_constraint_can_unlock_action(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "connector:github", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "repo:Constanteer/testamur", AuthoritySubjectKind.REPOSITORY)
    store.record_edge(
        "connector:github",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo:Constanteer/testamur",
        capabilities=[_cap()],
        constraints={"resource": "repo:Constanteer/testamur"},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "connector:github",
        compromise_model=CompromiseModel.CONNECTOR_TAKEOVER,
    )

    assert [item["target_ref"] for item in result["actionable_capabilities"]] == [
        "repo:Constanteer/testamur"
    ]
    assert result["blocked_transitions"] == []


def test_wrong_exact_resource_remains_blocked(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "connector:github", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "repo:Constanteer/testamur", AuthoritySubjectKind.REPOSITORY)
    store.record_edge(
        "connector:github",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo:Constanteer/testamur",
        capabilities=[_cap()],
        constraints={"resource": "repo:Constanteer/other"},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "connector:github",
        compromise_model=CompromiseModel.CONNECTOR_TAKEOVER,
    )

    assert result["actionable_capabilities"] == []
    assert result["blocked_transitions"][0]["reasons"] == ["resource_mismatch"]


def test_exact_principal_constraint_uses_source_identity(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "connector:github", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "repo:Constanteer/testamur", AuthoritySubjectKind.REPOSITORY)
    store.record_edge(
        "connector:github",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo:Constanteer/testamur",
        capabilities=[_cap()],
        constraints={"principal": "connector:github"},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "connector:github",
        compromise_model=CompromiseModel.CONNECTOR_TAKEOVER,
    )

    assert len(result["actionable_capabilities"]) == 1


def test_runtime_only_gate_stays_unresolved_in_reachability(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "connector:github", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "repo:Constanteer/testamur", AuthoritySubjectKind.REPOSITORY)
    store.record_edge(
        "connector:github",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo:Constanteer/testamur",
        capabilities=[_cap()],
        constraints={"resource": "repo:Constanteer/testamur", "device_binding": "device:ci-runner"},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "connector:github",
        compromise_model=CompromiseModel.CONNECTOR_TAKEOVER,
    )

    assert result["actionable_capabilities"] == []
    blocked = result["blocked_transitions"][0]
    assert blocked["reasons"] == []
    assert blocked["unresolved_constraints"] == ["device_binding"]
