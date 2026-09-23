from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .authority import TestamurAuthorityStore
from .authority_edge_identity import exact_authority_edge_identity, exact_nonempty_string
from .authority_seed import exact_subject_ref


def _exact_ref_sequence(value: Any, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a sequence of exact refs")
    return tuple(exact_nonempty_string(item, field=f"{field}[{index}]") for index, item in enumerate(value))


def trust_boundary_crossing_identity(crossing: Mapping[str, Any]) -> tuple[str, str, tuple[str, ...], int]:
    """Return the exact authority-path identity of a recorded boundary crossing.

    An edge/boundary pair is deliberately insufficient identity: the same edge can
    be reached through distinct authority paths carrying different evidence and
    compromise provenance. Missing path evidence stays missing (the empty tuple);
    callers must not reconstruct it from graph connectivity or material lineage.
    """
    if not isinstance(crossing, Mapping):
        raise ValueError("trust-boundary crossing must be a mapping")
    edge_id = exact_nonempty_string(crossing.get("edge_id"), field="crossing.edge_id")
    boundary_ref = exact_nonempty_string(crossing.get("boundary_ref"), field="crossing.boundary_ref")
    path_edge_ids = _exact_ref_sequence(crossing.get("path_edge_ids"), field="crossing.path_edge_ids")
    path_position = crossing.get("path_position", 0)
    if isinstance(path_position, bool) or not isinstance(path_position, int) or path_position < 0:
        raise ValueError("crossing.path_position must be a non-negative integer")
    return edge_id, boundary_ref, path_edge_ids, path_position


def aggregate_trust_boundary_crossings(
    crossings: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate recorded crossings without weakening exact-path evidence.

    This helper intentionally knows nothing about graph connectivity, material
    lineage, reliance, or affectedness. Two crossings merge only when their
    recorded authority-path identities are exactly equal. It also does not invent
    compromise provenance: if otherwise-identical records carry seed provenance,
    only explicitly recorded exact seed refs are unioned.
    """
    aggregated: dict[tuple[str, str, tuple[str, ...], int], dict[str, Any]] = {}
    for raw in crossings:
        if not isinstance(raw, Mapping):
            raise ValueError("trust-boundary crossing must be a mapping")
        item = dict(raw)
        identity = trust_boundary_crossing_identity(item)
        current = aggregated.get(identity)
        if current is None:
            if "compromise_seed_refs" in item:
                seeds = _exact_ref_sequence(item.get("compromise_seed_refs"), field="crossing.compromise_seed_refs")
                item["compromise_seed_refs"] = sorted(set(seeds))
            aggregated[identity] = item
            continue

        if "compromise_seed_refs" in current or "compromise_seed_refs" in item:
            current_seeds = _exact_ref_sequence(current.get("compromise_seed_refs"), field="crossing.compromise_seed_refs")
            raw_seeds = _exact_ref_sequence(item.get("compromise_seed_refs"), field="crossing.compromise_seed_refs")
            current["compromise_seed_refs"] = sorted({*current_seeds, *raw_seeds})

    return [aggregated[key] for key in sorted(aggregated)]


def project_trust_boundary_crossings(
    store: TestamurAuthorityStore,
    edge_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Project only trust-boundary crossings explicitly attached to authority edges.

    Boundary membership is not authority and graph connectivity is not a crossing.
    A crossing exists here only when the exact traversed authority edge carries the
    boundary reference. Material lineage, reliance, affectedness, endpoint domains,
    and neighboring connectivity are never consulted to infer one.
    """
    path_edge_ids = _exact_ref_sequence(tuple(edge_ids), field="authority_path.edge_ids")
    crossings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...], int]] = set()
    for position, edge_id in enumerate(path_edge_ids):
        edge = store.get_edge(edge_id)
        exact_edge_id, source_ref, target_ref, relation_type = exact_authority_edge_identity(edge)
        if exact_edge_id != edge_id:
            raise ValueError("authority path edge identity does not match fetched edge evidence")
        raw_boundary_refs = edge.get("boundary_refs")
        boundary_refs = _exact_ref_sequence(raw_boundary_refs, field=f"edge[{edge_id}].boundary_refs") if raw_boundary_refs is not None else ()
        for boundary_ref in boundary_refs:
            crossing = {
                "edge_id": edge_id,
                "boundary_ref": boundary_ref,
                "path_position": position,
                "path_edge_ids": list(path_edge_ids),
                "source_ref": source_ref,
                "target_ref": target_ref,
                "relation_type": relation_type,
            }
            identity = trust_boundary_crossing_identity(crossing)
            if identity in seen:
                continue
            seen.add(identity)
            crossings.append(crossing)
    return crossings


def boundary_refs_from_crossings(crossings: Iterable[dict[str, Any]]) -> list[str]:
    """Compatibility projection for clients that only need the exact boundary set."""
    refs: set[str] = set()
    for index, item in enumerate(crossings):
        if not isinstance(item, Mapping):
            raise ValueError(f"crossings[{index}] must be a mapping")
        refs.add(exact_nonempty_string(item.get("boundary_ref"), field=f"crossings[{index}].boundary_ref"))
    return sorted(refs)


__all__ = [
    "project_trust_boundary_crossings",
    "boundary_refs_from_crossings",
    "trust_boundary_crossing_identity",
    "aggregate_trust_boundary_crossings",
]
