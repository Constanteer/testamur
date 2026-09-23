from __future__ import annotations

import pytest

from testamur.authority_edge_identity import (
    exact_authority_edge_identity,
    exact_optional_constraint_ref,
)


def test_exact_authority_edge_identity_preserves_explicit_identity() -> None:
    edge = {
        "edge_id": "edge:1",
        "source_ref": "subject:a",
        "target_ref": "subject:b",
        "relation_type": "DELEGATES",
    }
    assert exact_authority_edge_identity(edge) == (
        "edge:1", "subject:a", "subject:b", "DELEGATES"
    )


@pytest.mark.parametrize("field", ["edge_id", "source_ref", "target_ref", "relation_type"])
@pytest.mark.parametrize("bad", [123, {"ref": "subject:a"}, None, "   "])
def test_exact_authority_edge_identity_rejects_coercion(field: str, bad: object) -> None:
    edge = {
        "edge_id": "edge:1",
        "source_ref": "subject:a",
        "target_ref": "subject:b",
        "relation_type": "DELEGATES",
    }
    edge[field] = bad
    with pytest.raises(ValueError):
        exact_authority_edge_identity(edge)


def test_optional_binding_ref_distinguishes_absent_from_malformed() -> None:
    assert exact_optional_constraint_ref(None, field="service_ref") is None
    assert exact_optional_constraint_ref("service:github", field="service_ref") == "service:github"
    with pytest.raises(ValueError):
        exact_optional_constraint_ref(42, field="service_ref")


def test_connectivity_shaped_object_cannot_become_binding_ref() -> None:
    with pytest.raises(ValueError):
        exact_optional_constraint_ref(
            {"target_ref": "service:github", "connected": True}, field="service_ref"
        )
