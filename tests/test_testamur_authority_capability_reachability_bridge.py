from testamur.authority_capability import delegation_budget, edge_capabilities, project_budget


def _cap(*, scopes=("repo:read",), approval=True):
    return {
        "namespace": "github",
        "action": "contents.read",
        "resource": "repo:Constanteer/testamur",
        "constraints": {
            "required_scopes": list(scopes),
            "approval_required": approval,
            "audience": ["api.github.com"],
        },
    }


def test_delegation_budget_preserves_constraints_and_blocks_widening():
    parent = _cap()
    delegated = {"relation_type": "DELEGATES", "capabilities": [parent]}
    budget = delegation_budget(delegated, None)
    assert project_budget(budget) == [parent]

    unconstrained = {
        "namespace": "github",
        "action": "contents.read",
        "resource": "repo:Constanteer/testamur",
        "constraints": {},
    }
    edge = {"relation_type": "HAS_CAPABILITY", "capabilities": [unconstrained]}
    assert edge_capabilities(edge, budget=budget) == []


def test_downstream_capability_may_attenuate_but_not_add_scope():
    budget = delegation_budget(
        {"relation_type": "DELEGATES", "capabilities": [_cap(scopes=("repo:read", "metadata:read"))]},
        None,
    )
    narrower = _cap(scopes=("repo:read",))
    wider = _cap(scopes=("repo:read", "admin:org"))
    assert edge_capabilities({"relation_type": "HAS_CAPABILITY", "capabilities": [narrower]}, budget=budget) == [narrower]
    assert edge_capabilities({"relation_type": "HAS_CAPABILITY", "capabilities": [wider]}, budget=budget) == []


def test_empty_delegation_is_never_unrestricted():
    assert delegation_budget({"relation_type": "DELEGATES"}, None) == ()
    assert edge_capabilities({"relation_type": "HAS_CAPABILITY", "capabilities": [_cap()]}, budget=()) == []


def test_connectivity_without_capability_does_not_infer_permission():
    budget = delegation_budget({"relation_type": "CAN_CONNECT"}, None)
    assert budget is None
    assert edge_capabilities({"relation_type": "CAN_CONNECT"}, budget=budget) == []


def test_connectivity_rejects_even_caller_supplied_implicit_capability():
    implicit = {"namespace": "testamur", "action": "connect", "resource": "service:api", "constraints": {}}
    assert edge_capabilities(
        {"relation_type": "CAN_CONNECT", "target_ref": "service:api"},
        budget=None,
        implicit_capability=implicit,
    ) == []


def test_authorized_action_relation_may_supply_semantic_implicit_capability():
    implicit = {"namespace": "testamur", "action": "read", "resource": "artifact:manifest", "constraints": {}}
    assert edge_capabilities(
        {"relation_type": "CAN_READ", "target_ref": "artifact:manifest"},
        budget=None,
        implicit_capability=implicit,
    ) == [implicit]


def test_issuer_and_tenant_constraints_cannot_be_dropped_or_widened():
    parent = _cap()
    parent["constraints"].update({
        "required_issuer": ["https://token.actions.githubusercontent.com"],
        "tenant_id": ["installation:42", "installation:43"],
    })
    budget = delegation_budget({"relation_type": "DELEGATES", "capabilities": [parent]}, None)

    narrowed = _cap()
    narrowed["constraints"].update({
        "issuer": ["https://token.actions.githubusercontent.com"],
        "tenant": ["installation:42"],
    })
    assert edge_capabilities({"relation_type": "HAS_CAPABILITY", "capabilities": [narrowed]}, budget=budget) == [narrowed]

    missing_issuer = _cap()
    missing_issuer["constraints"].update({"tenant": ["installation:42"]})
    assert edge_capabilities({"relation_type": "HAS_CAPABILITY", "capabilities": [missing_issuer]}, budget=budget) == []

    cross_tenant = _cap()
    cross_tenant["constraints"].update({
        "issuer": ["https://token.actions.githubusercontent.com"],
        "tenant": ["installation:99"],
    })
    assert edge_capabilities({"relation_type": "HAS_CAPABILITY", "capabilities": [cross_tenant]}, budget=budget) == []


def test_malformed_capability_payloads_are_not_wildcards():
    missing_namespace = {"action": "contents.read", "constraints": {}}
    missing_action = {"namespace": "github", "constraints": {}}
    blank_action = {"namespace": "github", "action": "  ", "constraints": {}}

    assert edge_capabilities(
        {"relation_type": "HAS_CAPABILITY", "capabilities": [missing_namespace, missing_action, blank_action]},
        budget=None,
    ) == []
    assert delegation_budget(
        {"relation_type": "DELEGATES", "capabilities": [missing_namespace]},
        None,
    ) == ()


def test_malformed_inherited_budget_cannot_authorize_downstream_capability():
    malformed_budget = ({"namespace": "", "action": "contents.read", "constraints": {}},)
    assert edge_capabilities(
        {"relation_type": "HAS_CAPABILITY", "capabilities": [_cap()]},
        budget=malformed_budget,
    ) == []
    assert project_budget(malformed_budget) == []
