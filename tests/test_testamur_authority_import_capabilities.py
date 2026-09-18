from __future__ import annotations

import pytest

from testamur.authority import TestamurAuthorityStore
from testamur.authority_import import exact_evidence, record_connector_delegation


def _evidence() -> dict[str, str]:
    return exact_evidence(
        ref="provider://github/installations/42",
        evidence_class="OBSERVED",
        revision="etag:permissions-v7",
    )


def test_connector_import_rejects_missing_namespace_or_action(tmp_path) -> None:
    store = TestamurAuthorityStore(tmp_path / "authority.json")

    for capability in (
        {"action": "read", "resource": "repo:a"},
        {"namespace": "github", "resource": "repo:a"},
        {"namespace": " ", "action": "read"},
        {"namespace": "github", "action": " "},
    ):
        with pytest.raises(ValueError):
            record_connector_delegation(
                store,
                delegator_ref="principal:owner",
                connector_ref="connector:github-app:42",
                capabilities=[capability],
                evidence=[_evidence()],
            )

    assert store.list_edges() == []


def test_connector_import_rejects_non_object_constraints(tmp_path) -> None:
    store = TestamurAuthorityStore(tmp_path / "authority.json")

    with pytest.raises(ValueError, match="capability.constraints must be an object"):
        record_connector_delegation(
            store,
            delegator_ref="principal:owner",
            connector_ref="connector:github-app:42",
            capabilities=[
                {
                    "namespace": "github",
                    "action": "contents:read",
                    "resource": "repo:a",
                    "constraints": ["branch:main"],
                }
            ],
            evidence=[_evidence()],
        )

    assert store.list_edges() == []


def test_connector_import_preserves_provider_constraints_exactly(tmp_path) -> None:
    store = TestamurAuthorityStore(tmp_path / "authority.json")
    provider_constraints = {
        "required_scopes": ["repo:read"],
        "tenant_id": "acme",
        "approval_required": True,
        "provider_condition": {"ref": "refs/heads/main"},
    }

    edge = record_connector_delegation(
        store,
        delegator_ref="principal:owner",
        connector_ref="connector:github-app:42",
        capabilities=[
            {
                "namespace": "github",
                "action": "contents:read",
                "resource": "repo:a",
                "constraints": provider_constraints,
            }
        ],
        evidence=[_evidence()],
        boundary_refs=["boundary:github"],
    )

    assert edge["capabilities"][0]["constraints"] == provider_constraints
    assert edge["boundary_refs"] == ["boundary:github"]
    assert edge["metadata"]["permission_source"] == "explicit_delegation"
