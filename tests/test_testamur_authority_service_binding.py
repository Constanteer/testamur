from datetime import datetime, timezone

from testamur.authority_credentials import credential_constraints_satisfied
from testamur.authority_graph_constraints import evaluate_exact_edge_constraints


NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)


def edge(relation="DELEGATES", *, target="svc:github", service_ref="svc:github"):
    return {
        "edge_id": "edge:service-binding",
        "source_ref": "connector:1",
        "target_ref": target,
        "relation_type": relation,
        "constraints": {"service_ref": service_ref},
    }


def test_service_ref_is_not_silently_ignored_by_credential_stage():
    ok, reasons, unresolved = credential_constraints_satisfied(
        {}, {"service_ref": "svc:github"}, as_of=NOW
    )
    assert not ok
    assert reasons == []
    assert unresolved == ["service_ref"]


def test_delegation_service_binding_must_match_exact_target():
    ok, reasons, unresolved = evaluate_exact_edge_constraints(
        edge(), credential_attributes={}, as_of=NOW
    )
    assert ok
    assert reasons == []
    assert unresolved == []

    ok, reasons, unresolved = evaluate_exact_edge_constraints(
        edge(target="svc:other"), credential_attributes={}, as_of=NOW
    )
    assert not ok
    assert reasons == ["service_mismatch"]
    assert unresolved == []


def test_explicit_target_service_alias_can_prove_binding_without_graph_search():
    ok, reasons, unresolved = evaluate_exact_edge_constraints(
        edge(target="connector-account:github"),
        credential_attributes={},
        target_subject={"attributes": {"service_ref": "svc:github"}},
        as_of=NOW,
    )
    assert ok
    assert reasons == []
    assert unresolved == []


def test_malformed_or_conflicting_service_aliases_fail_closed():
    ok, reasons, unresolved = evaluate_exact_edge_constraints(
        edge(target="connector-account:github"),
        credential_attributes={},
        target_subject={"service_ref": "svc:github", "attributes": {"service_ref": "svc:other"}},
        as_of=NOW,
    )
    assert not ok
    assert reasons == ["service_evidence_malformed_or_conflicting"]
    assert unresolved == []

    malformed = edge(service_ref=123)
    ok, reasons, unresolved = evaluate_exact_edge_constraints(
        malformed, credential_attributes={}, as_of=NOW
    )
    assert not ok
    assert reasons == ["service_constraint_malformed_or_conflicting"]
    assert unresolved == []


def test_authentication_service_ref_is_deferred_to_acceptance_support_edge():
    # The exact edge target is an account, not the accepting service. The raw
    # constraint evaluator must not reject it as a service mismatch; reachability
    # subsequently requires an explicit service -> credential ACCEPTS_CREDENTIAL edge.
    ok, reasons, unresolved = evaluate_exact_edge_constraints(
        edge(relation="CAN_AUTHENTICATE_AS", target="account:alice"),
        credential_attributes={},
        as_of=NOW,
    )
    assert ok
    assert reasons == []
    assert unresolved == []
