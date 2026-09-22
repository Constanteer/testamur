from testamur.authority_capability import (
    capability_is_attenuation,
    delegation_budget,
    edge_capabilities,
)


def _cap(expires_at: str) -> dict:
    return {
        "namespace": "github",
        "action": "contents:write",
        "resource": "repo:example/demo",
        "constraints": {"expires_at": expires_at},
    }


def test_ambiguous_capability_expiry_is_not_exercisable() -> None:
    edge = {"relation_type": "HAS_CAPABILITY", "capabilities": [_cap("2026-09-22T10:00:00")]}

    assert edge_capabilities(edge, budget=None) == []


def test_ambiguous_delegated_capability_does_not_enter_budget() -> None:
    edge = {"relation_type": "DELEGATES", "capabilities": [_cap("2026-09-22T10:00:00")]}

    assert delegation_budget(edge, None) == ()


def test_zoned_expiry_attenuation_compares_real_instants() -> None:
    parent = _cap("2026-09-22T10:00:00+08:00")
    child = _cap("2026-09-22T01:30:00Z")
    later_child = _cap("2026-09-22T02:30:00Z")

    assert capability_is_attenuation(child, parent) is True
    assert capability_is_attenuation(later_child, parent) is False
