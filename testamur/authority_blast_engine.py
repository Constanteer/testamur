from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Sequence

from .authority import TestamurAuthorityStore
from .authority_blast_provenance import build_blast_radius_result


def canonical_authority_blast_radius(
    store: TestamurAuthorityStore,
    compromised_refs: str | Sequence[str],
    *,
    compromise_model: str,
    capability_filter: Iterable[tuple[str, str]] | None = None,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | datetime | None = None,
) -> dict[str, Any]:
    """Run one exact authority-reachability traversal per explicit compromise seed.

    This orchestration deliberately does not combine graphs before traversal. Each
    seed is evaluated independently by the authority engine and only the recorded
    per-seed results are aggregated afterwards. Material lineage, reliance,
    affectedness, common targets, and graph connectivity therefore cannot create
    compromise-seed provenance or authority that the engine did not record.
    """
    # Local import avoids making the reachability module depend on this orchestration
    # while it still exposes the legacy authority_blast_radius entry point.
    from .authority_reachability_v2 import _normalize_model, authority_reachability

    refs = [compromised_refs] if isinstance(compromised_refs, str) else list(compromised_refs)
    seeds = sorted({str(ref).strip() for ref in refs if str(ref).strip()})
    if not seeds:
        raise ValueError("compromised_refs must contain at least one subject ref")

    model = _normalize_model(compromise_model)
    results = [
        authority_reachability(
            store,
            seed_ref,
            compromise_model=model,
            capability_filter=capability_filter,
            max_depth=max_depth,
            max_paths=max_paths,
            expansion_budget=expansion_budget,
            as_of=as_of,
        )
        for seed_ref in seeds
    ]
    return build_blast_radius_result(
        results,
        compromised_refs=seeds,
        compromise_model=model,
    )


__all__ = ["canonical_authority_blast_radius"]
