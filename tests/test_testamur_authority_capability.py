from testamur.authority_capability import (
    attenuate_budget,
    capability_allowed,
    capability_is_attenuation,
    project_budget,
)


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


def test_delegation_cannot_drop_binding_or_trust_context():
    parent = cap(
        "repo:a",
        audience=["github-app"],
        service_ref=["svc:github"],
        network_zone=["prod"],
        device_binding=["device:1"],
        session_binding=["session:1"],
    )
    assert capability_is_attenuation(
        cap(
            "repo:a",
            audience=["github-app"],
            service_ref=["svc:github"],
            network_zone=["prod"],
            device_binding=["device:1"],
            session_binding=["session:1"],
        ),
        parent,
    )
    assert not capability_is_attenuation(
        cap("repo:a", audience=["github-app"], service_ref=["svc:github"]),
        parent,
    )


def test_constraint_aliases_are_semantic_not_authority_widening():
    parent = cap(
        "repo:a",
        scopes=["contents:write", "metadata:read"],
        audiences=["github-app", "github-api"],
        service_refs=["svc:github"],
    )
    assert capability_is_attenuation(
        cap(
            "repo:a",
            scope=["contents:write"],
            audience=["github-app"],
            service_ref="svc:github",
        ),
        parent,
    )
    assert not capability_is_attenuation(
        cap(
            "repo:a",
            scope=["contents:write", "admin"],
            audience=["github-app"],
            service_ref="svc:github",
        ),
        parent,
    )


def test_plural_binding_aliases_cannot_be_dropped():
    parent = cap(
        "repo:a",
        network_zones=["prod"],
        source_ips=["10.0.0.8"],
        device_bindings=["device:1"],
        session_bindings=["session:1"],
    )
    assert capability_is_attenuation(
        cap(
            "repo:a",
            network_zone="prod",
            source_ip="10.0.0.8",
            device_binding="device:1",
            session_binding="session:1",
        ),
        parent,
    )
    assert not capability_is_attenuation(cap("repo:a", network_zone="prod"), parent)


def test_expiry_attenuation_uses_timestamps_not_lexical_order():
    parent = cap("repo:a", expires_at="2026-09-18T12:00:00Z")
    # Same instant, different offset: valid attenuation.
    assert capability_is_attenuation(
        cap("repo:a", expires_at="2026-09-18T20:00:00+08:00"), parent
    )
    assert capability_is_attenuation(
        cap("repo:a", expires_at="2026-09-18T11:59:59Z"), parent
    )
    assert not capability_is_attenuation(
        cap("repo:a", expires_at="2026-09-18T12:00:01Z"), parent
    )
    assert not capability_is_attenuation(cap("repo:a", expires_at="not-a-time"), parent)


def test_budget_projection_preserves_constraints_for_product_surfaces():
    budget = attenuate_budget(
        [cap("repo:a", approval_required=True, scopes=["contents:write"])],
        None,
    )
    projected = project_budget(budget)
    assert projected == [
        cap("repo:a", approval_required=True, scopes=["contents:write"])
    ]
    assert project_budget(None) is None
