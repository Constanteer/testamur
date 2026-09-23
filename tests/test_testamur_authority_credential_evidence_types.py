from datetime import datetime, timezone

from testamur.authority_credentials import credential_constraints_satisfied


NOW = datetime(2026, 9, 22, tzinfo=timezone.utc)


def evaluate(attributes, constraints):
    return credential_constraints_satisfied(attributes, constraints, as_of=NOW)


def test_scope_claim_does_not_stringify_non_string_scalar():
    ok, reasons, unresolved = evaluate({"scope": 42}, {"scope": "42"})
    assert not ok
    assert reasons == []
    assert unresolved == ["scope"]


def test_audience_claim_does_not_stringify_mapping():
    ok, reasons, unresolved = evaluate(
        {"audience": {"ref": "github-app"}},
        {"audience": "github-app"},
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["audience"]


def test_mixed_scope_sequence_is_unresolved_not_partial_grant():
    ok, reasons, unresolved = evaluate(
        {"scopes": ["contents:write", 7]},
        {"required_scope": "contents:write"},
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["scope"]


def test_conflicting_actual_aliases_are_ambiguous_not_union():
    ok, reasons, unresolved = evaluate(
        {"scope": "contents:write", "scopes": ["metadata:read"]},
        {"required_scope": "contents:write"},
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["scope"]


def test_conflicting_required_aliases_are_ambiguous_not_additive():
    ok, reasons, unresolved = evaluate(
        {"scopes": ["contents:write", "metadata:read"]},
        {"scope": "contents:write", "required_scopes": ["metadata:read"]},
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["scope"]


def test_equivalent_singular_and_plural_aliases_are_valid_encodings():
    ok, reasons, unresolved = evaluate(
        {
            "scope": "contents:write",
            "scopes": ["contents:write"],
            "audience": "github-app",
            "audiences": ["github-app"],
        },
        {
            "required_scope": "contents:write",
            "required_scopes": ["contents:write"],
            "required_audience": "github-app",
            "required_audiences": ["github-app"],
        },
    )
    assert ok
    assert reasons == []
    assert unresolved == []


def test_expiry_does_not_stringify_non_string_temporal_evidence():
    ok, reasons, unresolved = evaluate({}, {"expires_at": 20260923})
    assert not ok
    assert reasons == []
    assert unresolved == ["expires_at"]


def test_not_before_does_not_stringify_datetime_object():
    ok, reasons, unresolved = evaluate(
        {"not_before": datetime(2026, 9, 21, tzinfo=timezone.utc)},
        {},
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["not_before"]


def test_revocation_state_does_not_stringify_typed_evidence():
    ok, reasons, unresolved = evaluate({"revocation_state": 7}, {})
    assert not ok
    assert reasons == []
    assert unresolved == ["revocation_state"]
