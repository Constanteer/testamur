from __future__ import annotations

from testamur.authority_graph_constraints import (
    evaluate_exact_edge_constraints,
    graph_context_constraints_satisfied,
    resolve_graph_context_verdict,
)


def test_exact_resource_constraint_matches_traversed_target_only() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:Constanteer/testamur"}, source_ref="connector:github", target_ref="repo:Constanteer/testamur", unresolved=["resource"]
    )
    assert (ok, reasons, unresolved) == (True, [], [])


def test_resource_constraint_cannot_be_satisfied_by_connectivity_to_other_resource() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:Constanteer/other"}, source_ref="connector:github", target_ref="repo:Constanteer/testamur", unresolved=["resource"]
    )
    assert (ok, reasons, unresolved) == (False, ["resource_mismatch"], [])


def test_resource_pattern_is_matched_against_exact_target_identity() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource_pattern": "repo:Constanteer/*"}, source_ref="connector:github", target_ref="repo:Constanteer/testamur", unresolved=["resource_pattern"]
    )
    assert (ok, reasons, unresolved) == (True, [], [])


def test_principal_constraint_matches_exact_source_identity() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"principal": "user:alice"}, source_ref="user:alice", target_ref="service:api", unresolved=["principal"]
    )
    assert (ok, reasons, unresolved) == (True, [], [])


def test_generic_name_or_id_is_not_authorization_evidence() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:Constanteer/testamur"}, source_ref="connector:github", target_ref="resource:opaque-17",
        target_subject={"name": "repo:Constanteer/testamur", "attributes": {"id": "repo:Constanteer/testamur"}}, unresolved=["resource"]
    )
    assert (ok, reasons, unresolved) == (False, ["resource_mismatch"], [])


def test_runtime_context_remains_fail_closed_without_evidence() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"network_zone": "corp", "device_binding": "managed"}, source_ref="user:alice", target_ref="service:api", unresolved=["network_zone", "device_binding"]
    )
    assert (ok, reasons, unresolved) == (False, [], ["device_binding", "network_zone"])


def test_empty_graph_constraint_value_fails_closed() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": ""}, source_ref="connector:github", target_ref="repo:Constanteer/testamur", unresolved=["resource"]
    )
    assert (ok, reasons, unresolved) == (False, ["resource_constraint_missing_value"], [])


def test_graph_context_can_discharge_unresolved_resource() -> None:
    ok, reasons, unresolved = resolve_graph_context_verdict(
        {"resource": "repo:Constanteer/testamur"}, (False, [], ["resource"]),
        source_ref="connector:github", target_ref="repo:Constanteer/testamur"
    )
    assert (ok, reasons, unresolved) == (True, [], [])


def test_graph_context_never_launders_credential_failure() -> None:
    ok, reasons, unresolved = resolve_graph_context_verdict(
        {"resource": "repo:Constanteer/testamur", "required_audience": "github.com"},
        (False, ["audience_mismatch"], ["resource"]), source_ref="connector:github", target_ref="repo:Constanteer/testamur"
    )
    assert (ok, reasons, unresolved) == (False, ["audience_mismatch"], [])


def test_graph_context_preserves_unresolved_runtime_gate() -> None:
    ok, reasons, unresolved = resolve_graph_context_verdict(
        {"resource": "repo:Constanteer/testamur", "device_binding": "managed"},
        (False, [], ["resource", "device_binding"]), source_ref="connector:github", target_ref="repo:Constanteer/testamur"
    )
    assert (ok, reasons, unresolved) == (False, [], ["device_binding"])


def test_exact_edge_composes_token_audience_scope_and_resource() -> None:
    edge = {
        "source_ref": "connector:github",
        "target_ref": "repo:Constanteer/testamur",
        "constraints": {
            "required_audience": "github.com",
            "required_scopes": ["contents:read"],
            "resource": "repo:Constanteer/testamur",
        },
    }
    verdict = evaluate_exact_edge_constraints(
        edge,
        credential_attributes={"audiences": ["github.com"], "scopes": ["contents:read", "metadata:read"]},
        as_of="2026-09-19T06:00:00Z",
    )
    assert verdict == (True, [], [])


def test_exact_edge_wrong_resource_blocks_even_with_valid_token_metadata() -> None:
    edge = {
        "source_ref": "connector:github",
        "target_ref": "repo:Constanteer/testamur",
        "constraints": {"required_audience": "github.com", "resource": "repo:Constanteer/other"},
    }
    verdict = evaluate_exact_edge_constraints(
        edge,
        credential_attributes={"audiences": ["github.com"]},
        as_of="2026-09-19T06:00:00Z",
    )
    assert verdict == (False, ["resource_mismatch"], [])


def test_exact_edge_runtime_gate_stays_unresolved_after_graph_match() -> None:
    edge = {
        "source_ref": "connector:github",
        "target_ref": "repo:Constanteer/testamur",
        "constraints": {"resource": "repo:Constanteer/testamur", "device_binding": "managed"},
    }
    verdict = evaluate_exact_edge_constraints(edge, credential_attributes={}, as_of="2026-09-19T06:00:00Z")
    assert verdict == (False, [], ["device_binding"])
