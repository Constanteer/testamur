from testamur.authority_reachability_policy import (
    action_result_identity,
    downstream_budget,
    exercisable_capabilities,
    implicit_capability,
    project_downstream_budget,
    traversal_state_identity,
)


def _edge(relation, capabilities=None, target="service:repo"):
    return {
        "relation_type": relation,
        "target_ref": target,
        "capabilities": capabilities or [],
    }


def test_connectivity_never_manufactures_authority():
    edge = _edge("CAN_CONNECT")
    assert implicit_capability(edge) is None
    assert exercisable_capabilities(edge, None) == []


def test_action_relations_can_express_their_own_semantic_action():
    edge = _edge("CAN_READ")
    assert exercisable_capabilities(edge, None) == [
        {
            "namespace": "testamur",
            "action": "read",
            "resource": "service:repo",
            "constraints": {},
        }
    ]


def test_delegation_budget_preserves_scope_and_audience_and_blocks_widening():
    delegated = {
        "namespace": "github",
        "action": "contents:read",
        "resource": "repo:constanteer/testamur",
        "constraints": {
            "required_scopes": ["contents:read"],
            "required_audience": ["github-api"],
            "tenant_id": ["constanteer"],
        },
    }
    budget = downstream_budget(_edge("DELEGATES", [delegated]), None)
    assert project_downstream_budget(budget) == [delegated]

    widened = {
        **delegated,
        "constraints": {
            "required_scopes": ["contents:read", "administration:write"],
            "required_audience": ["github-api"],
            "tenant_id": ["constanteer"],
        },
    }
    assert exercisable_capabilities(_edge("HAS_CAPABILITY", [widened]), budget) == []


def test_empty_delegation_is_explicitly_empty_not_unrestricted():
    budget = downstream_budget(_edge("DELEGATES"), None)
    assert budget == ()
    assert project_downstream_budget(budget) == []
    assert exercisable_capabilities(
        _edge(
            "HAS_CAPABILITY",
            [{"namespace": "github", "action": "contents:read", "resource": "repo:x"}],
        ),
        budget,
    ) == []


def test_action_identity_does_not_collapse_different_scopes():
    base = {
        "namespace": "github",
        "action": "contents:read",
        "resource": "repo:constanteer/testamur",
    }
    narrow = {**base, "constraints": {"required_scopes": ["contents:read"]}}
    broader = {
        **base,
        "constraints": {"required_scopes": ["contents:read", "metadata:read"]},
    }
    assert action_result_identity("repo", narrow, ["edge:1"]) != action_result_identity(
        "repo", broader, ["edge:1"]
    )


def test_traversal_state_identity_keeps_delegation_budget_and_empty_distinct():
    capability = {
        "namespace": "github",
        "action": "contents:read",
        "resource": "repo:constanteer/testamur",
        "constraints": {
            "required_audience": ["github-api"],
            "tenant_id": ["constanteer"],
        },
    }
    constrained = (capability,)
    unrestricted = traversal_state_identity("connector:x", "CONTROLLED", None, ["e1"])
    empty = traversal_state_identity("connector:x", "CONTROLLED", (), ["e1"])
    delegated = traversal_state_identity("connector:x", "CONTROLLED", constrained, ["e1"])

    assert unrestricted != empty
    assert empty != delegated
    assert delegated[2] is not None
    assert "required_audience" in delegated[2][0]
    assert "tenant_id" in delegated[2][0]
