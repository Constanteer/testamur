from __future__ import annotations

from testamur.authority_graph_constraints import graph_context_constraints_satisfied


def test_exact_resource_constraint_matches_traversed_target_only() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:Constanteer/testamur"},
        source_ref="connector:github",
        target_ref="repo:Constanteer/testamur",
        unresolved=["resource"],
    )
    assert ok is True
    assert reasons == []
    assert unresolved == []


def test_resource_constraint_cannot_be_satisfied_by_connectivity_to_other_resource() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:Constanteer/other"},
        source_ref="connector:github",
        target_ref="repo:Constanteer/testamur",
        unresolved=["resource"],
    )
    assert ok is False
    assert reasons == ["resource_mismatch"]
    assert unresolved == []


def test_resource_pattern_is_matched_against_exact_target_identity() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource_pattern": "repo:Constanteer/*"},
        source_ref="connector:github",
        target_ref="repo:Constanteer/testamur",
        unresolved=["resource_pattern"],
    )
    assert ok is True
    assert reasons == []
    assert unresolved == []


def test_principal_constraint_matches_exact_source_identity() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"principal": "user:alice"},
        source_ref="user:alice",
        target_ref="service:api",
        unresolved=["principal"],
    )
    assert ok is True
    assert reasons == []
    assert unresolved == []


def test_generic_name_or_id_is_not_authorization_evidence() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"resource": "repo:Constanteer/testamur"},
        source_ref="connector:github",
        target_ref="resource:opaque-17",
        target_subject={"name": "repo:Constanteer/testamur", "attributes": {"id": "repo:Constanteer/testamur"}},
        unresolved=["resource"],
    )
    assert ok is False
    assert reasons == ["resource_mismatch"]
    assert unresolved == []


def test_runtime_context_remains_fail_closed_without_evidence() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"network_zone": "corp", "device_binding": "managed"},
        source_ref="user:alice",
        target_ref="service:api",
        unresolved=["network_zone", "device_binding"],
    )
    assert ok is False
    assert reasons == []
    assert unresolved == ["device_binding", "network_zone"]
