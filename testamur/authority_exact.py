from __future__ import annotations

from typing import Any, Mapping

from .authority import AuthorityRelationType


_IMPLICIT_ACTIONS = {
    AuthorityRelationType.CAN_READ.value: "read",
    AuthorityRelationType.CAN_WRITE.value: "write",
    AuthorityRelationType.CAN_EXECUTE.value: "execute",
}


def exact_implicit_capability(edge: Mapping[str, Any]) -> dict[str, Any] | None:
    """Project an implicit action only from exact authority-edge evidence.

    Relation and target identity are evidence. They are never stringified: a typed,
    numeric, empty, or otherwise malformed value must not become an authority grant.
    Connectivity is not consulted here and CAN_CONNECT deliberately has no implicit
    capability.
    """
    relation_type = edge.get("relation_type")
    target_ref = edge.get("target_ref")
    if not (isinstance(relation_type, str) and relation_type.strip()):
        return None
    if not (isinstance(target_ref, str) and target_ref.strip()):
        return None
    action = _IMPLICIT_ACTIONS.get(relation_type)
    if action is None:
        return None
    return {
        "namespace": "testamur",
        "action": action,
        "resource": target_ref.strip(),
        "constraints": {},
    }


__all__ = ["exact_implicit_capability"]
