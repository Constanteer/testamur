from __future__ import annotations

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_reachability

OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind, *, attributes=None):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes=attributes or {})


def _cap(action: str) -> dict:
    return {"namespace": "github", "action": action, "resource": "repo:private"}


def _store(tmp_path, *, token_scopes):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "session", AuthoritySubjectKind.SESSION)
    _subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    _subject(
        store,
        "token",
        AuthoritySubjectKind.TOKEN,
        attributes={"audience": "service:github", "scopes": token_scopes},
    )
    _subject(store, "service:github", AuthoritySubjectKind.SERVICE)
    _subject(store, "account", AuthoritySubjectKind.PRINCIPAL)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    return store


def test_acceptance_edge_proves_service_but_cannot_expand_delegated_budget(tmp_path):
    store = _store(tmp_path, token_scopes=["repo:read", "repo:admin"])
    allowed = _cap("repo.read")
    forbidden = _cap("repo.admin")

    store.record_edge(
        "session", AuthorityRelationType.DELEGATES, "connector",
        capabilities=[allowed], evidence=OBSERVED,
    )
    store.record_edge(
        "connector", AuthorityRelationType.EXPOSES, "token", evidence=OBSERVED,
    )
    auth_edge = store.record_edge(
        "token", AuthorityRelationType.CAN_AUTHENTICATE_AS, "account",
        constraints={"service_ref": "service:github", "required_audience": "service:github", "required_scopes": ["repo:read"]},
        evidence=OBSERVED,
    )
    acceptance_edge = store.record_edge(
        "service:github", AuthorityRelationType.ACCEPTS_CREDENTIAL, "token",
        constraints={"required_audience": "service:github", "required_scopes": ["repo:read"]},
        evidence=OBSERVED,
    )
    store.record_edge(
        "account", AuthorityRelationType.HAS_CAPABILITY, "repo",
        capabilities=[allowed, forbidden], evidence=OBSERVED,
    )

    result = authority_reachability(
        store, "session", compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER
    )
    account = next(item for item in result["reachable_subjects"] if item["subject_ref"] == "account")
    actions = [item for item in result["actionable_capabilities"] if item["target_ref"] == "repo"]

    assert account["delegated_capability_budget"] == [allowed]
    assert acceptance_edge["edge_id"] in account["supporting_edge_ids"]
    assert auth_edge["edge_id"] in account["path_edge_ids"]
    assert [item["capability"]["action"] for item in actions] == ["repo.read"]


def test_service_acceptance_with_insufficient_scope_blocks_authentication(tmp_path):
    store = _store(tmp_path, token_scopes=["repo:read"])
    allowed = _cap("repo.read")

    store.record_edge(
        "session", AuthorityRelationType.DELEGATES, "connector",
        capabilities=[allowed], evidence=OBSERVED,
    )
    store.record_edge("connector", AuthorityRelationType.EXPOSES, "token", evidence=OBSERVED)
    auth_edge = store.record_edge(
        "token", AuthorityRelationType.CAN_AUTHENTICATE_AS, "account",
        constraints={"service_ref": "service:github"}, evidence=OBSERVED,
    )
    store.record_edge(
        "service:github", AuthorityRelationType.ACCEPTS_CREDENTIAL, "token",
        constraints={"required_audience": "service:github", "required_scopes": ["repo:admin"]},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store, "session", compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER
    )

    assert not any(item["subject_ref"] == "account" for item in result["reachable_subjects"])
    blocked = next(item for item in result["blocked_paths"] if item["edge_id"] == auth_edge["edge_id"])
    assert "credential_acceptance_constraints_unsatisfied" in blocked["reasons"]
    assert "scope_mismatch" in blocked["reasons"]


def test_service_ref_without_explicit_acceptance_edge_fails_closed(tmp_path):
    store = _store(tmp_path, token_scopes=["repo:read"])
    allowed = _cap("repo.read")

    store.record_edge("session", AuthorityRelationType.DELEGATES, "connector", capabilities=[allowed], evidence=OBSERVED)
    store.record_edge("connector", AuthorityRelationType.EXPOSES, "token", evidence=OBSERVED)
    auth_edge = store.record_edge(
        "token", AuthorityRelationType.CAN_AUTHENTICATE_AS, "account",
        constraints={"service_ref": "service:github"}, evidence=OBSERVED,
    )
    # CAN_CONNECT is deliberately not acceptance evidence.
    store.record_edge("connector", AuthorityRelationType.CAN_CONNECT, "service:github", evidence=OBSERVED)

    result = authority_reachability(
        store, "session", compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER
    )

    assert not any(item["subject_ref"] == "account" for item in result["reachable_subjects"])
    blocked = next(item for item in result["blocked_paths"] if item["edge_id"] == auth_edge["edge_id"])
    assert blocked["reasons"] == ["credential_acceptance_not_established"]
