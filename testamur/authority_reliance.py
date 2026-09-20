from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence


class RelianceReceiptView(Protocol):
    def list(self, *, scope_ref: str, reliant_ref: str | None = None, object_ref: str | None = None) -> list[dict[str, Any]]: ...


def _required(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"{field} must not be empty")
    return text


def _binding_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("binding evidence must be a sequence")
    result: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            raise ValueError("binding evidence entries must be mappings")
        item = dict(raw)
        item["ref"] = _required(item.get("ref"), field="binding.evidence.ref")
        item["evidence_class"] = _required(item.get("evidence_class"), field="binding.evidence.evidence_class")
        if item["evidence_class"] not in {"OBSERVED", "DERIVED", "DECLARED"}:
            raise ValueError("binding.evidence.evidence_class must be OBSERVED, DERIVED, or DECLARED")
        if item["evidence_class"] == "DERIVED":
            item["analyzer"] = _required(item.get("analyzer"), field="binding.evidence.analyzer")
            item["analyzer_version"] = _required(item.get("analyzer_version"), field="binding.evidence.analyzer_version")
        result.append(item)
    if not result:
        raise ValueError("authority/reliance bindings require explicit evidence")
    return result


def _binding_matches_receipt(binding: Mapping[str, Any], *, relied_object_ref: str, pinned: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    """Match every identity dimension explicitly recorded by the binding.

    A compound object+revision binding is conjunctive.  Matching either half is
    insufficient: otherwise an authority target could be projected onto a
    different relied object merely because one revision ref happened to match.
    Missing dimensions remain unspecified; they are never inferred.
    """
    object_ref = binding.get("object_ref")
    revision_ref = binding.get("revision_ref")
    object_match = object_ref is not None and relied_object_ref == object_ref
    revision_match = revision_ref is not None and revision_ref in {str(value) for value in pinned.values()}
    required_matches = []
    if object_ref is not None:
        required_matches.append(object_match)
    if revision_ref is not None:
        required_matches.append(revision_match)
    return bool(required_matches) and all(required_matches), object_match, revision_match


def authority_reliance_impact(authority_result: Mapping[str, Any], reliance_store: RelianceReceiptView, *, scope_ref: str, bindings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Project actionable authority onto actual durable Reliance receipts.

    Authority and material reliance remain separate graphs.  Projection requires
    an evidence-bearing, exact binding; connectivity or display-label similarity
    never creates resource identity.
    """
    scope = _required(scope_ref, field="scope_ref")
    actions = authority_result.get("actionable_capabilities")
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes, bytearray)):
        raise ValueError("authority_result.actionable_capabilities must be a sequence")

    normalized_bindings: dict[str, list[dict[str, Any]]] = {}
    for raw in bindings:
        if not isinstance(raw, Mapping):
            raise ValueError("bindings must contain mappings")
        binding = dict(raw)
        target_ref = _required(binding.get("authority_target_ref"), field="binding.authority_target_ref")
        binding_ref = _required(binding.get("binding_ref"), field="binding.binding_ref")
        object_ref, revision_ref = binding.get("object_ref"), binding.get("revision_ref")
        if object_ref is None and revision_ref is None:
            raise ValueError("authority/reliance binding requires object_ref and/or revision_ref")
        normalized_bindings.setdefault(target_ref, []).append({
            "authority_target_ref": target_ref,
            "binding_ref": binding_ref,
            "object_ref": None if object_ref is None else _required(object_ref, field="binding.object_ref"),
            "revision_ref": None if revision_ref is None else _required(revision_ref, field="binding.revision_ref"),
            "evidence": _binding_evidence(binding.get("evidence")),
        })

    receipts = reliance_store.list(scope_ref=scope)
    impacts: list[dict[str, Any]] = []
    unmatched_actions: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for raw_action in actions:
        if not isinstance(raw_action, Mapping):
            raise ValueError("authority action entries must be mappings")
        action = dict(raw_action)
        target_ref = _required(action.get("target_ref"), field="authority_action.target_ref")
        target_bindings = normalized_bindings.get(target_ref, [])
        if not target_bindings:
            unmatched_actions.append({"target_ref": target_ref, "capability": action.get("capability"), "path_edge_ids": list(action.get("path_edge_ids") or []), "reason": "no_explicit_authority_to_reliance_binding"})
            continue
        matched_any = False
        for binding in target_bindings:
            for receipt in receipts:
                if not isinstance(receipt, Mapping):
                    raise ValueError("reliance store returned a non-mapping receipt")
                receipt_id = _required(receipt.get("receipt_id"), field="receipt_id")
                reliant_ref = _required(receipt.get("reliant_ref"), field="reliant_ref")
                relied_object_ref = _required(receipt.get("object_ref"), field="receipt.object_ref")
                pinned = receipt.get("pinned_revisions")
                if not isinstance(pinned, Mapping):
                    raise ValueError("receipt.pinned_revisions must be a mapping")
                binding_match, object_match, revision_match = _binding_matches_receipt(binding, relied_object_ref=relied_object_ref, pinned=pinned)
                if not binding_match:
                    continue
                matched_any = True
                capability = action.get("capability")
                capability = dict(capability) if isinstance(capability, Mapping) else {}
                path = tuple(str(item) for item in action.get("path_edge_ids") or [])
                key = (receipt_id, binding["binding_ref"], target_ref, str(capability.get("namespace") or ""), str(capability.get("action") or ""), str(capability.get("resource") or ""), path)
                if key in seen:
                    continue
                seen.add(key)
                impacts.append({"receipt_id": receipt_id, "reliant_ref": reliant_ref, "reliant_revision_ref": receipt.get("reliant_revision_ref"), "relied_object_ref": relied_object_ref, "authority_target_ref": target_ref, "binding_ref": binding["binding_ref"], "binding_evidence": binding["evidence"], "object_match": object_match, "revision_match": revision_match, "capability": capability, "authority_path_edge_ids": list(path), "authority_evidence_state": action.get("evidence_state"), "review_required": True})
        if not matched_any:
            unmatched_actions.append({"target_ref": target_ref, "capability": action.get("capability"), "path_edge_ids": list(action.get("path_edge_ids") or []), "reason": "explicit_binding_did_not_match_any_durable_reliance"})

    impacts.sort(key=lambda item: (str(item["reliant_ref"]), str(item["receipt_id"]), str(item["authority_target_ref"]), str(item["capability"].get("namespace") or ""), str(item["capability"].get("action") or ""), tuple(item["authority_path_edge_ids"])))
    return {"schema_version": "testamur.authority-reliance-impact.v1", "scope_ref": scope, "impact_count": len(impacts), "affected_reliant_refs": sorted({str(item["reliant_ref"]) for item in impacts}), "impacts": impacts, "unmatched_actions": unmatched_actions, "semantics": {"authority_does_not_imply_reliance": True, "resource_identity_is_never_guessed": True, "compound_bindings_are_conjunctive": True, "actual_durable_reliance_only": True, "reachable_does_not_mean_exercised": True, "authority_reachability_triggers_review_not_falsehood": True}}


__all__ = ["RelianceReceiptView", "authority_reliance_impact"]
