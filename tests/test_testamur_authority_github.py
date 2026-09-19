from __future__ import annotations

import pytest

from testamur.authority import AuthoritySubjectKind, TestamurAuthorityStore
from testamur.authority_github import (
    github_permission_capabilities,
    record_github_connector_permissions,
)


def test_github_write_permission_does_not_become_generic_admin(tmp_path):
    capabilities = github_permission_capabilities(
        {"pull_requests": "write", "contents": "read"},
        installation_id="42",
        repository_refs=["repo:Constanteer/testamur"],
    )

    identities = {(item["resource"], item["action"]) for item in capabilities}
    assert identities == {
        ("contents", "read"),
        ("pull_requests", "read"),
        ("pull_requests", "write"),
    }
    assert all(item["namespace"] == "github" for item in capabilities)
    assert all(item["constraints"]["installation_id"] == "42" for item in capabilities)
    assert all(
        item["constraints"]["repository_refs"] == ["repo:Constanteer/testamur"]
        for item in capabilities
    )


def test_github_unknown_permission_level_fails_closed():
    with pytest.raises(ValueError, match="unsupported GitHub permission level"):
        github_permission_capabilities({"contents": "admin"}, installation_id="42")


def test_github_missing_repository_selection_stays_unresolved():
    capabilities = github_permission_capabilities(
        {"contents": "read"}, installation_id="42"
    )
    assert capabilities[0]["constraints"]["repository_selection"] == "unresolved"
    assert "repository_refs" not in capabilities[0]["constraints"]


def test_record_github_connector_requires_exact_evidence_and_explicit_permissions(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    store.record_subject(
        AuthoritySubjectKind.SESSION,
        label="employee session",
        subject_ref="session:employee",
    )

    edge = record_github_connector_permissions(
        store,
        delegator_ref="session:employee",
        connector_ref="connector:github:42",
        installation_id="42",
        permissions={"contents": "read", "pull_requests": "write"},
        repository_refs=["repo:Constanteer/testamur"],
        evidence_ref="github-installation:42",
        evidence_revision="etag:abc123",
        boundary_refs=["boundary:product-to-github"],
    )

    assert edge["relation_type"] == "DELEGATES"
    assert edge["boundary_refs"] == ["boundary:product-to-github"]
    assert edge["evidence"][0]["ref"] == "github-installation:42"
    assert edge["evidence"][0]["revision"] == "etag:abc123"
    assert edge["evidence"][0]["evidence_class"] == "DERIVED"
    assert edge["metadata"]["permission_source"] == "explicit_delegation"

    connector = store.get_subject("connector:github:42")
    assert connector["kind"] == "CONNECTOR"
    assert connector["attributes"]["provider"] == "github"

    with pytest.raises(ValueError, match="non-empty object"):
        record_github_connector_permissions(
            store,
            delegator_ref="session:employee",
            connector_ref="connector:github:empty",
            installation_id="43",
            permissions={},
            evidence_ref="github-installation:43",
            evidence_revision="etag:def456",
        )
    assert store.maybe_subject("connector:github:empty") is None


def test_invalid_exact_evidence_is_rejected_before_connector_subject_is_recorded(tmp_path):
    store = TestamurAuthorityStore(tmp_path / "authority.sqlite3")
    store.record_subject(
        AuthoritySubjectKind.SESSION,
        label="employee session",
        subject_ref="session:employee",
    )
    with pytest.raises(ValueError, match="evidence.revision"):
        record_github_connector_permissions(
            store,
            delegator_ref="session:employee",
            connector_ref="connector:github:bad-evidence",
            installation_id="44",
            permissions={"contents": "read"},
            evidence_ref="github-installation:44",
            evidence_revision="",
        )
    assert store.maybe_subject("connector:github:bad-evidence") is None
