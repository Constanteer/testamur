from __future__ import annotations

import pytest

from testamur.authority_reachability_policy import (
    action_result_identity,
    implicit_capability,
    traversal_state_identity,
)


CAPABILITY = {
    "namespace": "github",
    "action": "issues.write",
    "resource": "repo:Constanteer/testamur",
    "constraints": {},
}


def test_policy_implicit_capability_preserves_exact_grant() -> None:
    result = implicit_capability(
        {"relation_type": "CAN_WRITE", "target_ref": "repo:Constanteer/testamur"}
    )
    assert result == {
        "namespace": "testamur",
        "action": "write",
        "resource": "repo:Constanteer/testamur",
        "constraints": {},
    }


@pytest.mark.parametrize(
    "edge",
    [
        {"relation_type": "CAN_WRITE", "target_ref": 123},
        {"relation_type": 123, "target_ref": "repo:Constanteer/testamur"},
        {"relation_type": "CAN_CONNECT", "target_ref": "service:github"},
    ],
)
def test_policy_implicit_capability_does_not_coerce_or_infer_connectivity(edge: dict[str, object]) -> None:
    assert implicit_capability(edge) is None


def test_policy_action_identity_rejects_typed_target() -> None:
    with pytest.raises(ValueError):
        action_result_identity(123, CAPABILITY, ["edge:grant"])  # type: ignore[arg-type]


def test_policy_action_identity_rejects_typed_path_ref() -> None:
    with pytest.raises(ValueError):
        action_result_identity("connector:github", CAPABILITY, [123])  # type: ignore[list-item]


def test_policy_traversal_identity_rejects_typed_subject() -> None:
    with pytest.raises(ValueError):
        traversal_state_identity(123, "delegated", None, ["edge:delegate"])  # type: ignore[arg-type]


def test_policy_traversal_identity_rejects_typed_reachability_class() -> None:
    with pytest.raises(ValueError):
        traversal_state_identity("principal:alice", 123, None, ["edge:delegate"])  # type: ignore[arg-type]
