from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from .authority import TestamurAuthorityStore
from .authority_boundaries import aggregate_trust_boundary_crossings, boundary_refs_from_crossings
from .authority_reachability_v2 import CompromiseModel, authority_reachability as _legacy_authority_reachability


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
    """Run reachability and canonicalize only explicitly recorded boundary evidence.

    The traversal engine records crossings on each reachable/action path.  This
    wrapper derives the envelope projection exclusively from those recorded
    crossings and the shared exact-path aggregator.  It does not inspect graph
    connectivity, material lineage, reliance, or affectedness, and therefore
    cannot manufacture authority or a boundary crossing from adjacency alone.
    """
    result = _legacy_authority_reachability(
        store,
        starting_subject_ref,
        compromise_model=compromise_model,
        capability_filter=capability_filter,
        max_depth=max_depth,
        max_paths=max_paths,
        expansion_budget=expansion_budget,
        as_of=as_of,
    )

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
        "trust_boundary_crossings_preserve_exact_path_identity": True,
        "trust_boundary_crossings_use_canonical_aggregation": True,
        "trust_boundary_crossings_are_recorded_not_connectivity_inferred": True,
    }
    return result


__all__ = ["canonical_authority_reachability"]
