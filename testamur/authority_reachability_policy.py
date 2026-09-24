from __future__ import annotations

import fnmatch
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .authority_capability import (
    CapabilityBudget,
    capability_allowed,
    delegation_budget,
    edge_capabilities,
    project_budget,
)
from .authority_exact import exact_implicit_capability
from .authority_identity import exact_action_result_identity, exact_traversal_state_identity

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
    """Return an action implied by exact authority-edge evidence only.

    The canonical projector deliberately excludes CAN_CONNECT and rejects malformed
    relation/target identities rather than stringifying them into authority.
    """
    return exact_implicit_capability(edge)


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


def _constraint_set(
    constraints: Mapping[str, Any], singular: str, *plural: str
) -> tuple[set[str], bool]:
    result: set[str] = set()
    malformed = False
    for key in (singular, *plural):
        if key not in constraints:
            continue
        value = constraints.get(key)
        if value is None:
            malformed = True
            continue
        if isinstance(value, str):
            text = value.strip()
            if text:
                result.add(text)
            else:
                malformed = True
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                if isinstance(item, str) and item.strip():
                    result.add(item.strip())
                else:
                    malformed = True
            continue
        malformed = True
    return result, malformed


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _failed_constraints(candidate: Mapping[str, Any], parent: Mapping[str, Any]) -> tuple[set[str], set[str], set[str]]:
    reasons: set[str] = set()
    failed: set[str] = set()
    unresolved: set[str] = set()
    cc = candidate.get("constraints") if isinstance(candidate.get("constraints"), Mapping) else {}
    pc = parent.get("constraints") if isinstance(parent.get("constraints"), Mapping) else {}

    parent_resource = parent.get("resource")
    if parent_resource is not None and candidate.get("resource") != parent_resource:
        reasons.add("resource_outside_delegation")
        failed.add("resource")

    parent_pattern = pc.get("resource_pattern")
    if parent_pattern is not None:
        child_resource = candidate.get("resource")
        child_pattern = cc.get("resource_pattern")
        if not isinstance(parent_pattern, str) or not parent_pattern.strip():
            reasons.add("resource_pattern_evidence_malformed")
            failed.add("resource_pattern")
            unresolved.add("resource_pattern")
        elif child_resource is not None:
            if not isinstance(child_resource, str) or not fnmatch.fnmatchcase(child_resource, parent_pattern):
                reasons.add("resource_pattern_outside_delegation")
                failed.add("resource_pattern")
        elif child_pattern != parent_pattern:
            reasons.add("resource_pattern_not_preserved")
            failed.add("resource_pattern")

    candidate_selection_present = "repository_selection" in cc
    parent_selection_present = "repository_selection" in pc
    candidate_selection = cc.get("repository_selection")
    parent_selection = pc.get("repository_selection")
    candidate_refs, candidate_refs_malformed = _constraint_set(cc, "repository_ref", "repository_refs")
    parent_refs, parent_refs_malformed = _constraint_set(pc, "repository_ref", "repository_refs")
    valid_selections = {"all", "selected", "unresolved"}
    selection_malformed = (
        (candidate_selection_present and (not isinstance(candidate_selection, str) or candidate_selection not in valid_selections))
        or (parent_selection_present and (not isinstance(parent_selection, str) or parent_selection not in valid_selections))
        or (candidate_selection == "selected" and not candidate_refs)
        or (parent_selection == "selected" and not parent_refs)
        or (candidate_selection in {"all", "unresolved"} and bool(candidate_refs))
        or (parent_selection in {"all", "unresolved"} and bool(parent_refs))
    )
    if candidate_refs_malformed or parent_refs_malformed or selection_malformed:
        reasons.add("repository_selection_evidence_malformed")
        failed.add("repository_selection")
        unresolved.add("repository_selection")
    elif parent_selection == "unresolved" and candidate_selection != "unresolved":
        reasons.add("repository_selection_unresolved")
        failed.add("repository_selection")
        unresolved.add("repository_selection")
    elif parent_selection == "selected" and (
        candidate_selection != "selected" or not candidate_refs <= parent_refs
    ):
        reasons.add("repository_scope_outside_delegation")
        failed.add("repository_selection")
    elif parent_selection == "all" and candidate_selection not in {"all", "selected"}:
        reasons.add("repository_scope_not_established")
        failed.add("repository_selection")

    for aliases, canonical in _CONSTRAINT_SETS:
        parent_values, parent_malformed = _constraint_set(pc, *aliases)
        child_values, child_malformed = _constraint_set(cc, *aliases)
        if parent_malformed or child_malformed:
            reasons.add(f"{canonical}_evidence_malformed")
            failed.add(canonical)
            unresolved.add(canonical)
            continue
        if not parent_values:
            continue
        if not child_values or not child_values <= parent_values:
            reasons.add(f"{canonical}_outside_delegation")
            failed.add(canonical)

    for key in _GATE_KEYS:
        parent_present = key in pc
        child_present = key in cc
        parent_gate = pc.get(key)
        child_gate = cc.get(key)
        if (parent_present and not isinstance(parent_gate, bool)) or (child_present and not isinstance(child_gate, bool)):
            reasons.add(f"{key}_evidence_malformed")
            failed.add(key)
            unresolved.add(key)
            continue
        if parent_gate is True and child_gate is not True:
            reasons.add(f"{key}_not_preserved")
            failed.add(key)

    parent_expiry_present = "expires_at" in pc
    child_expiry_present = "expires_at" in cc
    if parent_expiry_present or child_expiry_present:
        parent_expiry = _parse_time(pc.get("expires_at")) if parent_expiry_present else None
        child_expiry = _parse_time(cc.get("expires_at")) if child_expiry_present else None
        if parent_expiry_present and parent_expiry is None:
            reasons.add("expiry_evidence_malformed")
            failed.add("expires_at")
            unresolved.add("expires_at")
        elif child_expiry_present and child_expiry is None:
            reasons.add("expiry_evidence_malformed")
            failed.add("expires_at")
            unresolved.add("expires_at")
        elif parent_expiry is not None and child_expiry is None:
            reasons.add("expiry_not_preserved")
            failed.add("expires_at")
        elif parent_expiry is not None and child_expiry is not None and child_expiry > parent_expiry:
            reasons.add("expiry_outside_delegation")
            failed.add("expires_at")

    handled = {alias for aliases, _ in _CONSTRAINT_SETS for alias in aliases}
    handled.update(_GATE_KEYS)
    handled.update(_REPOSITORY_KEYS)
    handled.update({"expires_at", "resource_pattern"})
    for key, value in pc.items():
        if key in handled:
            continue
        if not isinstance(key, str) or not key.strip():
            reasons.add("provider_constraint_evidence_malformed")
            failed.add("provider_constraint")
            unresolved.add("provider_constraint")
            continue
        if key not in cc or cc[key] != value:
            reasons.add("provider_constraint_mismatch")
            failed.add(key)

    return reasons, failed, unresolved


