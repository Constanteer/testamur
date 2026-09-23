"""Canonical authority compromise reachability.

The implementation lives in ``authority_reachability_v2`` so the legacy tuple-budget
engine cannot silently reintroduce connectivity-as-permission or drop capability
constraints. This module remains the stable public import surface and enriches
blocked results with denial diagnostics derived from the exact traversed path.
"""

from __future__ import annotations

from typing import Any, Mapping

from .authority import AuthorityRelationType, TestamurAuthorityStore
from .authority_boundaries import boundary_refs_from_crossings, project_trust_boundary_crossings
from .authority_filter import normalize_capability_filter
from .authority_reachability_policy import capability_rejection_diagnostics, downstream_budget
from .authority_reachability_v2 import (
    AuthorityReachabilityClass,
    CompromiseModel,
    authority_blast_radius as _authority_blast_radius,
    authority_reachability as _authority_reachability,
)


_CAPABILITY_REASON_MARKERS = ("capability", "delegation", "scope", "audience", "resource")
_CREDENTIAL_REASON_MARKERS = ("credential", "token", "expired", "revoked", "issuer", "binding", "session", "device")
_CONTROL_REASON_MARKERS = ("approval", "mfa", "human_confirmation", "confirmation")
_BOUNDARY_REASON_MARKERS = ("boundary", "trust_zone", "network_zone", "source_ip")


def _reason_groups(reasons: list[str]) -> dict[str, list[str]]:
    """Classify canonical denial reasons without changing authority semantics."""
    groups: dict[str, list[str]] = {
        "credential_or_token": [], "capability_or_delegation": [],
        "approval_or_mfa": [], "trust_boundary_policy": [], "other": [],
    }
    for reason in reasons:
        lowered = reason.lower()
        if any(marker in lowered for marker in _CREDENTIAL_REASON_MARKERS): bucket = "credential_or_token"
        elif any(marker in lowered for marker in _CAPABILITY_REASON_MARKERS): bucket = "capability_or_delegation"
        elif any(marker in lowered for marker in _CONTROL_REASON_MARKERS): bucket = "approval_or_mfa"
        elif any(marker in lowered for marker in _BOUNDARY_REASON_MARKERS): bucket = "trust_boundary_policy"
        else: bucket = "other"
        groups[bucket].append(reason)
    return groups


def _budget_before_final_edge(store: TestamurAuthorityStore, path_edge_ids: list[str]):
    """Replay only canonical budget propagation for diagnostic attribution."""
    budget = None
    for edge_id in path_edge_ids[:-1]:
        edge = store.get_edge(edge_id)
        relation = str(edge.get("relation_type") or "")
        if relation == AuthorityRelationType.DELEGATES.value:
            budget = downstream_budget(edge, budget)
        elif relation in {AuthorityRelationType.CAN_AUTHENTICATE_AS.value, AuthorityRelationType.CAN_IMPERSONATE.value}:
            budget = downstream_budget(edge, None)
    return budget


def _blocked_boundary_evidence(store: TestamurAuthorityStore, path_edge_ids: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    """Project boundary evidence from the exact rejected authority path only."""
    if not path_edge_ids:
        return [], []
    crossings = project_trust_boundary_crossings(store, path_edge_ids)
    return boundary_refs_from_crossings(crossings), crossings


def _enrich_blocked(store: TestamurAuthorityStore, result: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(result)
    blocked: list[dict[str, Any]] = []
    for raw in result.get("blocked_transitions") or []:
        item = dict(raw)
        path = [str(value) for value in item.get("path_edge_ids") or [] if str(value)]
        # Prefer engine-recorded exact evidence once v2 emits it. Until then the
        # compatibility fallback replays only the already-recorded attempted path.
        if "boundary_refs" in item and "trust_boundary_crossings" in item:
            boundary_refs = list(item.get("boundary_refs") or [])
            crossings = list(item.get("trust_boundary_crossings") or [])
        else:
            boundary_refs, crossings = _blocked_boundary_evidence(store, path)
        item["boundary_refs"] = boundary_refs
        item["trust_boundary_crossings"] = crossings
        reasons = [str(value) for value in item.get("reasons") or [] if str(value)]
        if "missing_explicit_or_authorized_capability" in reasons and path:
            edge = store.get_edge(path[-1])
            diagnostic = capability_rejection_diagnostics(edge, _budget_before_final_edge(store, path))
            if diagnostic is not None:
                diagnostic_reasons = [str(value) for value in diagnostic.get("reasons") or [] if str(value)]
                item["reasons"] = list(dict.fromkeys(reason for reason in reasons if reason != "missing_explicit_or_authorized_capability"))
                item["reasons"].extend(reason for reason in diagnostic_reasons if reason not in item["reasons"])
                item["failed_constraints"] = diagnostic["failed_constraints"]
                item["unresolved_constraints"] = diagnostic["unresolved_constraints"]
                item["candidate_capabilities"] = diagnostic["candidate_capabilities"]
                item["inherited_capability_budget"] = diagnostic["inherited_capability_budget"]
        final_reasons = [str(value) for value in item.get("reasons") or [] if str(value)]
        item["reason_groups"] = _reason_groups(final_reasons)
        blocked.append(item)
    enriched["blocked_transitions"] = blocked
    semantics = dict(enriched.get("semantics") or {})
    semantics["blocked_boundary_evidence_uses_exact_recorded_path_only"] = True
    semantics["blocked_transition_does_not_grant_authority"] = True
    semantics["capability_filter_is_selector_not_authority_evidence"] = True
    enriched["semantics"] = semantics
    return enriched


def _canonical_kwargs(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    canonical = dict(kwargs)
    if "capability_filter" in canonical:
        canonical["capability_filter"] = normalize_capability_filter(canonical["capability_filter"])
    return canonical


def authority_reachability(store: TestamurAuthorityStore, *args, **kwargs):
    return _enrich_blocked(store, _authority_reachability(store, *args, **_canonical_kwargs(kwargs)))


def authority_blast_radius(store: TestamurAuthorityStore, *args, **kwargs):
    return _enrich_blocked(store, _authority_blast_radius(store, *args, **_canonical_kwargs(kwargs)))


__all__ = ["CompromiseModel", "AuthorityReachabilityClass", "authority_reachability", "authority_blast_radius"]
