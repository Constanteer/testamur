from __future__ import annotations

import sqlite3

import pytest

from testamur.authority import (
    AuthorityEvidenceClass,
    AuthorityRelationType,
    AuthoritySubjectKind,
    TestamurAuthorityStore,
)
from testamur.authority_reachability import (
    CompromiseModel,
    authority_blast_radius,
    authority_reachability,
)


OBSERVED = [{"ref": "tst:evidence:observed", "evidence_class": "OBSERVED"}]


def cap(namespace: str, action: str, resource: str | None = None) -> dict:
    value = {"namespace": namespace, "action": action, "constraints": {}}
    if resource is not None:
        value["resource"] = resource
    return value


def subject(
    store: TestamurAuthorityStore,
    ref: str,
    kind: AuthoritySubjectKind,
    *,
    attributes: dict | None = None,
) -> None:
    store.record_subject(
        kind,
        label=ref,
        subject_ref=ref,
        attributes=attributes or {},
    )


def test_authority_edges_require_explicit_evidence(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "worker", AuthoritySubjectKind.WORKLOAD)
    subject(store, "secret", AuthoritySubjectKind.SECRET)

    with pytest.raises(ValueError, match="explicit evidence"):
        store.record_edge(
            "worker",
            AuthorityRelationType.CAN_READ,
            "secret",
            evidence=[],
        )


def test_authority_store_is_append_only(tmp_path):
    path = tmp_path / "authority.sqlite3"
    store = TestamurAuthorityStore(path)
    subject(store, "worker", AuthoritySubjectKind.WORKLOAD)
    subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    edge = store.record_edge(
        "worker",
        AuthorityRelationType.CAN_WRITE,
        "repo",
        evidence=OBSERVED,
    )

    with sqlite3.connect(path) as conn, pytest.raises(
        sqlite3.IntegrityError, match="immutable"
    ):
        conn.execute(
            "UPDATE testamur_authority_edges SET target_ref='other' WHERE edge_id=?",
            (edge["edge_id"],),
        )


def test_plain_write_is_actionable_but_does_not_control_target(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "worker", AuthoritySubjectKind.WORKLOAD)
    subject(store, "repo", AuthoritySubjectKind.REPOSITORY)

    store.record_edge(
        "worker",
        AuthorityRelationType.CAN_WRITE,
        "repo",
        capabilities=[cap("github", "pull_request.write", "repo:demo")],
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "worker",
        compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
    )

    assert any(
        item["target_ref"] == "repo"
        and item["capability"]["action"] == "pull_request.write"
        for item in result["actionable_capabilities"]
    )
    assert not any(
        item["subject_ref"] == "repo"
        for item in result["reachable_subjects"]
        if item["subject_ref"] != "worker"
    )


def test_readable_token_audience_mismatch_fails_closed(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "worker", AuthoritySubjectKind.WORKLOAD)
    subject(
        store,
        "community-token",
        AuthoritySubjectKind.TOKEN,
        attributes={"audience": ["community"], "scopes": ["profile.read"]},
    )
    subject(store, "codex-session", AuthoritySubjectKind.SESSION)

    store.record_edge(
        "worker",
        AuthorityRelationType.CAN_READ,
        "community-token",
        evidence=OBSERVED,
    )
    auth_edge = store.record_edge(
        "community-token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "codex-session",
        constraints={"audience": ["codex"]},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "worker",
        compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
    )

    assert any(
        item["subject_ref"] == "community-token"
        and item["reachability_class"] == "CREDENTIAL_ACQUIRED"
        for item in result["reachable_subjects"]
    )
    assert not any(
        item["subject_ref"] == "codex-session"
        for item in result["reachable_subjects"]
    )
    assert any(
        item["edge_id"] == auth_edge["edge_id"]
        and "audience_mismatch" in item["reasons"]
        for item in result["blocked_transitions"]
    )


