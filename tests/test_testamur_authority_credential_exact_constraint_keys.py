from datetime import datetime, timezone

import pytest

from testamur.authority_credentials import credential_constraints_satisfied


NOW = datetime(2026, 9, 24, tzinfo=timezone.utc)


def test_unknown_exact_constraint_key_remains_unresolved() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {}, {"repository_selection": "selected"}, as_of=NOW
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["repository_selection"]


@pytest.mark.parametrize("key", [7, ("scope",), None, ""])
def test_typed_or_blank_constraint_key_is_not_manufactured_into_identity(key: object) -> None:
    with pytest.raises(ValueError, match="constraint keys must be exact non-empty strings"):
        credential_constraints_satisfied({}, {key: "connected"}, as_of=NOW)


def test_connectivity_shaped_unknown_constraint_does_not_grant_authority() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {}, {"repository_selection": {"connected": True, "target_ref": "repo:private"}}, as_of=NOW
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["repository_selection"]


def test_scope_is_subset_not_overlap() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"scopes": ["repo:read", "issues:read"]},
        {"required_scopes": ["repo:read", "repo:admin"]},
        as_of=NOW,
    )

    assert ok is False
    assert reasons == ["scope_mismatch"]
    assert unresolved == []


def test_audience_requires_explicit_intersection() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"audience": "service:github"},
        {"required_audience": "service:gitlab"},
        as_of=NOW,
    )

    assert ok is False
    assert reasons == ["audience_mismatch"]
    assert unresolved == []
