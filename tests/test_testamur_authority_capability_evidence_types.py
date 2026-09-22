from testamur.authority_capability import capability_allowed, capability_is_attenuation, delegation_budget


def cap(**constraints):
    return {"namespace": "github", "action": "contents:write", "resource": "repo:a", "constraints": constraints}


def test_set_valued_authority_evidence_never_stringifies_objects():
    for key in ("scope", "audience", "service_ref", "tenant_id", "repository_ref"):
        assert not capability_allowed(cap(**{key: {"ref": "x"}}), None)
        assert not capability_allowed(cap(**{key: 42}), None)
        assert not capability_allowed(cap(**{key: ["ok", 42]}), None)
        assert not capability_allowed(cap(**{key: []}), None)


def test_malformed_parent_or_child_evidence_cannot_participate_in_attenuation():
    parent = cap(scopes=["contents:write"], audience=["github-app"], service_ref=["svc:github"])
    assert not capability_is_attenuation(cap(scope={"name": "contents:write"}, audience="github-app", service_ref="svc:github"), parent)
    assert not capability_is_attenuation(cap(scope="contents:write", audience="github-app", service_ref="svc:github"), cap(scopes=42))


def test_malformed_delegated_connector_permission_produces_no_budget():
    edge = {
        "relation_type": "DELEGATES",
        "capabilities": [cap(scope="contents:write", audience={"unexpected": "github-app"})],
    }
    assert delegation_budget(edge, None) == ()


def test_explicit_string_and_string_list_evidence_remains_exact():
    parent = cap(scopes=["contents:write", "metadata:read"], audiences=["github-app"], service_refs=["svc:github"])
    child = cap(scope="contents:write", audience="github-app", service_ref="svc:github")
    assert capability_allowed(parent, None)
    assert capability_is_attenuation(child, parent)
