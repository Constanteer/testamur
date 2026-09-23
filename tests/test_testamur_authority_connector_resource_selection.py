from __future__ import annotations

from datetime import datetime, timezone

from testamur.authority_credentials import credential_constraints_satisfied

AT = datetime(2026, 9, 24, tzinfo=timezone.utc)


def verdict(attributes, constraints):
    return credential_constraints_satisfied(attributes, constraints, as_of=AT)


def test_repository_selection_requires_subset_of_explicit_credential_selection():
    ok, reasons, unresolved = verdict(
        {"repository_selection": ["repo:a", "repo:b"]},
        {"required_repository_selection": ["repo:a"]},
    )
    assert ok is True
    assert reasons == []
    assert unresolved == []


def test_repository_selection_cannot_expand_connector_credential_reach():
    ok, reasons, unresolved = verdict(
        {"repository_selection": ["repo:a"]},
        {"required_repository_selection": ["repo:a", "repo:b"]},
    )
    assert ok is False
    assert reasons == ["repository_selection_mismatch"]
    assert unresolved == []


def test_missing_repository_selection_fails_closed():
    ok, reasons, unresolved = verdict(
        {"scopes": ["repo:read"]},
        {"required_repository_selection": ["repo:a"]},
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["repository_selection"]


def test_repository_selection_aliases_are_not_additive_grants():
    ok, reasons, unresolved = verdict(
        {"repository_selection": ["repo:a"], "repositories": ["repo:a", "repo:b"]},
        {"required_repository_selection": ["repo:a"]},
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["repository_selection"]


def test_typed_repository_selection_evidence_is_not_stringified():
    ok, reasons, unresolved = verdict(
        {"repository_selection": [{"ref": "repo:a", "connected": True}]},
        {"required_repository_selection": ["repo:a"]},
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["repository_selection"]
