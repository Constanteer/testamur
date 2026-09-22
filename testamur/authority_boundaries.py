from __future__ import annotations

from typing import Any, Iterable, Mapping

from .authority import TestamurAuthorityStore


def trust_boundary_crossing_identity(crossing: Mapping[str, Any]) -> tuple[str, str, tuple[str, ...], int]:
    """Return the exact authority-path identity of a recorded boundary crossing.

    An edge/boundary pair is deliberately insufficient identity: the same edge can
    be reached through distinct authority paths carrying different evidence and
    compromise provenance. Missing path evidence stays missing (the empty tuple);
    callers must not reconstruct it from graph connectivity or material lineage.
    """
    edge_id = str(crossing.get("edge_id") or "").strip()
    boundary_ref = str(crossing.get("boundary_ref") or "").strip()
    path_edge_ids = tuple(
        str(edge).strip()
        for edge in crossing.get("path_edge_ids") or []
        if str(edge).strip()
    )
    path_position = int(crossing.get("path_position") or 0)
    return edge_id, boundary_ref, path_edge_ids, path_position


def aggregate_trust_boundary_crossings(
    crossings: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate recorded crossings without weakening exact-path evidence.

    This helper intentionally knows nothing about graph connectivity, material
    lineage, reliance, or affectedness. Two crossings merge only when their
    recorded authority-path identities are exactly equal. It also does not invent
    compromise provenance: if otherwise-identical records carry seed provenance,
    only the explicitly recorded seed refs are unioned.
    """
    aggregated: dict[tuple[str, str, tuple[str, ...], int], dict[str, Any]] = {}
    for raw in crossings:
        item = dict(raw)
        identity = trust_boundary_crossing_identity(item)
        current = aggregated.get(identity)
        if current is None:
            if "compromise_seed_refs" in item:
                seeds = item.get("compromise_seed_refs")
                if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Iterable):
                    raise ValueError("compromise_seed_refs must be a sequence")
                item["compromise_seed_refs"] = sorted(
                    {str(seed).strip() for seed in seeds if str(seed).strip()}
                )
            aggregated[identity] = item
            continue

        if "compromise_seed_refs" in current or "compromise_seed_refs" in item:
            raw_seeds = item.get("compromise_seed_refs") or []
            if isinstance(raw_seeds, (str, bytes)) or not isinstance(raw_seeds, Iterable):
                raise ValueError("compromise_seed_refs must be a sequence")
            current["compromise_seed_refs"] = sorted(
                {
                    *(str(seed).strip() for seed in current.get("compromise_seed_refs") or [] if str(seed).strip()),
                    *(str(seed).strip() for seed in raw_seeds if str(seed).strip()),
                }
            )

    return [aggregated[key] for key in sorted(aggregated)]


def project_trust_boundary_crossings(
    store: TestamurAuthorityStore,
    edge_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Project only trust-boundary crossings explicitly attached to authority edges.

    Boundary membership is not authority and graph connectivity is not a crossing.
    A crossing exists here only when the exact traversed authority edge carries the
    boundary reference. This deliberately does not inspect material lineage,
    reliance, affectedness, endpoint domains, or neighboring edges to infer one.

    Every crossing also records the complete traversed authority path. ``edge_id``
    identifies the exact edge carrying the boundary annotation while
    ``path_edge_ids`` preserves the authority path on which that crossing was
    observed. Consumers must not treat the same edge/boundary pair reached through
    a different authority path as equivalent evidence.
    """
    path_edge_ids = tuple(str(raw).strip() for raw in edge_ids if str(raw).strip())
    crossings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...], int]] = set()
    for position, edge_id in enumerate(path_edge_ids):
        edge = store.get_edge(edge_id)
        for raw_boundary_ref in edge.get("boundary_refs") or []:
            boundary_ref = str(raw_boundary_ref).strip()
            if not boundary_ref:
                continue
            crossing = {
                "edge_id": edge_id,
                "boundary_ref": boundary_ref,
                "path_position": position,
                "path_edge_ids": list(path_edge_ids),
                "source_ref": str(edge.get("source_ref") or ""),
                "target_ref": str(edge.get("target_ref") or ""),
                "relation_type": str(edge.get("relation_type") or ""),
            }
            identity = trust_boundary_crossing_identity(crossing)
            if identity in seen:
                continue
            seen.add(identity)
            crossings.append(crossing)
    return crossings


def boundary_refs_from_crossings(crossings: Iterable[dict[str, Any]]) -> list[str]:
    """Compatibility projection for clients that only need the boundary set."""
    return sorted(
        {
            str(item.get("boundary_ref") or "").strip()
            for item in crossings
            if str(item.get("boundary_ref") or "").strip()
        }
    )


__all__ = [
    "project_trust_boundary_crossings",
    "boundary_refs_from_crossings",
    "trust_boundary_crossing_identity",
    "aggregate_trust_boundary_crossings",
]
