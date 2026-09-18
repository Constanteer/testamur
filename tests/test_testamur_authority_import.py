from __future__ import annotations

import pytest

from testamur.authority import AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_import import (
    exact_evidence,
    record_connector_delegation,
    record_credential_observation,
)


def test_exact_evidence_requires_revision_and_derived_analyzer():
    with pytest.raises(ValueError, match="revision"):
        exact_evidence(ref="provider:iam", evidence_class="OBSERVED", revision="")
    with pytest.raises(ValueError, match="analyzer"):
        exact_evidence(ref="provider:iam", evidence_class="DERIVED", revision="sha256:abc")


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
