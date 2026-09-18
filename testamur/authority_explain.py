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


def explain_authority_path(
    store: TestamurAuthorityStore,
    edge_ids: Sequence[str] | Iterable[str],
    *,
    starting_ref: str | None = None,
    expected_target_ref: str | None = None,
) -> dict[str, Any]:
    """Hydrate and validate one exact authority path.

    The function never searches for missing edges and never repairs a broken path.
    Every returned transition is an immutable edge already recorded by the authority
    store. This makes explanations suitable for showing the exact basis of a
    compromise-reachability result.
    """

    ids = [_required(edge_id, field="edge_ids[]") for edge_id in edge_ids]
    if not ids:
        raise ValueError("edge_ids must contain at least one authority edge")

    edges = [store.get_edge(edge_id) for edge_id in ids]
    first_source = str(edges[0]["source_ref"])
    expected_source = (
        first_source
        if starting_ref is None
        else _required(starting_ref, field="starting_ref")
    )
    if first_source != expected_source:
        raise ValueError(
            "authority path does not start at the expected subject: "
            f"{first_source!r} != {expected_source!r}"
        )

    transitions: list[dict[str, Any]] = []
    subject_refs: list[str] = [expected_source]
    boundary_refs: set[str] = set()
    declared_only_edges: list[str] = []

    previous_target: str | None = None
    for index, edge in enumerate(edges):
        source_ref = str(edge["source_ref"])
        target_ref = str(edge["target_ref"])
        if previous_target is not None and source_ref != previous_target:
            raise ValueError(
                "authority path is not contiguous at edge "
                f"{edge['edge_id']}: expected source {previous_target!r}, "
                f"got {source_ref!r}"
            )

        evidence = [
            dict(item)
            for item in edge.get("evidence") or []
            if isinstance(item, Mapping)
        ]
        evidence_classes = sorted(
            {
                str(item.get("evidence_class") or "")
                for item in evidence
                if str(item.get("evidence_class") or "")
            }
        )
        declared_only = bool(evidence_classes) and set(evidence_classes) <= {"DECLARED"}
        if declared_only:
            declared_only_edges.append(str(edge["edge_id"]))

        boundaries = sorted(
            {str(ref) for ref in edge.get("boundary_refs") or [] if str(ref)}
        )
        boundary_refs.update(boundaries)
        transitions.append(
            {
                "index": index,
                "edge_id": str(edge["edge_id"]),
                "source_ref": source_ref,
                "target_ref": target_ref,
                "relation_type": str(edge["relation_type"]),
                "capabilities": list(edge.get("capabilities") or []),
                "constraints": dict(edge.get("constraints") or {}),
                "boundary_refs": boundaries,
                "evidence": evidence,
                "evidence_classes": evidence_classes,
                "declared_only": declared_only,
                "recorded_at": edge.get("recorded_at"),
            }
        )
        subject_refs.append(target_ref)
        previous_target = target_ref

    final_target = str(edges[-1]["target_ref"])
    if expected_target_ref is not None:
        expected_target = _required(expected_target_ref, field="expected_target_ref")
        if final_target != expected_target:
            raise ValueError(
                "authority path does not end at the expected target: "
                f"{final_target!r} != {expected_target!r}"
            )

    subjects: list[dict[str, Any]] = []
    for ref in subject_refs:
        subject = store.maybe_subject(ref)
        subjects.append(
            {
                "subject_ref": ref,
                "recorded_subject": subject,
                "subject_record_available": subject is not None,
            }
        )

    return {
        "schema_version": "testamur.authority-path-explanation.v1",
        "starting_ref": expected_source,
        "target_ref": final_target,
        "edge_ids": ids,
        "subject_refs": subject_refs,
        "subjects": subjects,
        "transitions": transitions,
        "trust_boundary_refs": sorted(boundary_refs),
        "declared_only_edge_ids": declared_only_edges,
        "semantics": {
            "exact_recorded_edges_only": True,
            "missing_edges_are_not_guessed": True,
            "path_does_not_prove_action_was_exercised": True,
            "declared_evidence_is_not_promoted_to_observed": True,
        },
    }


__all__ = ["explain_authority_path"]
