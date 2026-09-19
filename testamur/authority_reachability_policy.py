from __future__ import annotations

from datetime import datetime, timezone
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

_CONSTRAINT_SETS = (
    (("scope", "scopes", "required_scope", "required_scopes"), "scope"),
    (("audience", "audiences", "required_audience", "required_audiences"), "audience"),
    (("principal", "principals"), "principal"),
    (("service_ref", "service_refs"), "service_ref"),
    (("network_zone", "network_zones"), "network_zone"),
    (("source_ip", "source_ips"), "source_ip"),
    (("device_binding", "device_bindings"), "device_binding"),
    (("session_binding", "session_bindings"), "session_binding"),
    (("issuer", "issuers", "required_issuer", "required_issuers"), "issuer"),
    (("tenant", "tenants", "tenant_id", "tenant_ids"), "tenant"),
)
_GATE_KEYS = ("approval_required", "human_confirmation_required", "mfa_required")
_REPOSITORY_KEYS = {"repository_selection", "repository_ref", "repository_refs"}


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


def _constraint_set(constraints: Mapping[str, Any], singular: str, *plural: str) -> set[str]:
    result: set[str] = set()
    for key in (singular, *plural):
        value = constraints.get(key)
        if isinstance(value, str) and value:
            result.add(value)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            result.update(str(item) for item in value if str(item))
    return result


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _failed_constraints(candidate: Mapping[str, Any], parent: Mapping[str, Any]) -> tuple[set[str], set[str], set[str]]:
    """Attribute a rejected attenuation without making an independent auth decision.

    The caller invokes this only after canonical ``capability_allowed`` rejected the
    candidate. These labels explain which parent constraints were not preserved;
    they never turn a candidate into authority.
    """
    reasons: set[str] = set()
    failed: set[str] = set()
    unresolved: set[str] = set()
    cc = candidate.get("constraints") if isinstance(candidate.get("constraints"), Mapping) else {}
    pc = parent.get("constraints") if isinstance(parent.get("constraints"), Mapping) else {}

    parent_resource = parent.get("resource")
    if parent_resource is not None and candidate.get("resource") != parent_resource:
        reasons.add("resource_outside_delegation")
        failed.add("resource")

    candidate_selection = cc.get("repository_selection")
    candidate_refs = _constraint_set(cc, "repository_ref", "repository_refs")
    parent_selection = pc.get("repository_selection")
    parent_refs = _constraint_set(pc, "repository_ref", "repository_refs")
    if parent_selection == "unresolved" and candidate_selection != "unresolved":
        reasons.add("repository_selection_unresolved")
        failed.add("repository_selection")
        unresolved.add("repository_selection")
    elif parent_selection == "selected" and (
        candidate_selection != "selected" or not candidate_refs or not candidate_refs <= parent_refs
    ):
        reasons.add("repository_scope_outside_delegation")
        failed.add("repository_selection")
    elif parent_selection == "all" and candidate_selection not in {"all", "selected"}:
        reasons.add("repository_scope_not_established")
        failed.add("repository_selection")

    for aliases, canonical in _CONSTRAINT_SETS:
        parent_values = _constraint_set(pc, *aliases)
        if not parent_values:
            continue
        child_values = _constraint_set(cc, *aliases)
        if not child_values or not child_values <= parent_values:
            reasons.add(f"{canonical}_outside_delegation")
            failed.add(canonical)

    for key in _GATE_KEYS:
        if pc.get(key) is True and cc.get(key) is not True:
            reasons.add(f"{key}_not_preserved")
            failed.add(key)

    if pc.get("expires_at") is not None:
        parent_expiry = _parse_time(pc.get("expires_at"))
        child_expiry = _parse_time(cc.get("expires_at"))
        if parent_expiry is None or child_expiry is None or child_expiry > parent_expiry:
            reasons.add("expiry_outside_delegation")
            failed.add("expires_at")

    handled = {alias for aliases, _ in _CONSTRAINT_SETS for alias in aliases}
    handled.update(_GATE_KEYS)
    handled.update(_REPOSITORY_KEYS)
    handled.update({"expires_at", "resource_pattern"})
    for key, value in pc.items():
        if key in handled or value in (None, False, "", [], {}, ()):
            continue
        if key not in cc or cc[key] != value:
            reasons.add("provider_constraint_mismatch")
            failed.add(str(key))

    return reasons, failed, unresolved


def capability_rejection_diagnostics(
    edge: Mapping[str, Any], inherited: CapabilityBudget | None
) -> dict[str, Any] | None:
    """Explain why explicit edge capabilities do not fit inherited authority.

    This is diagnostic only: it calls the same canonical ``capability_allowed``
    predicate used by traversal and never turns a mismatch into authority. Exact
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
    failed: set[str] = set()
    unresolved: set[str] = set()
    for candidate in rejected:
        matching_identity = [
            parent for parent in inherited
            if str(parent.get("namespace") or "") == str(candidate.get("namespace") or "")
            and str(parent.get("action") or "") == str(candidate.get("action") or "")
        ]
        if not matching_identity:
            reasons.add("delegated_capability_identity_mismatch")
            failed.update({"namespace", "action"})
            continue
        attributed = False
        for parent in matching_identity:
            parent_reasons, parent_failed, parent_unresolved = _failed_constraints(candidate, parent)
            if parent_reasons:
                attributed = True
                reasons.update(parent_reasons)
                failed.update(parent_failed)
                unresolved.update(parent_unresolved)
        if not attributed:
            reasons.add("capability_constraints_outside_delegation")

    return {
        "reasons": sorted(reasons) or ["capability_constraints_outside_delegation"],
        "failed_constraints": sorted(failed),
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
