from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from .authority import TestamurAuthorityStore
from .authority_boundaries import aggregate_trust_boundary_crossings, boundary_refs_from_crossings
from .authority_reachability_v2 import CompromiseModel
from . import authority_reachability_v2 as reachability_v2


_REACHABILITY_SCHEMA_VERSION = "testamur.authority-reachability.v1"


def _normalize_observation_instant(value: str | datetime) -> str:
    """Normalize an explicit observation instant for provenance comparison.

    Observation instants are provenance, not convenience input: a timestamp
    without an explicit UTC offset is ambiguous and therefore rejected rather
    than silently interpreted as UTC. This helper is deliberately temporal
    only. It never derives credential validity, authority, or permission from
    graph connectivity.
    """
    if isinstance(value, datetime):
        parsed = value
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("as_of must include an explicit timezone offset")
    else:
        text = str(value or "").strip()
        if not text:
            raise ValueError("as_of must be an ISO timestamp or datetime")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("as_of must include an explicit timezone offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_authority_reachability(
    store: TestamurAuthorityStore,
    starting_subject_ref: str,
    *,
    compromise_model: str | CompromiseModel,
    capability_filter: Iterable[tuple[str, str]] | None = None,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | datetime | None = None,
) -> dict[str, Any]:
    """Run reachability and canonicalize only explicitly recorded authority evidence.

    The traversal engine records crossings on each reachable/action path. This
    wrapper derives the envelope projection exclusively from those recorded
    crossings and the shared exact-path aggregator. It also binds the returned
    envelope to the requested seed/model/schema/observation instant before
    exposing it as canonical. It does not inspect graph connectivity, material
    lineage, reliance, or affectedness, and therefore cannot manufacture
    authority or a boundary crossing from adjacency alone.
    """
    requested_seed = str(starting_subject_ref or "").strip()
    result = reachability_v2.authority_reachability(
        store,
        starting_subject_ref,
        compromise_model=compromise_model,
        capability_filter=capability_filter,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )

    if str(result.get("schema_version") or "").strip() != _REACHABILITY_SCHEMA_VERSION:
        raise ValueError("authority reachability returned an unsupported schema version")
    if str(result.get("starting_subject_ref") or "").strip() != requested_seed:
        raise ValueError("authority reachability result does not match requested starting subject")
    expected_model = CompromiseModel(str(compromise_model)).value
    if str(result.get("compromise_model") or "").strip() != expected_model:
        raise ValueError("authority reachability result does not match requested compromise model")

    returned_as_of = str(result.get("as_of") or "").strip()
    if not returned_as_of:
        raise ValueError("authority reachability result must record its observation instant")
    normalized_returned_as_of = _normalize_observation_instant(returned_as_of)
    if as_of is not None:
        expected_as_of = _normalize_observation_instant(as_of)
        if normalized_returned_as_of != expected_as_of:
            raise ValueError("authority reachability result does not match requested observation instant")
    result["as_of"] = normalized_returned_as_of

    recorded_crossings: list[dict[str, Any]] = []
    for collection_name in ("reachable_subjects", "actionable_capabilities"):
        for record in result.get(collection_name) or []:
            for crossing in record.get("trust_boundary_crossings") or []:
                recorded_crossings.append(dict(crossing))

    crossings = aggregate_trust_boundary_crossings(recorded_crossings)
    result["trust_boundary_crossings"] = crossings
    result["trust_boundary_refs"] = boundary_refs_from_crossings(crossings)
    result["semantics"] = {
        **dict(result.get("semantics") or {}),
        "reachability_result_is_bound_to_requested_seed": True,
        "reachability_result_is_bound_to_requested_compromise_model": True,
        "reachability_result_requires_canonical_schema": True,
        "reachability_result_records_observation_instant": True,
        "explicit_observation_instant_is_exactly_bound": True,
        "observation_instant_requires_explicit_timezone": True,
        "trust_boundary_crossings_preserve_exact_path_identity": True,
        "trust_boundary_crossings_use_canonical_aggregation": True,
        "trust_boundary_crossings_are_recorded_not_connectivity_inferred": True,
    }
    return result


__all__ = ["canonical_authority_reachability"]
