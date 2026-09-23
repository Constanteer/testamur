from __future__ import annotations

import pytest

from testamur.authority_identity import (
    exact_action_result_identity,
    exact_traversal_state_identity,
)


CAPABILITY = {
    "namespace": "github",
    "action": "issues.write",
    "resource": "repo:Constanteer/testamur",
    "constraints": {},
}


def test_action_identity_preserves_exact_authority_refs() -> None:
    identity = exact_action_result_identity("connector:github", CAPABILITY, ["edge:grant", "edge:delegate"])
    assert identity[0] == "connector:github"
    assert identity[2] == ("edge:grant", "edge:delegate")


@pytest.mark.parametrize("target", [123, {}, None, ""])
def test_action_identity_does_not_stringify_target(target: object) -> None:
    with pytest.raises(ValueError):
        exact_action_result_identity(target, CAPABILITY, ["edge:grant"])  # type: ignore[arg-type]


@pytest.mark.parametrize("path", [[123], [{}], [None], [""]])
def test_action_identity_does_not_stringify_path_refs(path: list[object]) -> None:
    with pytest.raises(ValueError):
        exact_action_result_identity("connector:github", CAPABILITY, path)  # type: ignore[arg-type]


def test_scalar_path_is_not_treated_as_ref_sequence() -> None:
    with pytest.raises(ValueError):
        exact_action_result_identity("connector:github", CAPABILITY, "edge:grant")  # type: ignore[arg-type]


@pytest.mark.parametrize("subject", [123, {}, None, ""])
def test_traversal_identity_does_not_stringify_subject(subject: object) -> None:
    with pytest.raises(ValueError):
        exact_traversal_state_identity(subject, "delegated", None, ["edge:delegate"])  # type: ignore[arg-type]


@pytest.mark.parametrize("reachability_class", [123, {}, None, ""])
def test_traversal_identity_requires_exact_reachability_class(reachability_class: object) -> None:
    with pytest.raises(ValueError):
        exact_traversal_state_identity("principal:alice", reachability_class, None, ["edge:delegate"])  # type: ignore[arg-type]
