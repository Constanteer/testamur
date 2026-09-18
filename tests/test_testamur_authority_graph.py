from __future__ import annotations

import json
import sqlite3
from io import StringIO

import pytest

from testamur.authority_affectedness import affectedness_compromise_seeds
from testamur.authority import (
    AuthorityEvidenceClass,
    AuthorityRelationType,
    AuthoritySubjectKind,
    TestamurAuthorityStore,
)
from testamur.authority_explain import explain_authority_path
from testamur.authority_reachability import (
    CompromiseModel,
    authority_blast_radius,
    authority_reachability,
)
from testamur.authority_reliance import authority_reliance_impact
from testamur.cli import main as cli_main
from testamur.environment import initialize
from testamur.product_cli import dispatch
from testamur.product_service import TestamurProductService


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


def test_product_service_and_cli_expose_authority_reachability(tmp_path):
    product = TestamurProductService(tmp_path / "testamur.sqlite3")
    subject(product.authority, "worker", AuthoritySubjectKind.WORKLOAD)
    subject(product.authority, "repo", AuthoritySubjectKind.REPOSITORY)
    product.authority.record_edge(
        "worker",
        AuthorityRelationType.CAN_READ,
        "repo",
        capabilities=[cap("github", "repo.read", "repo:demo")],
        evidence=OBSERVED,
    )

    service_payload = product.authority_reach(
        "worker",
        compromise_model=CompromiseModel.PROCESS_CODE_EXECUTION.value,
    )
    assert service_payload["ok"] is True
    assert service_payload["schema"] == "testamur.product.authority-reachability.v1"
    assert any(
        item["capability"]["action"] == "repo.read"
        for item in service_payload["result"]["actionable_capabilities"]
    )

    output = StringIO()
    code = dispatch(
        [
            "authority",
            "reach",
            "worker",
            "--model",
            CompromiseModel.PROCESS_CODE_EXECUTION.value,
        ],
        stdout=output,
        service=product,
    )
    assert code == 0
    cli_payload = json.loads(output.getvalue())
    assert cli_payload["ok"] is True
    assert cli_payload["result"]["starting_subject_ref"] == "worker"


def test_product_service_authority_missing_subject_is_not_guessed(tmp_path):
    product = TestamurProductService(tmp_path / "testamur.sqlite3")

    payload = product.authority_reach(
        "missing",
        compromise_model=CompromiseModel.FULL_SUBJECT_COMPROMISE.value,
    )

    assert payload["ok"] is False
    assert payload["error"]["code"] == "object_not_found"


