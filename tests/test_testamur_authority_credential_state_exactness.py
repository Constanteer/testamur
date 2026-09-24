from datetime import datetime, timezone

import pytest

from testamur.authority_credentials import credential_constraints_satisfied


AT = datetime(2026, 9, 24, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None, {}, []])
def test_typed_or_null_active_constraint_fails_closed(value):
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"active": True}, {"active": value}, as_of=AT
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["active"]


@pytest.mark.parametrize("value", ["false", "true", 0, 1, None, {}, []])
def test_typed_or_null_revoked_attribute_fails_closed(value):
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"revoked": value}, {}, as_of=AT
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["revoked"]


def test_edge_active_true_does_not_override_inactive_credential():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"active": False}, {"active": True}, as_of=AT
    )
    assert ok is False
    assert reasons == ["credential_or_edge_inactive"]
    assert unresolved == []


def test_edge_revoked_false_does_not_override_revoked_credential():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"revoked": True}, {"revoked": False}, as_of=AT
    )
    assert ok is False
    assert reasons == ["credential_or_edge_revoked"]
    assert unresolved == []


def test_malformed_edge_revocation_state_does_not_fall_through_to_valid_attribute():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"revocation_state": "active"}, {"revocation_state": False}, as_of=AT
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["revocation_state"]


def test_exact_boolean_state_can_remain_usable():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"active": True, "revoked": False, "revocation_state": "active"},
        {"active": True, "revoked": False},
        as_of=AT,
    )
    assert ok is True
    assert reasons == []
    assert unresolved == []