def test_scope_mismatch_blocks_authentication(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(
        store,
        "token",
        AuthoritySubjectKind.TOKEN,
        attributes={"audience": ["codex"], "scopes": ["profile.read"]},
    )
    subject(store, "session", AuthoritySubjectKind.SESSION)

    edge = store.record_edge(
        "token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "session",
        constraints={"audience": ["codex"], "required_scopes": ["repo.write"]},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "token",
        compromise_model=CompromiseModel.CREDENTIAL_THEFT,
    )

    assert not any(item["subject_ref"] == "session" for item in result["reachable_subjects"])
    assert any(
        item["edge_id"] == edge["edge_id"] and "scope_mismatch" in item["reasons"]
        for item in result["blocked_transitions"]
    )


def test_expired_token_does_not_authenticate(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(
        store,
        "token",
        AuthoritySubjectKind.TOKEN,
        attributes={
            "audience": ["codex"],
            "expires_at": "2026-01-01T00:00:00Z",
        },
    )
    subject(store, "session", AuthoritySubjectKind.SESSION)
    store.record_edge(
        "token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "session",
        constraints={"audience": ["codex"]},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "token",
        compromise_model=CompromiseModel.CREDENTIAL_THEFT,
        as_of="2026-09-18T00:00:00Z",
    )

    assert not any(item["subject_ref"] == "session" for item in result["reachable_subjects"])
    assert any(
        "credential_or_edge_expired" in item["reasons"]
        for item in result["blocked_transitions"]
    )


def test_delegation_intersects_capability_budget(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "session", AuthoritySubjectKind.SESSION)
    subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    subject(store, "repo", AuthoritySubjectKind.REPOSITORY)

    store.record_edge(
        "session",
        AuthorityRelationType.DELEGATES,
        "connector",
        capabilities=[
            cap("github", "repo.read", "repo:demo"),
            cap("github", "pull_request.write", "repo:demo"),
        ],
        evidence=OBSERVED,
    )
    store.record_edge(
        "connector",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo",
        capabilities=[
            cap("github", "repo.read", "repo:demo"),
            cap("github", "pull_request.write", "repo:demo"),
            cap("github", "repo.admin", "repo:demo"),
        ],
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "session",
        compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER,
    )

    actions = {
        item["capability"]["action"] for item in result["actionable_capabilities"]
        if item["target_ref"] == "repo"
    }
    assert actions == {"repo.read", "pull_request.write"}
    assert "repo.admin" not in actions


def test_delegation_without_explicit_capabilities_fails_closed(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "session", AuthoritySubjectKind.SESSION)
    subject(store, "connector", AuthoritySubjectKind.CONNECTOR)

    edge = store.record_edge(
        "session",
        AuthorityRelationType.DELEGATES,
        "connector",
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "session",
        compromise_model=CompromiseModel.ACCOUNT_SESSION_TAKEOVER,
    )

    assert not any(
        item["subject_ref"] == "connector" for item in result["reachable_subjects"]
    )
    assert any(
        item["edge_id"] == edge["edge_id"]
        and "missing_or_empty_delegated_capability_set" in item["reasons"]
        for item in result["blocked_transitions"]
    )


def test_human_confirmation_is_conditional_not_silently_bypassed(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    subject(store, "repo", AuthoritySubjectKind.REPOSITORY)

    edge = store.record_edge(
        "connector",
        AuthorityRelationType.CAN_WRITE,
        "repo",
        capabilities=[cap("github", "merge", "repo:demo")],
        constraints={"human_confirmation_required": True},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "connector",
        compromise_model=CompromiseModel.CONNECTOR_TAKEOVER,
    )

    assert not result["actionable_capabilities"]
    assert any(
        item["edge_id"] == edge["edge_id"]
        and item["reachability_class"] == "CONDITIONALLY_ACTIONABLE"
        for item in result["blocked_transitions"]
    )


def test_declared_only_path_remains_explicit(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "worker", AuthoritySubjectKind.WORKLOAD)
    subject(store, "token", AuthoritySubjectKind.TOKEN)

    store.record_edge(
        "worker",
        AuthorityRelationType.EXPOSES,
        "token",
        evidence=[
            {
                "ref": "docs:deployment",
                "evidence_class": AuthorityEvidenceClass.DECLARED.value,
            }
        ],
    )

    result = authority_reachability(
        store,
        "worker",
        compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
    )

    token = next(
        item for item in result["reachable_subjects"] if item["subject_ref"] == "token"
    )
    assert token["evidence_state"] == "CONTAINS_DECLARED_ONLY_EDGE"


def test_cycle_safe_and_depth_bound_is_explicit(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    for ref in ("a", "b", "c"):
        subject(store, ref, AuthoritySubjectKind.PROCESS)

    store.record_edge(
        "a",
        AuthorityRelationType.CAN_EXECUTE,
        "b",
        evidence=OBSERVED,
    )
    store.record_edge(
        "b",
        AuthorityRelationType.CAN_EXECUTE,
        "a",
        evidence=OBSERVED,
    )
    store.record_edge(
        "b",
        AuthorityRelationType.CAN_EXECUTE,
        "c",
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "a",
        compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
        max_depth=1,
    )

    assert result["truncated"] is True
    assert "max_depth" in result["truncation_reasons"]
    assert any(item["subject_ref"] == "b" for item in result["reachable_subjects"])
    assert not any(item["subject_ref"] == "c" for item in result["reachable_subjects"])


def test_end_to_end_worker_token_session_connector_repo(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "image-worker", AuthoritySubjectKind.WORKLOAD)
    subject(
        store,
        "community-token",
        AuthoritySubjectKind.TOKEN,
        attributes={
            "audience": ["codex"],
            "scopes": ["session.create"],
            "expires_at": "2027-01-01T00:00:00Z",
        },
    )
    subject(store, "employee-session", AuthoritySubjectKind.SESSION)
    subject(store, "github-connector", AuthoritySubjectKind.CONNECTOR)
    subject(store, "private-repo", AuthoritySubjectKind.REPOSITORY)

    store.record_edge(
        "image-worker",
        AuthorityRelationType.EXPOSES,
        "community-token",
        evidence=OBSERVED,
        boundary_refs=["boundary:workload-identity"],
    )
    store.record_edge(
        "community-token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "employee-session",
        constraints={"audience": ["codex"], "required_scopes": ["session.create"]},
        evidence=OBSERVED,
        boundary_refs=["boundary:identity-product"],
    )
    store.record_edge(
        "employee-session",
        AuthorityRelationType.DELEGATES,
        "github-connector",
        capabilities=[
            cap("github", "repo.read", "repo:private"),
            cap("github", "pull_request.write", "repo:private"),
        ],
        evidence=OBSERVED,
        boundary_refs=["boundary:product-connector"],
    )
    store.record_edge(
        "github-connector",
        AuthorityRelationType.HAS_CAPABILITY,
        "private-repo",
        capabilities=[
            cap("github", "repo.read", "repo:private"),
            cap("github", "pull_request.write", "repo:private"),
            cap("github", "repo.admin", "repo:private"),
        ],
        evidence=OBSERVED,
        boundary_refs=["boundary:connector-repository"],
    )

    result = authority_blast_radius(
        store,
        "image-worker",
        compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION,
        as_of="2026-09-18T00:00:00Z",
    )

    actions = {
        item["capability"]["action"]
        for item in result["actionable_capabilities"]
        if item["target_ref"] == "private-repo"
    }
    assert actions == {"repo.read", "pull_request.write"}
    assert result["trust_boundary_refs"] == [
        "boundary:connector-repository",
        "boundary:identity-product",
        "boundary:product-connector",
        "boundary:workload-identity",
    ]
    assert result["truncated"] is False