def test_public_cli_exposes_authority_reachability(tmp_path, monkeypatch, capsys):
    env = initialize(tmp_path, name="authority-demo")
    store = TestamurAuthorityStore(env.database_path)
    subject(store, "worker", AuthoritySubjectKind.WORKLOAD)
    subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    store.record_edge(
        "worker",
        AuthorityRelationType.CAN_READ,
        "repo",
        capabilities=[cap("github", "repo.read", "repo:demo")],
        evidence=OBSERVED,
    )

    monkeypatch.chdir(tmp_path)
    code = cli_main(
        [
            "--json",
            "authority",
            "reach",
            "worker",
            "--model",
            CompromiseModel.PROCESS_CODE_EXECUTION.value,
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["starting_subject_ref"] == "worker"
    assert any(
        item["capability"]["action"] == "repo.read"
        for item in payload["actionable_capabilities"]
    )


def test_authority_path_explanation_requires_exact_contiguity(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    for ref, kind in (
        ("worker", AuthoritySubjectKind.WORKLOAD),
        ("token", AuthoritySubjectKind.TOKEN),
        ("session", AuthoritySubjectKind.SESSION),
        ("other", AuthoritySubjectKind.PROCESS),
    ):
        subject(store, ref, kind)

    first = store.record_edge(
        "worker",
        AuthorityRelationType.EXPOSES,
        "token",
        evidence=OBSERVED,
        boundary_refs=["boundary:one"],
    )
    second = store.record_edge(
        "token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "session",
        evidence=OBSERVED,
        boundary_refs=["boundary:two"],
    )
    unrelated = store.record_edge(
        "other",
        AuthorityRelationType.CAN_EXECUTE,
        "session",
        evidence=OBSERVED,
    )

    explanation = explain_authority_path(
        store,
        [first["edge_id"], second["edge_id"]],
        starting_ref="worker",
        expected_target_ref="session",
    )
    assert explanation["subject_refs"] == ["worker", "token", "session"]
    assert explanation["trust_boundary_refs"] == ["boundary:one", "boundary:two"]

    with pytest.raises(ValueError, match="not contiguous"):
        explain_authority_path(
            store,
            [first["edge_id"], unrelated["edge_id"]],
            starting_ref="worker",
        )


def test_authority_path_explanation_does_not_guess_wrong_target(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "a", AuthoritySubjectKind.PROCESS)
    subject(store, "b", AuthoritySubjectKind.PROCESS)
    edge = store.record_edge(
        "a",
        AuthorityRelationType.CAN_EXECUTE,
        "b",
        evidence=OBSERVED,
    )

    with pytest.raises(ValueError, match="does not end"):
        explain_authority_path(
            store,
            [edge["edge_id"]],
            expected_target_ref="c",
        )


def test_affectedness_never_automatically_becomes_compromise(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "runtime", AuthoritySubjectKind.WORKLOAD)
    assessment = {
        "assessment_id": "tst:affectedness:1",
        "subject_revision": "revision:runtime:1",
        "state": "CONFIRMED_AFFECTED",
    }
    binding = {
        "subject_revision": "revision:runtime:1",
        "authority_subject_ref": "runtime",
        "binding_ref": "tst:binding:runtime:1",
        "compromise_basis": [],
    }

    result = affectedness_compromise_seeds(
        store,
        [assessment],
        [binding],
        policy_ref="policy:remote-rce",
        eligible_states=["CONFIRMED_AFFECTED"],
    )

    assert result["seed_refs"] == []
    assert result["rejected"][0]["reasons"] == ["compromise_basis_required"]


def test_affectedness_bridge_requires_explicit_policy_basis(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "runtime", AuthoritySubjectKind.WORKLOAD)
    assessment = {
        "assessment_id": "tst:affectedness:2",
        "subject_revision": "revision:runtime:2",
        "state": "CONFIRMED_AFFECTED",
    }
    binding = {
        "subject_revision": "revision:runtime:2",
        "authority_subject_ref": "runtime",
        "binding_ref": "tst:binding:runtime:2",
        "compromise_basis": [
            {
                "kind": "remote_exploitability",
                "ref": "advisory:exploitability",
                "evidence_class": "OBSERVED",
            },
            {
                "kind": "exposure",
                "ref": "runtime:internet-exposed",
                "evidence_class": "DERIVED",
                "analyzer": "deployment-inspector",
                "analyzer_version": "1",
            },
        ],
    }

    result = affectedness_compromise_seeds(
        store,
        [assessment],
        [binding],
        policy_ref="policy:remote-rce",
        eligible_states=["CONFIRMED_AFFECTED"],
        required_basis_kinds=["remote_exploitability", "exposure"],
    )

    assert result["seed_refs"] == ["runtime"]
    assert result["seeds"][0]["assessment_ids"] == ["tst:affectedness:2"]
    assert result["seeds"][0]["policy_ref"] == "policy:remote-rce"


def test_affectedness_bridge_rejects_declared_only_compromise_basis_by_default(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "runtime", AuthoritySubjectKind.WORKLOAD)
    assessment = {
        "assessment_id": "tst:affectedness:3",
        "subject_revision": "revision:runtime:3",
        "state": "CONFIRMED_AFFECTED",
    }
    binding = {
        "subject_revision": "revision:runtime:3",
        "authority_subject_ref": "runtime",
        "binding_ref": "tst:binding:runtime:3",
        "compromise_basis": [
            {
                "kind": "remote_exploitability",
                "ref": "docs:claims-rce",
                "evidence_class": "DECLARED",
            }
        ],
    }

    result = affectedness_compromise_seeds(
        store,
        [assessment],
        [binding],
        policy_ref="policy:remote-rce",
        eligible_states=["CONFIRMED_AFFECTED"],
        required_basis_kinds=["remote_exploitability"],
    )

    assert result["seed_refs"] == []
    assert result["rejected"][0]["reasons"] == [
        "declared_only_compromise_basis_not_accepted"
    ]


class FakeRelianceStore:
    def __init__(self, receipts):
        self.receipts = list(receipts)

    def list(self, *, scope_ref, reliant_ref=None, object_ref=None):
        values = [
            item
            for item in self.receipts
            if item["scope_ref"] == scope_ref
        ]
        if reliant_ref is not None:
            values = [item for item in values if item["reliant_ref"] == reliant_ref]
        if object_ref is not None:
            values = [item for item in values if item["object_ref"] == object_ref]
        return values


def test_authority_reliance_bridge_requires_explicit_resource_binding(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    store.record_edge(
        "connector",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo",
        capabilities=[cap("github", "repo.read", "repo:demo")],
        evidence=OBSERVED,
    )
    authority = authority_reachability(
        store,
        "connector",
        compromise_model=CompromiseModel.CONNECTOR_TAKEOVER,
    )
    reliance = FakeRelianceStore(
        [
            {
                "scope_ref": "scope:demo",
                "receipt_id": "receipt:1",
                "reliant_ref": "artifact:downstream",
                "reliant_revision_ref": "revision:downstream:1",
                "object_ref": "source:repo",
                "pinned_revisions": {"source:repo": "revision:repo:1"},
            }
        ]
    )

    result = authority_reliance_impact(
        authority,
        reliance,
        scope_ref="scope:demo",
        bindings=[],
    )

    assert result["impact_count"] == 0
    assert result["unmatched_actions"][0]["reason"] == (
        "no_explicit_authority_to_reliance_binding"
    )


def test_authority_reliance_bridge_matches_actual_durable_reliance(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(store, "connector", AuthoritySubjectKind.CONNECTOR)
    subject(store, "repo", AuthoritySubjectKind.REPOSITORY)
    store.record_edge(
        "connector",
        AuthorityRelationType.HAS_CAPABILITY,
        "repo",
        capabilities=[cap("github", "repo.read", "repo:demo")],
        evidence=OBSERVED,
    )
    authority = authority_reachability(
        store,
        "connector",
        compromise_model=CompromiseModel.CONNECTOR_TAKEOVER,
    )
    reliance = FakeRelianceStore(
        [
            {
                "scope_ref": "scope:demo",
                "receipt_id": "receipt:1",
                "reliant_ref": "artifact:downstream",
                "reliant_revision_ref": "revision:downstream:1",
                "object_ref": "source:repo",
                "pinned_revisions": {"source:repo": "revision:repo:1"},
            },
            {
                "scope_ref": "scope:demo",
                "receipt_id": "receipt:2",
                "reliant_ref": "artifact:other",
                "reliant_revision_ref": "revision:other:1",
                "object_ref": "source:other",
                "pinned_revisions": {"source:other": "revision:other-source:1"},
            },
        ]
    )

    result = authority_reliance_impact(
        authority,
        reliance,
        scope_ref="scope:demo",
        bindings=[
            {
                "authority_target_ref": "repo",
                "binding_ref": "binding:repo",
                "object_ref": "source:repo",
                "revision_ref": "revision:repo:1",
                "evidence": [
                    {
                        "ref": "inventory:repo-binding",
                        "evidence_class": "OBSERVED",
                    }
                ],
            }
        ],
    )

    assert result["impact_count"] == 1
    assert result["affected_reliant_refs"] == ["artifact:downstream"]
    impact = result["impacts"][0]
    assert impact["receipt_id"] == "receipt:1"
    assert impact["object_match"] is True
    assert impact["revision_match"] is True
    assert impact["review_required"] is True


def test_authentication_with_service_ref_requires_acceptance_evidence(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(
        store,
        "token",
        AuthoritySubjectKind.TOKEN,
        attributes={"audience": ["codex"], "scopes": ["session.create"]},
    )
    subject(store, "codex-service", AuthoritySubjectKind.SERVICE)
    subject(store, "session", AuthoritySubjectKind.SESSION)

    auth = store.record_edge(
        "token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "session",
        constraints={"service_ref": "codex-service"},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "token",
        compromise_model=CompromiseModel.CREDENTIAL_THEFT,
    )

    assert not any(
        item["subject_ref"] == "session" for item in result["reachable_subjects"]
    )
    blocked = next(
        item for item in result["blocked_transitions"]
        if item["edge_id"] == auth["edge_id"]
    )
    assert "credential_acceptance_not_established" in blocked["reasons"]


def test_service_acceptance_constraints_are_checked_against_credential(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(
        store,
        "token",
        AuthoritySubjectKind.TOKEN,
        attributes={"audience": ["community"], "scopes": ["profile.read"]},
    )
    subject(store, "codex-service", AuthoritySubjectKind.SERVICE)
    subject(store, "session", AuthoritySubjectKind.SESSION)

    acceptance = store.record_edge(
        "codex-service",
        AuthorityRelationType.ACCEPTS_CREDENTIAL,
        "token",
        constraints={"audience": ["codex"]},
        evidence=OBSERVED,
    )
    auth = store.record_edge(
        "token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "session",
        constraints={"service_ref": "codex-service"},
        evidence=OBSERVED,
    )

    result = authority_reachability(
        store,
        "token",
        compromise_model=CompromiseModel.CREDENTIAL_THEFT,
    )

    assert not any(
        item["subject_ref"] == "session" for item in result["reachable_subjects"]
    )
    blocked = next(
        item for item in result["blocked_transitions"]
        if item["edge_id"] == auth["edge_id"]
    )
    assert "credential_acceptance_constraints_unsatisfied" in blocked["reasons"]
    assert "audience_mismatch" in blocked["reasons"]
    assert acceptance["edge_id"] not in blocked["supporting_edge_ids"]


def test_matching_service_acceptance_is_preserved_as_supporting_evidence(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    subject(
        store,
        "token",
        AuthoritySubjectKind.TOKEN,
        attributes={"audience": ["codex"], "scopes": ["session.create"]},
    )
    subject(store, "codex-service", AuthoritySubjectKind.SERVICE)
    subject(store, "session", AuthoritySubjectKind.SESSION)

    acceptance = store.record_edge(
        "codex-service",
        AuthorityRelationType.ACCEPTS_CREDENTIAL,
        "token",
        constraints={
            "audience": ["codex"],
            "required_scopes": ["session.create"],
        },
        evidence=OBSERVED,
        boundary_refs=["boundary:service-acceptance"],
    )
    auth = store.record_edge(
        "token",
        AuthorityRelationType.CAN_AUTHENTICATE_AS,
        "session",
        constraints={"service_ref": "codex-service"},
        evidence=OBSERVED,
        boundary_refs=["boundary:credential-session"],
    )

    result = authority_reachability(
        store,
        "token",
        compromise_model=CompromiseModel.CREDENTIAL_THEFT,
    )

    reached = next(
        item for item in result["reachable_subjects"]
        if item["subject_ref"] == "session"
    )
    assert reached["path_edge_ids"] == [auth["edge_id"]]
    assert reached["supporting_edge_ids"] == [acceptance["edge_id"]]
    assert reached["boundary_refs"] == [
        "boundary:credential-session",
        "boundary:service-acceptance",
    ]
