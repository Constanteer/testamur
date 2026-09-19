from __future__ import annotations

from typing import Any, Mapping, Sequence

from .authority import AuthorityRelationType
from .authority_capability import (
    CapabilityBudget,
    delegation_budget,
    edge_capabilities,
    project_budget,
)
from .authority_projection import capability_identity, projected_budget_identity


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


def action_result_identity(
    target_ref: str,
    capability: Mapping[str, Any],
    path_edge_ids: Sequence[str],
) -> tuple[str, str, tuple[str, ...]]:
    """Identity for an actionable result without collapsing constrained authority.

    Reachability historically keyed actions by namespace/action/resource only. That
    makes differently scoped, audience-bound, tenant-bound, or approval-gated
    capabilities indistinguishable. Keep the exact effective capability in the key.
    """
    return (
        str(target_ref),
        capability_identity(capability),
        tuple(str(edge_id) for edge_id in path_edge_ids),
    )


def traversal_state_identity(
    subject_ref: str,
    reachability_class: str,
    budget: CapabilityBudget | None,
    path_edge_ids: Sequence[str],
) -> tuple[str, str, tuple[str, ...] | None, tuple[str, ...]]:
    """Identity for a traversal state including the exact inherited authority budget.

    ``None`` remains distinct from ``()``: the former means no inherited delegation
    restriction, while the latter is an explicitly empty authority budget. This is
    essential when compromise paths converge on the same subject through different
    connector delegations.
    """
    return (
        str(subject_ref),
        str(reachability_class),
        projected_budget_identity(budget),
        tuple(str(edge_id) for edge_id in path_edge_ids),
    )


__all__ = [
    "implicit_capability",
    "exercisable_capabilities",
    "downstream_budget",
    "project_downstream_budget",
    "action_result_identity",
    "traversal_state_identity",
]
