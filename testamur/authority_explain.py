from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .authority import TestamurAuthorityStore


def _required(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must not be empty")
    return text


def _project_edge(edge: Mapping[str, Any], *, index: int | None = None) -> dict[str, Any]:
    evidence = [dict(item) for item in edge.get("evidence") or [] if isinstance(item, Mapping)]
    evidence_classes = sorted({str(item.get("evidence_class") or "") for item in evidence if str(item.get("evidence_class") or "")})
    boundaries = sorted({str(ref) for ref in edge.get("boundary_refs") or [] if str(ref)})
    projected = {
        "edge_id": str(edge["edge_id"]),
        "source_ref": str(edge["source_ref"]),
        "target_ref": str(edge["target_ref"]),
        "relation_type": str(edge["relation_type"]),
        "capabilities": list(edge.get("capabilities") or []),
        "constraints": dict(edge.get("constraints") or {}),
        "boundary_refs": boundaries,
        "evidence": evidence,
        "evidence_classes": evidence_classes,
        "declared_only": bool(evidence_classes) and set(evidence_classes) <= {"DECLARED"},
        "recorded_at": edge.get("recorded_at"),
    }
    if index is not None:
        projected["index"] = index
    return projected


def explain_authority_path(
    store: TestamurAuthorityStore,
    edge_ids: Sequence[str] | Iterable[str],
    *,
    starting_ref: str | None = None,
    expected_target_ref: str | None = None,
    supporting_edge_ids: Sequence[str] | Iterable[str] = (),
) -> dict[str, Any]:
    """Hydrate and validate one exact authority path.

    The function never searches for missing edges and never repairs a broken path.
    Every returned transition is an immutable edge already recorded by the authority
    store. Supporting credential/token evidence stays separate from traversed edges.
    """

    ids = [_required(edge_id, field="edge_ids[]") for edge_id in edge_ids]
    if not ids:
        raise ValueError("edge_ids must contain at least one authority edge")
    support_ids = sorted({_required(edge_id, field="supporting_edge_ids[]") for edge_id in supporting_edge_ids})

    edges = [store.get_edge(edge_id) for edge_id in ids]
    first_source = str(edges[0]["source_ref"])
    expected_source = first_source if starting_ref is None else _required(starting_ref, field="starting_ref")
    if first_source != expected_source:
        raise ValueError(f"authority path does not start at the expected subject: {first_source!r} != {expected_source!r}")

    transitions: list[dict[str, Any]] = []
    subject_refs: list[str] = [expected_source]
    boundary_refs: set[str] = set()
    declared_only_edges: list[str] = []
    boundary_crossings: list[dict[str, Any]] = []

    previous_target: str | None = None
    for index, edge in enumerate(edges):
        source_ref = str(edge["source_ref"])
        target_ref = str(edge["target_ref"])
        if previous_target is not None and source_ref != previous_target:
            raise ValueError(f"authority path is not contiguous at edge {edge['edge_id']}: expected source {previous_target!r}, got {source_ref!r}")

        projected = _project_edge(edge, index=index)
        if projected["declared_only"]:
            declared_only_edges.append(projected["edge_id"])
        boundary_refs.update(projected["boundary_refs"])
        for boundary_ref in projected["boundary_refs"]:
            boundary_crossings.append({
                "boundary_ref": boundary_ref,
                "edge_id": projected["edge_id"],
                "source_ref": source_ref,
                "target_ref": target_ref,
                "path_index": index,
            })
        transitions.append(projected)
        subject_refs.append(target_ref)
        previous_target = target_ref

    supporting_edges: list[dict[str, Any]] = []
    supporting_subject_refs: set[str] = set()
    for edge_id in support_ids:
        edge = store.get_edge(edge_id)
        projected = _project_edge(edge)
        if projected["declared_only"]:
            declared_only_edges.append(projected["edge_id"])
        boundary_refs.update(projected["boundary_refs"])
        supporting_subject_refs.update({projected["source_ref"], projected["target_ref"]})
        supporting_edges.append(projected)

    final_target = str(edges[-1]["target_ref"])
    if expected_target_ref is not None:
        expected_target = _required(expected_target_ref, field="expected_target_ref")
        if final_target != expected_target:
            raise ValueError(f"authority path does not end at the expected target: {final_target!r} != {expected_target!r}")

    subjects: list[dict[str, Any]] = []
    all_subject_refs = list(subject_refs)
    all_subject_refs.extend(ref for ref in sorted(supporting_subject_refs) if ref not in subject_refs)
    for ref in all_subject_refs:
        subject = store.maybe_subject(ref)
        subjects.append({"subject_ref": ref, "recorded_subject": subject, "subject_record_available": subject is not None})

    # Canonical structured projections are aliases of the exact hydrated records,
    # not a second evaluator. In particular, supporting evidence is not inserted
    # into authority_edges and boundary crossings are emitted only for boundary_refs
    # recorded on traversed authority edges.
    return {
        "schema_version": "testamur.authority-path-explanation.v1",
        "starting_ref": expected_source,
        "target_ref": final_target,
        "edge_ids": ids,
        "supporting_edge_ids": support_ids,
        "subject_refs": subject_refs,
        "supporting_subject_refs": sorted(supporting_subject_refs),
        "subjects": subjects,
        "transitions": transitions,
        "supporting_edges": supporting_edges,
        "authority_edges": transitions,
        "supporting_evidence": supporting_edges,
        "trust_boundary_crossings": boundary_crossings,
        "trust_boundary_refs": sorted(boundary_refs),
        "declared_only_edge_ids": declared_only_edges,
        "semantics": {
            "exact_recorded_edges_only": True,
            "missing_edges_are_not_guessed": True,
            "supporting_edges_are_not_forced_into_path_contiguity": True,
            "supporting_evidence_is_not_authority_path": True,
            "boundary_crossings_require_recorded_path_boundary_refs": True,
            "path_does_not_prove_action_was_exercised": True,
            "declared_evidence_is_not_promoted_to_observed": True,
        },
    }


__all__ = ["explain_authority_path"]
