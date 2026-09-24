from datetime import datetime, timezone

import pytest

from testamur.authority_credentials import credential_constraints_satisfied


AT = datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("value", [None, False, "", [], {}, ()])
def test_unknown_constraint_is_unresolved_even_when_falsey(value):
    ok, reasons, unresolved = credential_constraints_satisfied(
        {},
        {"provider_specific_constraint": value},
        as_of=AT,
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["provider_specific_constraint"]


def test_unknown_constraint_is_unresolved_when_truthy():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {},
        {"provider_specific_constraint": "required"},
        as_of=AT,
    )

    assert ok is False
    assert reasons == []
    assert unresolved == ["provider_specific_constraint"]


@pytest.mark.parametrize("key", ["", "   ", 7, None])
def test_unknown_constraint_key_must_be_exact_nonempty_string(key):
    with pytest.raises(ValueError, match="constraint keys"):
        credential_constraints_satisfied({}, {key: False}, as_of=AT)


def test_absent_unknown_constraint_does_not_block_known_exact_evidence():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"audience": "svc:testamur", "scope": ["repo.read"]},
        {"required_audience": "svc:testamur", "required_scope": ["repo.read"]},
        as_of=AT,
    )

    assert ok is True
    assert reasons == []
    assert unresolved == []
