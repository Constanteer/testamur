from datetime import datetime, timezone

from testamur.authority_credentials import credential_constraints_satisfied


NOW = datetime(2026, 9, 19, tzinfo=timezone.utc)


def test_required_audience_scope_issuer_and_tenant_are_checked_explicitly():
    attributes = {
        "audiences": ["api://testamur"],
        "scopes": ["repo:read", "issues:write"],
        "issuer": "https://issuer.example",
        "tenant_id": "tenant-a",
    }
    constraints = {
        "required_audience": "api://testamur",
        "required_scopes": ["repo:read"],
        "required_issuer": "https://issuer.example",
        "tenant": "tenant-a",
    }
    assert credential_constraints_satisfied(attributes, constraints, as_of=NOW) == (True, [], [])


def test_scope_requires_subset_but_audience_is_membership():
    attributes = {"audiences": ["api://one", "api://two"], "scopes": ["repo:read"]}
    ok, reasons, unresolved = credential_constraints_satisfied(
        attributes,
        {"required_audiences": ["api://two"], "required_scopes": ["repo:read", "admin:org"]},
        as_of=NOW,
    )
    assert not ok
    assert reasons == ["scope_mismatch"]
    assert unresolved == []


def test_missing_identity_metadata_fails_closed_instead_of_inference():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"scopes": ["repo:read"]},
        {"required_issuer": "https://issuer.example", "tenant_id": "tenant-a"},
        as_of=NOW,
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["issuer", "tenant"]


def test_unknown_provider_constraint_fails_closed():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {}, {"provider_condition": {"installation_id": 42}}, as_of=NOW
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["provider_condition"]


def test_expired_or_malformed_expiry_is_not_valid_authority():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"expires_at": "2026-09-18T00:00:00Z"}, {}, as_of=NOW
    )
    assert not ok and reasons == ["credential_or_edge_expired"] and unresolved == []

    ok, reasons, unresolved = credential_constraints_satisfied(
        {"expires_at": "not-a-time"}, {}, as_of=NOW
    )
    assert not ok and reasons == [] and unresolved == ["expires_at"]


def test_metadata_match_does_not_create_or_claim_authority():
    # The evaluator deliberately has no graph/store argument and returns only a
    # constraint verdict. Matching token metadata is evidence about an explicit
    # edge; it is never itself an authority edge.
    assert credential_constraints_satisfied(
        {"audience": "api://testamur", "scope": "repo:read"},
        {"required_audience": "api://testamur", "required_scope": "repo:read"},
        as_of=NOW,
    )[0]
