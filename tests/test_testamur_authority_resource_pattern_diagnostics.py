from testamur.authority_reachability_policy import capability_rejection_diagnostics


def cap(resource=None, **constraints):
    value = {"namespace": "github", "action": "contents:write", "constraints": constraints}
    if resource is not None:
        value["resource"] = resource
    return value


def edge(*capabilities):
    return {"relation_type": "HAS_CAPABILITY", "capabilities": list(capabilities)}


def test_concrete_resource_outside_inherited_pattern_has_exact_reason():
    parent = cap(resource_pattern="org/project-*", approval_required=True)
    candidate = cap("other/project-api", approval_required=True)
    result = capability_rejection_diagnostics(edge(candidate), (parent,))

    assert result is not None
    assert result["reasons"] == ["resource_pattern_outside_delegation"]
    assert result["failed_constraints"] == ["resource_pattern"]
    assert result["candidate_capabilities"] == [candidate]
    assert result["inherited_capability_budget"] == [parent]


def test_pattern_only_child_cannot_widen_or_drop_inherited_pattern():
    parent = cap(resource_pattern="org/project-*", approval_required=True)

    widened = capability_rejection_diagnostics(
        edge(cap(resource_pattern="*", approval_required=True)), (parent,)
    )
    assert widened is not None
    assert widened["reasons"] == ["resource_pattern_not_preserved"]
    assert widened["failed_constraints"] == ["resource_pattern"]

    dropped = capability_rejection_diagnostics(
        edge(cap(approval_required=True)), (parent,)
    )
    assert dropped is not None
    assert dropped["reasons"] == ["resource_pattern_not_preserved"]
    assert dropped["failed_constraints"] == ["resource_pattern"]


def test_concrete_resource_inside_inherited_pattern_is_not_reported_as_denied():
    parent = cap(resource_pattern="org/project-*", approval_required=True)
    candidate = cap("org/project-api", approval_required=True)
    assert capability_rejection_diagnostics(edge(candidate), (parent,)) is None
