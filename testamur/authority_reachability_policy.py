from __future__ import annotations

from typing import Any, Mapping, Sequence

from .authority import AuthorityRelationType
from .authority_capability import (
    CapabilityBudget,
    capability_allowed,
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


def _constraint_set(constraints: Mapping[str, Any], singular: str, plural: str) -> set[str]:
    result: set[str] = set()
    for key in (singular, plural):
        value = constraints.get(key)
        if isinstance(value, str) and value:
            result.add(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            result.update(str(item) for item in value if str(item))
    return result


def capability_rejection_diagnostics(
    edge: Mapping[str, Any], inherited: CapabilityBudget | None
) -> dict[str, Any] | None:
    """Explain why explicit edge capabilities do not fit inherited authority.

    This is diagnostic only: it calls the same canonical ``capability_allowed``
    predicate used by traversal and never turns a mismatch into authority.  Exact
    candidate and inherited budgets are returned so Product/CLI/Web can explain a
    denial without reconstructing permissions from graph connectivity.
    """
    candidates = [dict(item) for item in edge.get("capabilities") or [] if isinstance(item, Mapping)]
    if not candidates or inherited is None:
        return None
    rejected = [item for item in candidates if not capability_allowed(item, inherited)]
    if not rejected:
        return None

    reasons: set[str] = set()
    unresolved: set[str] = set()
    for candidate in rejected:
        cc = candidate.get("constraints") if isinstance(candidate.get("constraints"), Mapping) else {}
        candidate_selection = cc.get("repository_selection")
        candidate_refs = _constraint_set(cc, "repository_ref", "repository_refs")
        matching_identity = [
            parent for parent in inherited
            if str(parent.get("namespace") or "") == str(candidate.get("namespace") or "")
            and str(parent.get("action") or "") == str(candidate.get("action") or "")
        ]
        if not matching_identity:
            reasons.add("delegated_capability_identity_mismatch")
            continue
        for parent in matching_identity:
            pc = parent.get("constraints") if isinstance(parent.get("constraints"), Mapping) else {}
            parent_selection = pc.get("repository_selection")
            parent_refs = _constraint_set(pc, "repository_ref", "repository_refs")
            if parent_selection == "unresolved" and candidate_selection != "unresolved":
                reasons.add("repository_selection_unresolved")
                unresolved.add("repository_selection")
            elif parent_selection == "selected" and (
                candidate_selection != "selected" or not candidate_refs or not candidate_refs <= parent_refs
            ):
                reasons.add("repository_scope_outside_delegation")
            elif parent_selection == "all" and candidate_selection not in {"all", "selected"}:
                reasons.add("repository_scope_not_established")
            else:
                reasons.add("capability_constraints_outside_delegation")

    return {
        "reasons": sorted(reasons) or ["capability_constraints_outside_delegation"],
        "unresolved_constraints": sorted(unresolved),
        "candidate_capabilities": rejected,
        "inherited_capability_budget": project_budget(inherited),
    }


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
    """Identity for an actionable result without collapsing constrained authority."""
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
    """Identity for a traversal state including the exact inherited authority budget."""
    return (
        str(subject_ref),
        str(reachability_class),
        projected_budget_identity(budget),
        tuple(str(edge_id) for edge_id in path_edge_ids),
    )


__all__ = [
    "implicit_capability",
    "exercisable_capabilities",
    "capability_rejection_diagnostics",
    "downstream_budget",
    "project_downstream_budget",
    "action_result_identity",
    "traversal_state_identity",
]
