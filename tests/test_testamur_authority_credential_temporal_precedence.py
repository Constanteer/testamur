from __future__ import annotations

from datetime import datetime, timezone

import pytest

from testamur.authority_credentials import credential_constraints_satisfied


NOW = datetime(2026, 9, 24, 4, 0, tzinfo=timezone.utc)
VALID_EXPIRY = "2026-09-25T04:00:00Z"
VALID_NBF = "2026-09-23T04:00:00Z"


@pytest.mark.parametrize("malformed", [False, 0, "", {}, []])
def test_explicit_malformed_edge_expiry_does_not_fall_back_to_credential_attribute(malformed):
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"expires_at": VALID_EXPIRY},
        {"expires_at": malformed},
        as_of=NOW,
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["expires_at"]


@pytest.mark.parametrize("malformed", [False, 0, "", {}, []])
def test_explicit_malformed_edge_not_before_does_not_fall_back_to_credential_attribute(malformed):
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"not_before": VALID_NBF},
        {"not_before": malformed},
        as_of=NOW,
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["not_before"]


def test_explicit_malformed_not_before_alias_does_not_fall_through_to_nbf_alias():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {},
        {"not_before": "", "nbf": VALID_NBF},
        as_of=NOW,
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["not_before"]


def test_absent_edge_temporal_constraint_may_use_explicit_credential_attribute():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"expires_at": VALID_EXPIRY, "not_before": VALID_NBF},
        {},
        as_of=NOW,
    )
    assert ok is True
    assert reasons == []
    assert unresolved == []