def capability_rejection_diagnostics(
    edge: Mapping[str, Any], inherited: CapabilityBudget | None
) -> dict[str, Any] | None:
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
        candidate_namespace = candidate.get("namespace")
        candidate_action = candidate.get("action")
        identity_is_exact = (
            isinstance(candidate_namespace, str)
            and bool(candidate_namespace.strip())
            and isinstance(candidate_action, str)
            and bool(candidate_action.strip())
        )
        matching_identity = []
        if identity_is_exact:
            matching_identity = [
                parent for parent in inherited
                if parent.get("namespace") == candidate_namespace
                and parent.get("action") == candidate_action
            ]
        if not matching_identity:
            reasons.add("delegated_capability_identity_mismatch")
            failed.update({"namespace", "action"})
            if not identity_is_exact:
                unresolved.update({"namespace", "action"})
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


def downstream_budget(edge: Mapping[str, Any], inherited: CapabilityBudget | None) -> CapabilityBudget | None:
    return delegation_budget(edge, inherited)


def project_downstream_budget(budget: CapabilityBudget | None) -> list[dict[str, Any]] | None:
    return project_budget(budget)


def action_result_identity(
    target_ref: str,
    capability: Mapping[str, Any],
    path_edge_ids: Sequence[str],
) -> tuple[str, str, tuple[str, ...]]:
    """Canonical actionable-result identity; malformed refs fail closed."""
    return exact_action_result_identity(target_ref, capability, path_edge_ids)


def traversal_state_identity(
    subject_ref: str,
    reachability_class: str,
    budget: CapabilityBudget | None,
    path_edge_ids: Sequence[str],
) -> tuple[str, str, tuple[str, ...] | None, tuple[str, ...]]:
    """Canonical traversal identity; malformed refs fail closed."""
    return exact_traversal_state_identity(subject_ref, reachability_class, budget, path_edge_ids)


__all__ = [
    "implicit_capability",
    "exercisable_capabilities",
    "capability_rejection_diagnostics",
    "downstream_budget",
    "project_downstream_budget",
    "action_result_identity",
    "traversal_state_identity",
]
