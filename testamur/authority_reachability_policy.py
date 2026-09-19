from __future__ import annotations

from typing import Any, Mapping

from .authority import AuthorityRelationType
from .authority_capability import (
    CapabilityBudget,
    delegation_budget,
    edge_capabilities,
    project_budget,
)


_IMPLICIT_ACTIONS = {
    AuthorityRelationType.CAN_READ.value: "read",
    AuthorityRelationType.CAN_WRITE.value: "write",
    AuthorityRelationType.CAN_EXECUTE.value: "execute",
}


def implicit_capability(edge: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return an action implied by an authority relation itself.

    CAN_CONNECT is deliberately absent: network/service connectivity is not
    authorization and must never manufacture a capability during traversal.
    """
    action = _IMPLICIT_ACTIONS.get(str(edge.get("relation_type") or ""))
    target_ref = str(edge.get("target_ref") or "").strip()
    if action is None or not target_ref:
        return None
    return {
        "namespace": "testamur",
        "action": action,
        "resource": target_ref,
        "constraints": {},
    }


def exercisable_capabilities(
    edge: Mapping[str, Any],
    inherited: CapabilityBudget | None,
) -> list[dict[str, Any]]:
    """Capabilities exercisable on this exact edge under inherited authority."""
    return edge_capabilities(
        edge,
        budget=inherited,
        implicit_capability=implicit_capability(edge),
    )


def downstream_budget(
    edge: Mapping[str, Any],
    inherited: CapabilityBudget | None,
) -> CapabilityBudget | None:
    """Compute the exact capability budget propagated by this edge."""
    return delegation_budget(edge, inherited)


def project_downstream_budget(
    budget: CapabilityBudget | None,
) -> list[dict[str, Any]] | None:
    """Product/CLI projection that preserves every authority constraint."""
    return project_budget(budget)


__all__ = [
    "implicit_capability",
    "exercisable_capabilities",
    "downstream_budget",
    "project_downstream_budget",
]
