from testamur.authority_exact import exact_implicit_capability


def test_exact_implicit_capability_projects_read_authority():
    assert exact_implicit_capability({"relation_type": "CAN_READ", "target_ref": "artifact:1"}) == {
        "namespace": "testamur",
        "action": "read",
        "resource": "artifact:1",
        "constraints": {},
    }


def test_exact_implicit_capability_rejects_typed_target_identity():
    assert exact_implicit_capability({"relation_type": "CAN_READ", "target_ref": 123}) is None
    assert exact_implicit_capability({"relation_type": "CAN_WRITE", "target_ref": {"ref": "artifact:1"}}) is None


def test_exact_implicit_capability_rejects_typed_relation_identity():
    assert exact_implicit_capability({"relation_type": 123, "target_ref": "artifact:1"}) is None


def test_exact_implicit_capability_does_not_turn_connectivity_into_authority():
    assert exact_implicit_capability({"relation_type": "CAN_CONNECT", "target_ref": "service:1"}) is None


def test_exact_implicit_capability_rejects_empty_identity_evidence():
    assert exact_implicit_capability({"relation_type": "CAN_READ", "target_ref": "   "}) is None
    assert exact_implicit_capability({"relation_type": "   ", "target_ref": "artifact:1"}) is None
