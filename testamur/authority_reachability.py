"""Canonical authority compromise reachability.

The implementation lives in ``authority_reachability_v2`` so the legacy tuple-budget
engine cannot silently reintroduce connectivity-as-permission or drop capability
constraints. This module remains the stable public import surface and enriches
blocked results with denial diagnostics derived from the exact traversed path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .authority import AuthorityRelationType, TestamurAuthorityStore
from .authority_edge_identity import exact_nonempty_string
from .authority_exact_store import ExactAuthorityStoreView
from .authority_filter import normalize_capability_filter
from .authority_reachability_policy import capability_rejection_diagnostics, downstream_budget
from .authority_reachability_v2 import (
    AuthorityReachabilityClass,
    CompromiseModel,
    authority_blast_radius as _authority_blast_radius,
    authority_reachability as _authority_reachability,
)
from .authority_seed import exact_subject_ref, normalize_compromise_seeds


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


def _exact_string_list(value: Any, *, field: str) -> list[str]:
    """Preserve engine evidence without coercing arbitrary values into identities."""
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{field} must be a sequence of exact strings")
    result: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError(f"{field} entries must be non-empty exact strings")
        result.append(entry)
    return result


def _budget_before_final_edge(store: TestamurAuthorityStore, path_edge_ids: list[str]):
    """Replay canonical attenuation without allowing identity hops to reset delegation."""
    budget = None
    for edge_id in path_edge_ids[:-1]:
        edge = store.get_edge(edge_id)
        relation = exact_nonempty_string(edge.get("relation_type"), field="relation_type")
        if relation in {
            AuthorityRelationType.DELEGATES.value,
            AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
            AuthorityRelationType.CAN_IMPERSONATE.value,
        }:
            budget = downstream_budget(edge, budget)
    return budget


def _enrich_blocked(store: TestamurAuthorityStore, result: Mapping[str, Any]) -> dict[str, Any]:
    enriched = dict(result)
    blocked: list[dict[str, Any]] = []
    for raw in result.get("blocked_transitions") or []:
        item = dict(raw)
        path = _exact_string_list(item.get("path_edge_ids"), field="blocked.path_edge_ids")
        if "boundary_refs" not in item or "trust_boundary_crossings" not in item:
            raise ValueError("raw blocked transition is missing exact trust-boundary evidence")
        boundary_refs = _exact_string_list(item.get("boundary_refs"), field="blocked.boundary_refs")
        raw_crossings = item.get("trust_boundary_crossings")
        if not isinstance(raw_crossings, list):
            raise ValueError("blocked.trust_boundary_crossings must be an exact record list")
        crossings: list[dict[str, Any]] = []
        for crossing in raw_crossings:
            if not isinstance(crossing, Mapping):
                raise ValueError("blocked trust-boundary crossing must be a mapping")
            crossing_item = dict(crossing)
            crossing_path = _exact_string_list(crossing_item.get("path_edge_ids"), field="blocked.crossing.path_edge_ids")
            if crossing_path != path:
                raise ValueError("blocked trust-boundary crossing must preserve the exact attempted path")
            edge_id = crossing_item.get("edge_id")
            boundary_ref = crossing_item.get("boundary_ref")
            if not isinstance(edge_id, str) or not edge_id.strip() or edge_id not in path:
                raise ValueError("blocked trust-boundary crossing edge_id must be on the exact attempted path")
            if not isinstance(boundary_ref, str) or not boundary_ref.strip():
                raise ValueError("blocked trust-boundary crossing boundary_ref must be an exact string")
            crossings.append(crossing_item)
        proven_boundaries = sorted({crossing["boundary_ref"] for crossing in crossings})
        if sorted(set(boundary_refs)) != proven_boundaries:
            raise ValueError("blocked boundary_refs must equal boundaries proven by exact crossings")
        item["boundary_refs"] = boundary_refs
        item["trust_boundary_crossings"] = crossings

        reasons = _exact_string_list(item.get("reasons"), field="blocked.reasons")
        if "missing_explicit_or_authorized_capability" in reasons and path:
            edge = store.get_edge(path[-1])
            diagnostic = capability_rejection_diagnostics(edge, _budget_before_final_edge(store, path))
            if diagnostic is not None:
                diagnostic_reasons = _exact_string_list(diagnostic.get("reasons"), field="diagnostic.reasons")
                item["reasons"] = list(dict.fromkeys(reason for reason in reasons if reason != "missing_explicit_or_authorized_capability"))
                item["reasons"].extend(reason for reason in diagnostic_reasons if reason not in item["reasons"])
                item["failed_constraints"] = diagnostic["failed_constraints"]
                item["unresolved_constraints"] = diagnostic["unresolved_constraints"]
                item["candidate_capabilities"] = diagnostic["candidate_capabilities"]
                item["inherited_capability_budget"] = diagnostic["inherited_capability_budget"]
        final_reasons = _exact_string_list(item.get("reasons"), field="blocked.reasons")
        item["reason_groups"] = _reason_groups(final_reasons)
        blocked.append(item)
    enriched["blocked_transitions"] = blocked
    semantics = dict(enriched.get("semantics") or {})
    semantics["blocked_boundary_evidence_is_engine_recorded_exact_path"] = True
    semantics["blocked_boundary_evidence_uses_exact_recorded_path_only"] = True
    semantics["blocked_transition_does_not_grant_authority"] = True
    semantics["capability_filter_is_selector_not_authority_evidence"] = True
    semantics["compromise_seeds_are_explicit_authority_assumptions"] = True
    semantics["traversed_authority_edges_require_exact_identity_evidence"] = True
    semantics["service_binding_is_exact_authority_evidence"] = True
    semantics["as_of_requires_explicit_timezone_when_supplied"] = True
    semantics["compromise_model_requires_exact_identity"] = True
    semantics["diagnostic_replay_preserves_delegated_capability_budget"] = True
    enriched["semantics"] = semantics
    return enriched


def _canonical_as_of(value: Any) -> datetime | None:
    """Normalize explicit temporal evidence without guessing a timezone or coercing types."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of datetime must include an explicit timezone")
        return value.astimezone(timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("as_of must be an exact timezone-aware ISO timestamp string or datetime")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("as_of must be a valid timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as_of timestamp must include an explicit timezone")
    return parsed.astimezone(timezone.utc)


def _canonical_compromise_model(value: Any) -> str:
    """Accept only an exact declared compromise model; arbitrary objects are not identities."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("compromise_model must be an exact non-empty string")
    try:
        return CompromiseModel(value.strip()).value
    except ValueError as exc:
        raise ValueError(f"unsupported compromise model {value!r}") from exc


def _canonical_kwargs(kwargs: Mapping[str, Any]) -> dict[str, Any]:
    canonical = dict(kwargs)
    if "capability_filter" in canonical:
        canonical["capability_filter"] = normalize_capability_filter(canonical["capability_filter"])
    if "as_of" in canonical:
        canonical["as_of"] = _canonical_as_of(canonical["as_of"])
    if "compromise_model" in canonical:
        canonical["compromise_model"] = _canonical_compromise_model(canonical["compromise_model"])
    return canonical


def authority_reachability(store: TestamurAuthorityStore, starting_subject_ref: str, *args, **kwargs):
    start = exact_subject_ref(starting_subject_ref, field="starting_subject_ref")
    exact_store = ExactAuthorityStoreView(store)
    return _enrich_blocked(exact_store, _authority_reachability(exact_store, start, *args, **_canonical_kwargs(kwargs)))


def authority_blast_radius(store: TestamurAuthorityStore, compromised_refs, *args, **kwargs):
    seeds = normalize_compromise_seeds(compromised_refs)
    exact_store = ExactAuthorityStoreView(store)
    return _enrich_blocked(exact_store, _authority_blast_radius(exact_store, seeds, *args, **_canonical_kwargs(kwargs)))


__all__ = ["CompromiseModel", "AuthorityReachabilityClass", "authority_reachability", "authority_blast_radius"]