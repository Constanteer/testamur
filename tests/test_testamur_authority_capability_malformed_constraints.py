from testamur.authority_capability import (
    capability_allowed,
    capability_is_attenuation,
    delegation_budget,
    edge_capabilities,
    project_budget,
)


def cap(**overrides):
    value = {
        "namespace": "github",
        "action": "contents:write",
        "resource": "repo:Constanteer/testamur",
        "constraints": {},
    }
    value.update(overrides)
    return value


def test_invalid_expiry_is_not_unbounded_authority():
    malformed = cap(constraints={"expires_at": "not-a-timestamp"})
    assert not capability_allowed(malformed, None)
    assert not capability_is_attenuation(malformed, cap())
    assert project_budget((malformed,)) == []


def test_non_object_constraints_fail_closed_even_outside_importer():
    malformed = cap(constraints=["admin:org"])
    edge = {"relation_type": "HAS_CAPABILITY", "capabilities": [malformed]}
    assert edge_capabilities(edge, budget=None) == []


def test_malformed_boolean_gate_cannot_be_interpreted_as_no_gate():
    malformed = cap(constraints={"approval_required": "false"})
    edge = {"relation_type": "DELEGATES", "capabilities": [malformed]}
    assert delegation_budget(edge, None) == ()


def test_blank_resource_is_not_a_wildcard():
    malformed = cap(resource="   ")
    assert not capability_allowed(malformed, None)
    assert project_budget((malformed,)) == []
