from __future__ import annotations

from datetime import datetime, timezone

from testamur.authority_credentials import credential_constraints_satisfied


NOW = datetime(2026, 9, 19, 3, 0, tzinfo=timezone.utc)


def test_resource_constraint_is_not_silently_treated_as_credential_metadata() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"audiences": ["api"], "scopes": ["repo:read"]},
        {"audience": "api", "scope": "repo:read", "resource": "repo:Constanteer/testamur"},
        as_of=NOW,
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["resource"]


def test_principal_constraint_requires_graph_context() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"audience": "api"},
        {"audience": "api", "principal": "user:alice"},
        as_of=NOW,
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["principal"]


def test_service_ref_remains_routing_metadata_for_exact_acceptance_lookup() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"audience": "api"},
        {"audience": "api", "service_ref": "service:api"},
        as_of=NOW,
    )

    assert ok is True
    assert reasons == []
    assert unresolved == []


def test_plural_service_refs_fail_closed_until_exact_multi_target_routing_exists() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"audience": "api"},
        {"audience": "api", "service_refs": ["service:api", "service:admin"]},
        as_of=NOW,
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["service_refs"]
