from __future__ import annotations

import pytest

from testamur.authority import AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_import import (
    exact_evidence,
    record_authentication_authority,
    record_connector_delegation,
    record_credential_acceptance,
    record_credential_observation,
)
from testamur.authority_reachability import CompromiseModel, authority_reachability


def test_exact_evidence_requires_revision_and_derived_analyzer():
    with pytest.raises(ValueError, match="revision"):
        exact_evidence(ref="provider:iam", evidence_class="OBSERVED", revision="")
    with pytest.raises(ValueError, match="analyzer"):
        exact_evidence(ref="provider:iam", evidence_class="DERIVED", revision="sha256:abc")


def test_raw_import_evidence_cannot_bypass_class_or_derived_provenance(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    with pytest.raises(ValueError, match="evidence_class"):
        record_credential_acceptance(
            store,
            service_ref="service:product",
            credential_ref="token:1",
            evidence=[{
                "ref": "provider:oauth",
                "revision": "sha256:policy",
                "evidence_class": "TRUST_ME",
            }],
        )
    with pytest.raises(ValueError, match="analyzer"):
        record_connector_delegation(
            store,
            delegator_ref="session:1",
            connector_ref="connector:1",
            capabilities=[{"namespace": "github", "action": "repo.read", "constraints": {}}],
            evidence=[{
                "ref": "provider:connector",
                "revision": "sha256:installation",
                "evidence_class": "DERIVED",
            }],
        )
    with pytest.raises(ValueError, match="analyzer"):
        record_credential_observation(
            store,
            credential_ref="token:1",
            label="token",
            evidence={
                "ref": "provider:token",
                "revision": "sha256:token-observation",
                "evidence_class": "DERIVED",
            },
        )


def test_credential_metadata_does_not_infer_authentication_edges(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    evidence = exact_evidence(
        ref="tst:snapshot:oauth-config",
        evidence_class="OBSERVED",
        revision="sha256:oauth-config-v1",
    )
    record_credential_observation(
        store,
        credential_ref="token:1",
        label="token 1",
        kind=AuthoritySubjectKind.TOKEN,
        issuer="issuer:1",
        audience=["product"],
        scopes=["repo.read"],
        evidence=evidence,
    )
    token = store.get_subject("token:1")
    assert token["attributes"]["audience"] == ["product"]
    assert token["attributes"]["scopes"] == ["repo.read"]
    assert token["metadata"]["import_evidence"]["revision"] == "sha256:oauth-config-v1"
    assert store.edges_from("token:1") == []


def test_imported_authority_edges_require_exact_revision(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    with pytest.raises(ValueError, match="revision"):
        record_credential_acceptance(
            store,
            service_ref="service:product",
            credential_ref="token:1",
            evidence=[{"ref": "provider:oauth", "evidence_class": "OBSERVED"}],
        )
    with pytest.raises(ValueError, match="exact evidence"):
        record_connector_delegation(
            store,
            delegator_ref="session:1",
            connector_ref="connector:1",
            capabilities=[{"namespace": "github", "action": "repo.read", "constraints": {}}],
            evidence=[],
        )


def test_authentication_requires_separate_service_acceptance_fact(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    ev = [exact_evidence(
        ref="provider:oauth-policy",
        evidence_class="OBSERVED",
        revision="sha256:policy-v3",
    )]
    store.record_subject(
        AuthoritySubjectKind.TOKEN,
        label="token",
        subject_ref="token:1",
        attributes={"audience": ["product"], "scopes": ["session.create"]},
    )
    store.record_subject(AuthoritySubjectKind.SERVICE, label="product", subject_ref="service:product")
    store.record_subject(AuthoritySubjectKind.SESSION, label="session", subject_ref="session:1")

    auth = record_authentication_authority(
        store,
        credential_ref="token:1",
        principal_ref="session:1",
        service_ref="service:product",
        audience="product",
        required_scopes=["session.create"],
        evidence=ev,
    )
    before = authority_reachability(
        store,
        "token:1",
        compromise_model=CompromiseModel.CREDENTIAL_THEFT,
    )
    assert not any(item["subject_ref"] == "session:1" for item in before["reachable_subjects"])
    assert any(
        item["edge_id"] == auth["edge_id"]
        and "credential_acceptance_not_established" in item["reasons"]
        for item in before["blocked_transitions"]
    )

    acceptance = record_credential_acceptance(
        store,
        service_ref="service:product",
        credential_ref="token:1",
        audience="product",
        required_scopes=["session.create"],
        evidence=ev,
        boundary_refs=["boundary:identity-product"],
    )
    after = authority_reachability(
        store,
        "token:1",
        compromise_model=CompromiseModel.CREDENTIAL_THEFT,
    )
    reached = next(item for item in after["reachable_subjects"] if item["subject_ref"] == "session:1")
    assert acceptance["edge_id"] in reached["supporting_edge_ids"]
    assert "boundary:identity-product" in reached["boundary_refs"]


def test_connector_delegation_rejects_implicit_unbounded_permission(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    evidence = [exact_evidence(
        ref="tst:snapshot:connector-installation",
        evidence_class="DERIVED",
        revision="sha256:installation-v2",
        analyzer="github-connector-importer",
        analyzer_version="1",
    )]
    with pytest.raises(ValueError, match="non-empty capability"):
        record_connector_delegation(
            store,
            delegator_ref="session:1",
            connector_ref="connector:1",
            capabilities=[],
            evidence=evidence,
        )

    edge = record_connector_delegation(
        store,
        delegator_ref="session:1",
        connector_ref="connector:1",
        capabilities=[{
            "namespace": "github",
            "action": "pull_request.write",
            "resource": "repo:demo",
            "constraints": {},
        }],
        evidence=evidence,
        boundary_refs=["boundary:product-github"],
    )
    assert edge["relation_type"] == "DELEGATES"
    assert edge["capabilities"][0]["action"] == "pull_request.write"
    assert edge["boundary_refs"] == ["boundary:product-github"]
    assert edge["metadata"]["permission_source"] == "explicit_delegation"
