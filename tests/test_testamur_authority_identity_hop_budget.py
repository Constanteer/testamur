from __future__ import annotations

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_reachability

OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes={})


def _cap(action: str) -> dict:
    return {"namespace": "github", "action": action, "resource": "repo:private"}


def test_impersonation_hop_cannot_reset_delegated_capability_budget(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "session", AuthoritySubjectKind.SESSION)
    _subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "principal", AuthoritySubjectKind.PRINCIPAL)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)

    allowed = _cap("repo.read")
    forbidden = _cap("repo.admin")
    store.record_edge("session", AuthorityRelationType.DELEGATES, "connector", capabilities=[allowed], evidence=OBSERVED)
    store.record_edge("connector", AuthorityRelationType.CAN_IMPERSONATE, "principal", evidence=OBSERVED)
    store.record_edge("principal", AuthorityRelationType.HAS_CAPABILITY, "repo", capabilities=[allowed, forbidden], evidence=OBSERVED)

    result = authority_reachability(store, "session", compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER)
    principal = next(item for item in result["reachable_subjects"] if item["subject_ref"] == "principal")
    actions = [item["capability"]["action"] for item in result["actionable_capabilities"] if item["target_ref"] == "repo"]

    assert principal["delegated_capability_budget"] == [allowed]
    assert actions == ["repo.read"]
    assert result["semantics"]["identity_hops_do_not_reset_delegated_capability_budget"] is True


def test_authentication_hop_cannot_reset_delegated_capability_budget(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "session", AuthoritySubjectKind.SESSION)
    _subject(store, "token", AuthoritySubjectKind.TOKEN)
    _subject(store, "account", AuthoritySubjectKind.PRINCIPAL)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)

    allowed = _cap("repo.read")
    forbidden = _cap("repo.admin")
    store.record_edge("session", AuthorityRelationType.DELEGATES, "token", capabilities=[allowed], evidence=OBSERVED)
    store.record_edge("token", AuthorityRelationType.CAN_AUTHENTICATE_AS, "account", evidence=OBSERVED)
    store.record_edge("account", AuthorityRelationType.HAS_CAPABILITY, "repo", capabilities=[allowed, forbidden], evidence=OBSERVED)

    result = authority_reachability(store, "session", compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER)
    account = next(item for item in result["reachable_subjects"] if item["subject_ref"] == "account")
    actions = [item["capability"]["action"] for item in result["actionable_capabilities"] if item["target_ref"] == "repo"]

    assert account["delegated_capability_budget"] == [allowed]
    assert actions == ["repo.read"]
