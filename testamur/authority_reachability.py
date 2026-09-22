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
from .authority_reachability_policy import capability_rejection_diagnostics, downstream_budget
from .authority_reachability_v2 import (
    AuthorityReachabilityClass,
    CompromiseModel,
    authority_blast_radius as _authority_blast_radius,
    authority_reachability as _authority_reachability,
)


_CAPABILITY_REASON_MARKERS = (
    "capability",
    "delegation",
    "scope",
    "audience",
    "resource",
)
_CREDENTIAL_REASON_MARKERS = (
    "credential",
    "token",
    "expired",
    "revoked",
    "issuer",
    "binding",
    "session",
    "device",
)
_CONTROL_REASON_MARKERS = (
    "approval",
    "mfa",
    "human_confirmation",
    "confirmation",
)
_BOUNDARY_REASON_MARKERS = ("boundary", "trust_zone", "network_zone", "source_ip")


def _reason_groups(reasons: list[str]) -> dict[str, list[str]]:
    """Classify canonical denial reasons for projections without changing semantics.

    Grouping is deliberately descriptive: a reason remains the exact engine reason,
    may appear in only one presentation bucket, and never becomes evidence that an
    authority transition is valid. Unknown reasons remain visible under ``other``.
    """
    groups: dict[str, list[str]] = {
        "credential_or_token": [],
        "capability_or_delegation": [],
        "approval_or_mfa": [],
        "trust_boundary_policy": [],
        "other": [],
    }
    for reason in reasons:
        lowered = reason.lower()
        if any(marker in lowered for marker in _CREDENTIAL_REASON_MARKERS):
            bucket = "credential_or_token"
        elif any(marker in lowered for marker in _CAPABILITY_REASON_MARKERS):
            bucket = "capability_or_delegation"
        elif any(marker in lowered for marker in _CONTROL_REASON_MARKERS):
            bucket = "approval_or_mfa"
        elif any(marker in lowered for marker in _BOUNDARY_REASON_MARKERS):
            bucket = "trust_boundary_policy"
        else:
            bucket = "other"
        groups[bucket].append(reason)
    return groups


def _budget_before_final_edge(store: TestamurAuthorityStore, path_edge_ids: list[str]):
    """Replay only canonical budget propagation for diagnostic attribution.

    This does not decide reachability. The v2 engine already made that decision;
    replay is restricted to the exact recorded path so diagnostics can expose the
    inherited delegation that rejected a candidate capability.
    """
    budget = None
    for edge_id in path_edge_ids[:-1]:
        edge = store.get_edge(edge_id)
        relation = str(edge.get("relation_type") or "")
        if relation == AuthorityRelationType.DELEGATES.value:
            budget = downstream_budget(edge, budget)
        elif relation in {
            AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
            AuthorityRelationType.CAN_IMPERSONATE.value,
        }:
            budget = downstream_budget(edge, None)
    return budget


def _blocked_boundary_evidence(
    store: TestamurAuthorityStore, path_edge_ids: list[str]
) -> tuple[list[str], list[dict[str, Any]]]:
    """Project boundary evidence from the exact rejected authority path only.

    This is explanatory evidence for an attempted transition, not a permission
    inference. In particular, no graph search, material-lineage walk, reliance edge,
    or affectedness relation is consulted to invent an alternate authority path.
    """
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
        boundary_refs, crossings = _blocked_boundary_evidence(store, path)
        item["boundary_refs"] = boundary_refs
        item["trust_boundary_crossings"] = crossings
        reasons = [str(value) for value in item.get("reasons") or [] if str(value)]
        # A transition may carry more than one canonical blocking reason. Capability
        # diagnostics must not disappear merely because the engine also recorded an
        # independent gate/validity reason. Diagnostics explain the exact recorded
        # candidate edge; they never turn that edge into authority.
        if "missing_explicit_or_authorized_capability" in reasons:
            if path:
                edge = store.get_edge(path[-1])
                diagnostic = capability_rejection_diagnostics(
                    edge, _budget_before_final_edge(store, path)
                )
                if diagnostic is not None:
                    diagnostic_reasons = [
                        str(value) for value in diagnostic.get("reasons") or [] if str(value)
                    ]
                    item["reasons"] = list(
                        dict.fromkeys(
                            reason
                            for reason in reasons
                            if reason != "missing_explicit_or_authorized_capability"
                        )
                    )
                    item["reasons"].extend(
                        reason
                        for reason in diagnostic_reasons
                        if reason not in item["reasons"]
                    )
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
    enriched["semantics"] = semantics
    return enriched


def authority_reachability(store: TestamurAuthorityStore, *args, **kwargs):
    return _enrich_blocked(store, _authority_reachability(store, *args, **kwargs))


def authority_blast_radius(store: TestamurAuthorityStore, *args, **kwargs):
    return _enrich_blocked(store, _authority_blast_radius(store, *args, **kwargs))


__all__ = [
    "CompromiseModel",
    "AuthorityReachabilityClass",
    "authority_reachability",
    "authority_blast_radius",
]
