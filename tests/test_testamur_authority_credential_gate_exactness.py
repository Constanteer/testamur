from __future__ import annotations

from datetime import datetime, timezone

import pytest

from testamur.authority_credentials import credential_constraints_satisfied


AT = datetime(2026, 9, 24, 6, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("gate", ["approval_required", "human_confirmation_required", "mfa_required"])
@pytest.mark.parametrize("value", [None, "true", "false", 0, 1, {}, []])
def test_interactive_credential_gates_require_exact_boolean_evidence(gate: str, value: object) -> None:
    ok, reasons, unresolved = credential_constraints_satisfied({}, {gate: value}, as_of=AT)

    assert ok is False
    assert reasons == []
    assert unresolved == [gate]


@pytest.mark.parametrize("gate", ["approval_required", "human_confirmation_required", "mfa_required"])
def test_true_interactive_gate_blocks_without_becoming_authority(gate: str) -> None:
    ok, reasons, unresolved = credential_constraints_satisfied({}, {gate: True}, as_of=AT)

    assert ok is False
    assert reasons == [gate]
    assert unresolved == []


@pytest.mark.parametrize("gate", ["approval_required", "human_confirmation_required", "mfa_required"])
def test_false_interactive_gate_is_explicitly_satisfied(gate: str) -> None:
    ok, reasons, unresolved = credential_constraints_satisfied({}, {gate: False}, as_of=AT)

    assert ok is True
    assert reasons == []
    assert unresolved == []
