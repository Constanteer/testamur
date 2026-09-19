from __future__ import annotations

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_github import record_github_connector_permissions
from testamur.authority_reachability import CompromiseModel, authority_reachability


def evidence(ref: str):
    return [{"ref": ref, "evidence_class": "OBSERVED"}]


def action_cap(repository_ref: str):
    return {
        "namespace": "github",
        "action": "write",
        "resource": "contents",
        "constraints": {
            "provider": "github",
            "installation_id": "42",
            "provider_permission": "contents",
            "provider_level": "write",
            "repository_selection": "selected",
            "repository_ref": repository_ref,
        },
    }


def build_graph(tmp_path, *, repository_selection=None, repository_refs=None):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    store.record_subject(AuthoritySubjectKind.SESSION, label="session", subject_ref="session:user")
    for ref in ("repo:a", "repo:b"):
        store.record_subject(AuthoritySubjectKind.REPOSITORY, label=ref, subject_ref=ref)
    record_github_connector_permissions(
        store,
        delegator_ref="session:user",
        connector_ref="connector:github:42",
        installation_id="42",
        permissions={"contents": "write"},
        repository_selection=repository_selection,
        repository_refs=repository_refs,
        evidence_ref="github-installation:42",
        evidence_revision="etag:permissions",
    )
    for ref in ("repo:a", "repo:b"):
        store.record_edge(
            "connector:github:42",
            AuthorityRelationType.HAS_CAPABILITY,
            ref,
            capabilities=[action_cap(ref)],
            evidence=evidence(f"github-action:{ref}"),
        )
    return store


def reachable_targets(store):
    result = authority_reachability(
        store,
        "session:user",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE,
    )
    return result, {item["target_ref"] for item in result["actionable_capabilities"]}


def test_selected_installation_only_reaches_explicit_repositories(tmp_path):
    store = build_graph(
        tmp_path,
        repository_selection="selected",
        repository_refs=["repo:a"],
    )
    result, targets = reachable_targets(store)
    assert targets == {"repo:a"}
    blocked = [item for item in result["blocked_transitions"] if item["target_ref"] == "repo:b"]
    assert blocked
    assert blocked[0]["reasons"] == ["missing_explicit_or_authorized_capability"]


def test_unresolved_installation_scope_cannot_authorize_repository_action(tmp_path):
    store = build_graph(tmp_path)
    result, targets = reachable_targets(store)
    assert targets == set()
    assert {item["target_ref"] for item in result["blocked_transitions"]} >= {"repo:a", "repo:b"}


def test_explicit_all_installation_scope_can_attenuate_to_repository_action(tmp_path):
    store = build_graph(tmp_path, repository_selection="all")
    _result, targets = reachable_targets(store)
    assert targets == {"repo:a", "repo:b"}
