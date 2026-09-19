from __future__ import annotations

from testamur.authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_github import record_github_connector_permissions
from testamur.authority_reachability import CompromiseModel, authority_reachability
from testamur.authority_reachability_policy import capability_rejection_diagnostics


def evidence(ref: str):
    return [{"ref": ref, "evidence_class": "OBSERVED"}]


def action_cap(repository_ref: str):
    return {"namespace": "github", "action": "write", "resource": "contents", "constraints": {"provider": "github", "installation_id": "42", "provider_permission": "contents", "provider_level": "write", "repository_selection": "selected", "repository_ref": repository_ref}}


def build_graph(tmp_path, *, repository_selection=None, repository_refs=None):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    store.record_subject(AuthoritySubjectKind.SESSION, label="session", subject_ref="session:user")
    for ref in ("repo:a", "repo:b"):
        store.record_subject(AuthoritySubjectKind.REPOSITORY, label=ref, subject_ref=ref)
    record_github_connector_permissions(store, delegator_ref="session:user", connector_ref="connector:github:42", installation_id="42", permissions={"contents": "write"}, repository_selection=repository_selection, repository_refs=repository_refs, evidence_ref="github-installation:42", evidence_revision="etag:permissions")
    for ref in ("repo:a", "repo:b"):
        store.record_edge("connector:github:42", AuthorityRelationType.HAS_CAPABILITY, ref, capabilities=[action_cap(ref)], evidence=evidence(f"github-action:{ref}"))
    return store


def reachable_targets(store):
    result = authority_reachability(store, "session:user", compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE)
    return result, {item["target_ref"] for item in result["actionable_capabilities"]}


def test_selected_installation_only_reaches_explicit_repositories(tmp_path):
    store = build_graph(tmp_path, repository_selection="selected", repository_refs=["repo:a"])
    result, targets = reachable_targets(store)
    assert targets == {"repo:a"}
    blocked = [item for item in result["blocked_transitions"] if item["target_ref"] == "repo:b"]
    assert blocked
    assert blocked[0]["reasons"] == ["repository_scope_outside_delegation"]
    assert blocked[0]["failed_constraints"] == ["repository_selection"]
    assert blocked[0]["candidate_capabilities"] == [action_cap("repo:b")]
    assert blocked[0]["inherited_capability_budget"][0]["constraints"]["repository_refs"] == ["repo:a"]


def test_rejection_diagnostics_preserve_exact_repository_budget(tmp_path):
    store = build_graph(tmp_path, repository_selection="selected", repository_refs=["repo:a"])
    delegation = store.list_edges(source_ref="session:user", target_ref="connector:github:42", relation_type=AuthorityRelationType.DELEGATES)[0]
    candidate = store.list_edges(source_ref="connector:github:42", target_ref="repo:b", relation_type=AuthorityRelationType.HAS_CAPABILITY)[0]
    inherited = tuple(delegation["capabilities"])
    diagnostic = capability_rejection_diagnostics(candidate, inherited)
    assert diagnostic is not None
    assert diagnostic["reasons"] == ["repository_scope_outside_delegation"]
    assert diagnostic["failed_constraints"] == ["repository_selection"]
    assert diagnostic["unresolved_constraints"] == []
    assert diagnostic["candidate_capabilities"] == [action_cap("repo:b")]
    assert diagnostic["inherited_capability_budget"] == list(inherited)


def test_unresolved_repository_budget_is_reported_as_unresolved(tmp_path):
    store = build_graph(tmp_path)
    result, targets = reachable_targets(store)
    assert targets == set()
    blocked = [item for item in result["blocked_transitions"] if item["target_ref"] == "repo:a"]
    assert blocked[0]["reasons"] == ["repository_selection_unresolved"]
    assert blocked[0]["failed_constraints"] == ["repository_selection"]
    assert blocked[0]["unresolved_constraints"] == ["repository_selection"]


def test_unresolved_installation_scope_cannot_authorize_repository_action(tmp_path):
    store = build_graph(tmp_path)
    result, targets = reachable_targets(store)
    assert targets == set()
    assert {item["target_ref"] for item in result["blocked_transitions"]} >= {"repo:a", "repo:b"}


def test_explicit_all_installation_scope_can_attenuate_to_repository_action(tmp_path):
    store = build_graph(tmp_path, repository_selection="all")
    _result, targets = reachable_targets(store)
    assert targets == {"repo:a", "repo:b"}


def _diagnose_constraints(parent_constraints, candidate_constraints):
    parent = {"namespace": "oauth", "action": "invoke", "resource": "svc:api", "constraints": parent_constraints}
    candidate = {"namespace": "oauth", "action": "invoke", "resource": "svc:api", "constraints": candidate_constraints}
    edge = {"capabilities": [candidate]}
    return capability_rejection_diagnostics(edge, (parent,))


def test_token_audience_scope_issuer_and_tenant_denials_are_exact():
    diagnostic = _diagnose_constraints(
        {
            "audiences": ["api://testamur"],
            "required_scopes": ["project:read", "project:write"],
            "required_issuer": ["https://issuer.example"],
            "tenant_id": ["tenant:a"],
        },
        {
            "audience": ["api://other"],
            "scope": ["project:admin"],
            "issuer": ["https://other-issuer.example"],
            "tenant": ["tenant:b"],
        },
    )
    assert diagnostic is not None
    assert diagnostic["reasons"] == [
        "audience_outside_delegation",
        "issuer_outside_delegation",
        "scope_outside_delegation",
        "tenant_outside_delegation",
    ]
    assert diagnostic["failed_constraints"] == ["audience", "issuer", "scope", "tenant"]


def test_runtime_binding_and_gate_denials_name_exact_constraints():
    diagnostic = _diagnose_constraints(
        {
            "device_binding": ["device:trusted"],
            "session_binding": ["session:trusted"],
            "mfa_required": True,
            "human_confirmation_required": True,
        },
        {
            "device_binding": ["device:other"],
            "session_binding": ["session:other"],
        },
    )
    assert diagnostic is not None
    assert diagnostic["reasons"] == [
        "device_binding_outside_delegation",
        "human_confirmation_required_not_preserved",
        "mfa_required_not_preserved",
        "session_binding_outside_delegation",
    ]
    assert diagnostic["failed_constraints"] == [
        "device_binding",
        "human_confirmation_required",
        "mfa_required",
        "session_binding",
    ]


def test_expiry_and_provider_specific_constraint_denials_remain_fail_closed():
    diagnostic = _diagnose_constraints(
        {"expires_at": "2026-09-20T12:00:00Z", "provider_condition": {"branch": "main"}},
        {"expires_at": "2026-09-20T12:00:01Z", "provider_condition": {"branch": "dev"}},
    )
    assert diagnostic is not None
    assert diagnostic["reasons"] == ["expiry_outside_delegation", "provider_constraint_mismatch"]
    assert diagnostic["failed_constraints"] == ["expires_at", "provider_condition"]
