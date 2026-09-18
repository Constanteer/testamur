from testamur.authority_capability import attenuate_budget, capability_allowed, capability_is_attenuation


def cap(resource=None, **constraints):
    value = {"namespace": "github", "action": "contents:write", "constraints": constraints}
    if resource is not None:
        value["resource"] = resource
    return value


def test_delegation_cannot_drop_approval_or_scope_constraints():
    parent = cap("repo:a", scopes=["contents:write", "metadata:read"], approval_required=True)
    assert not capability_is_attenuation(cap("repo:a", scopes=["contents:write"]), parent)
    assert capability_is_attenuation(
        cap("repo:a", scopes=["contents:write"], approval_required=True, mfa_required=True), parent
    )


def test_delegation_cannot_widen_resource_pattern():
    parent = cap(resource_pattern="org/project-*", approval_required=True)
    assert capability_is_attenuation(cap("org/project-api", approval_required=True), parent)
    assert not capability_is_attenuation(cap("other/project-api", approval_required=True), parent)
    assert not capability_is_attenuation(cap(resource_pattern="*", approval_required=True), parent)


def test_unknown_parent_constraint_must_be_preserved_exactly():
    parent = cap("repo:a", provider_condition={"ref": "refs/heads/main"})
    assert not capability_is_attenuation(cap("repo:a"), parent)
    assert capability_is_attenuation(
        cap("repo:a", provider_condition={"ref": "refs/heads/main"}), parent
    )


def test_inherited_budget_filters_widened_downstream_capability():
    inherited = (cap("repo:a", approval_required=True),)
    downstream = [cap("repo:a"), cap("repo:a", approval_required=True)]
    budget = attenuate_budget(downstream, inherited)
    assert len(budget) == 1
    assert budget[0]["constraints"]["approval_required"] is True
    assert capability_allowed(cap("repo:a", approval_required=True), budget)
    assert not capability_allowed(cap("repo:a"), budget)
