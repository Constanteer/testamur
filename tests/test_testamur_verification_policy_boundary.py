from __future__ import annotations

from pathlib import Path

from testamur.model import ObjectKind, VerificationStatus, VerifierClass
from testamur.verification_policy import authorize_verification, verifier_contract


ROOT = Path(__file__).resolve().parents[1]


def _verifier(verifier_class: str, *, allowed_statuses: list[str] | None = None) -> dict[str, object]:
    payload: dict[str, object] = {"verifier_class": verifier_class}
    if allowed_statuses is not None:
        payload["allowed_statuses"] = allowed_statuses
    return {"kind": ObjectKind.VERIFIER.value, "payload": payload}


def test_verifier_contract_is_not_the_purpose_scoped_policy_store() -> None:
    contract = verifier_contract(_verifier(VerifierClass.TEST_SUITE.value))
    assert contract["contract_version"] == "witness-verifier-contract-v0.1"
    assert contract["verifier_class"] == VerifierClass.TEST_SUITE.value
    assert VerificationStatus.TESTED.value in contract["allowed_statuses"]
    assert VerificationStatus.FORMALLY_PROVEN.value not in contract["allowed_statuses"]


def test_verifier_class_cannot_elevate_its_allowed_statuses() -> None:
    try:
        verifier_contract(
            _verifier(
                VerifierClass.TEST_SUITE.value,
                allowed_statuses=[VerificationStatus.FORMALLY_PROVEN.value],
            )
        )
    except ValueError as exc:
        assert "cannot elevate" in str(exc)
    else:
        raise AssertionError("test-suite verifier must not issue formally-proven status")


def test_authorization_is_capability_check_not_universal_truth() -> None:
    result = authorize_verification(
        _verifier(VerifierClass.MECHANICAL.value),
        VerificationStatus.TESTED.value,
    )
    assert result["status"] == VerificationStatus.TESTED.value
    assert "truth" not in result
    assert "relied" not in result


def test_retired_verifier_policy_shim_is_not_shipped() -> None:
    assert not (ROOT / "witness" / "policy.py").exists()
    assert not (ROOT / "witness_service").exists()
