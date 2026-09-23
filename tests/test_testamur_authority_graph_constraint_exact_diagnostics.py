from __future__ import annotations

import pytest

from testamur.authority_graph_constraints import (
    graph_context_constraints_satisfied,
    resolve_graph_context_verdict,
)


def test_graph_context_rejects_typed_unresolved_constraint_identity() -> None:
    with pytest.raises(ValueError, match=r"unresolved\[0\].*exact non-empty string"):
        graph_context_constraints_satisfied(
            {"service_ref": "service:github"},
            source_ref="credential:token",
            target_ref="service:github",
            unresolved=[{"name": "service_ref", "connected": True}],
        )


def test_graph_context_rejects_numeric_unresolved_constraint_identity() -> None:
    with pytest.raises(ValueError, match=r"unresolved\[0\].*exact non-empty string"):
        graph_context_constraints_satisfied(
            {},
            source_ref="principal:alice",
            target_ref="resource:repo",
            unresolved=[123],
        )


def test_graph_context_preserves_exact_unresolved_constraint_identity() -> None:
    ok, reasons, unresolved = graph_context_constraints_satisfied(
        {"service_ref": "service:github"},
        source_ref="credential:token",
        target_ref="service:github",
        target_subject={"service_ref": "service:github"},
        unresolved=["service_ref"],
    )

    assert ok is True
    assert reasons == []
    assert unresolved == []


def test_resolve_verdict_rejects_typed_credential_reason() -> None:
    with pytest.raises(ValueError, match=r"credential_reasons\[0\].*exact non-empty string"):
        resolve_graph_context_verdict(
            {},
            (False, [{"reason": "scope_mismatch"}], []),
            source_ref="credential:token",
            target_ref="service:github",
        )


def test_connectivity_object_cannot_become_constraint_name() -> None:
    with pytest.raises(ValueError):
        graph_context_constraints_satisfied(
            {},
            source_ref="credential:token",
            target_ref="service:github",
            unresolved=[{"target_ref": "service:github", "connected": True}],
        )
