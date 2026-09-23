from datetime import datetime, timezone

from testamur.authority_capability import (
    attenuate_budget,
    capability_allowed,
    capability_is_attenuation,
    delegation_budget,
)


def cap(**constraints):
    return {
        "namespace": "github",
        "action": "contents:write",
        "resource": "repo:a",
        "constraints": constraints,
    }


def test_typed_expiry_cannot_be_coerced_into_delegated_authority():
    typed = cap(expires_at=datetime(2026, 9, 23, 12, tzinfo=timezone.utc))
    assert not capability_allowed(typed, None)
    assert attenuate_budget([typed], None) == ()
    assert delegation_budget({"relation_type": "DELEGATES", "capabilities": [typed]}, None) == ()


def test_numeric_expiry_cannot_be_coerced_into_delegated_authority():
    malformed = cap(expires_at=1790164800)
    assert not capability_allowed(malformed, None)
    assert attenuate_budget([malformed], None) == ()


def test_naive_expiry_is_not_exact_temporal_authority_evidence():
    malformed = cap(expires_at="2026-09-23T12:00:00")
    assert not capability_allowed(malformed, None)


def test_typed_resource_pattern_cannot_be_stringified_into_authority_scope():
    malformed = cap(resource_pattern=["repo:*", "other:*"])
    assert not capability_allowed(malformed, None)
    assert not capability_is_attenuation(cap(), malformed)


def test_empty_resource_pattern_fails_closed():
    malformed = cap(resource_pattern="   ")
    assert not capability_allowed(malformed, None)


def test_exact_expiry_and_resource_pattern_still_attenuate():
    parent = cap(resource_pattern="repo:*", expires_at="2026-09-23T12:00:00Z")
    child = {
        "namespace": "github",
        "action": "contents:write",
        "resource": "repo:b",
        "constraints": {"expires_at": "2026-09-23T11:00:00Z"},
    }
    assert capability_is_attenuation(child, parent)
