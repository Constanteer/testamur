from __future__ import annotations

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_reachability import CompromiseModel, authority_reachability

OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def _subject(store, ref, kind):
    store.record_subject(kind, label=ref, subject_ref=ref, attributes={})


def test_connectivity_does_not_manufacture_actionable_authority(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "worker", AuthoritySubjectKind.WORKLOAD)
    _subject(store, "service", AuthoritySubjectKind.SERVICE)
    store.record_edge("worker", AuthorityRelationType.CAN_CONNECT, "service", evidence=OBSERVED)

    result = authority_reachability(store, "worker", compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION)

    assert result["actionable_capabilities"] == []
    assert not any(item["subject_ref"] == "service" for item in result["reachable_subjects"])


def test_delegated_constraints_survive_into_reachability_projection(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    _subject(store, "session", AuthoritySubjectKind.SESSION)
    _subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    _subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    delegated = {
        "namespace": "github",
        "action": "repo.write",
        "resource": "repo:private",
        "constraints": {
            "required_scopes": ["contents:write"],
            "audience": ["github-app"],
            "tenant_id": "installation:42",
        },
    }
    store.record_edge("session", AuthorityRelationType.DELEGATES, "connector", capabilities=[delegated], evidence=OBSERVED)
    store.record_edge("connector", AuthorityRelationType.HAS_CAPABILITY, "repo", capabilities=[delegated], evidence=OBSERVED)

    result = authority_reachability(store, "session", compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER)
    connector = next(item for item in result["reachable_subjects"] if item["subject_ref"] == "connector")
    action = next(item for item in result["actionable_capabilities"] if item["target_ref"] == "repo")

    assert connector["delegated_capability_budget"][0]["constraints"] == delegated["constraints"]
    assert action["capability"]["constraints"] == delegated["constraints"]


def test_exact_path_boundary_crossings_exclude_supporting_acceptance_edge(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    store.record_subject(AuthoritySubjectKind.TOKEN, label="token", subject_ref="token", attributes={"audience": ["app"]})
    _subject(store, "session", AuthoritySubjectKind.SESSION)
    _subject(store, "auth", AuthoritySubjectKind.SERVICE)
    store.record_edge("auth", AuthorityRelationType.ACCEPTS_CREDENTIAL, "token", evidence=OBSERVED, boundary_refs=["boundary:support-only"])
    auth = store.record_edge("token", AuthorityRelationType.CAN_AUTHENTICATE_AS, "session", constraints={"audience": ["app"], "service_ref": "auth"}, evidence=OBSERVED, boundary_refs=["boundary:path"])

    result = authority_reachability(store, "token", compromise_model=CompromiseModel.CREDENTIAL_THEFT)
    session = next(item for item in result["reachable_subjects"] if item["subject_ref"] == "session")

    assert session["boundary_refs"] == ["boundary:path"]
    assert session["trust_boundary_crossings"][0]["edge_id"] == auth["edge_id"]
    assert "boundary:support-only" not in result["trust_boundary_refs"]
