from testamur.authority_projection import (
    capability_identity,
    project_authority_budget,
    projected_budget_identity,
)


def test_capability_identity_does_not_collapse_different_scopes():
    read_only = {
        "namespace": "github",
        "action": "issues",
        "resource": "repo:acme/widget",
        "constraints": {"required_scopes": ["issues:read"]},
    }
    admin = {
        "namespace": "github",
        "action": "issues",
        "resource": "repo:acme/widget",
        "constraints": {"required_scopes": ["issues:read", "admin:org"]},
    }

    assert capability_identity(read_only) != capability_identity(admin)
    assert projected_budget_identity((read_only,)) != projected_budget_identity((admin,))


def test_budget_projection_preserves_audience_tenant_and_bindings():
    capability = {
        "namespace": "connector",
        "action": "write",
        "resource": "project:alpha",
        "constraints": {
            "required_audience": ["testamur-product"],
            "tenant_id": ["tenant-a"],
            "device_binding": ["device-7"],
            "approval_required": True,
        },
    }

    assert project_authority_budget((capability,)) == [capability]


def test_unrestricted_and_empty_budgets_remain_distinct():
    assert projected_budget_identity(None) is None
    assert projected_budget_identity(()) == ()
    assert project_authority_budget(None) is None
    assert project_authority_budget(()) == []
