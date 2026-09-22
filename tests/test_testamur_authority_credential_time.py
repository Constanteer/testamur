from datetime import datetime, timezone

import pytest

from testamur.authority_credentials import credential_constraints_satisfied


def test_credential_expiry_requires_explicit_timezone() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"expires_at": "2026-09-22T01:00:00"},
        {},
        as_of=datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc),
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["expires_at"]


def test_credential_not_before_requires_explicit_timezone() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"not_before": "2026-09-22T00:00:00"},
        {},
        as_of=datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc),
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["not_before"]


def test_credential_observation_instant_requires_explicit_timezone() -> None:
    with pytest.raises(ValueError, match="explicit timezone"):
        credential_constraints_satisfied(
            {"expires_at": "2026-09-22T01:00:00Z"},
            {},
            as_of=datetime(2026, 9, 22, 0, 0),
        )


def test_equivalent_zoned_credential_times_compare_as_same_instant() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {
            "not_before": "2026-09-22T08:00:00+08:00",
            "expires_at": "2026-09-22T09:00:00+08:00",
        },
        {},
        as_of=datetime(2026, 9, 22, 0, 30, tzinfo=timezone.utc),
    )

    assert ok is True
    assert reasons == []
    assert unresolved == []
