from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping, Sequence

from .authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from .authority_boundaries import boundary_refs_from_crossings, project_trust_boundary_crossings
from .authority_graph_constraints import evaluate_exact_edge_constraints
from .authority_projection import capability_identity
from .authority_reachability_policy import (
    action_result_identity,
    downstream_budget,
    exercisable_capabilities,
    project_downstream_budget,
    traversal_state_identity,
)


class CompromiseModel(StrEnum):
    READ_ONLY_COMPROMISE = "READ_ONLY_COMPROMISE"
    PROCESS_CODE_EXECUTION = "PROCESS_CODE_EXECUTION"
    ACCOUNT_SESSION_TAKEOVER = "ACCOUNT_SESSION_TAKEOVER"
    CONNECTOR_TAKEOVER = "CONNECTOR_TAKEOVER"
    CREDENTIAL_THEFT = "CREDENTIAL_THEFT"
    FULL_SUBJECT_COMPROMISE = "FULL_SUBJECT_COMPROMISE"


class AuthorityReachabilityClass(StrEnum):
    CONTROLLED = "CONTROLLED"
    CREDENTIAL_ACQUIRED = "CREDENTIAL_ACQUIRED"
    ACTIONABLE = "ACTIONABLE"
    CONDITIONALLY_ACTIONABLE = "CONDITIONALLY_ACTIONABLE"
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"


_CREDENTIAL_KINDS = {
    AuthoritySubjectKind.CREDENTIAL.value,
    AuthoritySubjectKind.TOKEN.value,
    AuthoritySubjectKind.SECRET.value,
    AuthoritySubjectKind.SESSION.value,
}
_ACTION_RELATIONS = {
    AuthorityRelationType.CAN_READ.value,
    AuthorityRelationType.CAN_WRITE.value,
    AuthorityRelationType.CAN_EXECUTE.value,
    AuthorityRelationType.HAS_CAPABILITY.value,
}
_PROPAGATING_RELATIONS = {
    AuthorityRelationType.EXPOSES.value,
    AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
    AuthorityRelationType.CAN_IMPERSONATE.value,
    AuthorityRelationType.DELEGATES.value,
    AuthorityRelationType.CAN_EXECUTE.value,
}
_MODEL_RELATIONS = {
    CompromiseModel.READ_ONLY_COMPROMISE.value: frozenset({AuthorityRelationType.CAN_READ.value, AuthorityRelationType.EXPOSES.value}),
    CompromiseModel.PROCESS_CODE_EXECUTION.value: frozenset({AuthorityRelationType.CAN_READ.value, AuthorityRelationType.CAN_WRITE.value, AuthorityRelationType.CAN_EXECUTE.value, AuthorityRelationType.CAN_CONNECT.value, AuthorityRelationType.CAN_IMPERSONATE.value, AuthorityRelationType.CAN_AUTHENTICATE_AS.value, AuthorityRelationType.DELEGATES.value, AuthorityRelationType.HAS_CAPABILITY.value, AuthorityRelationType.EXPOSES.value}),
    CompromiseModel.ACCOUNT_SESSION_TAKEOVER.value: frozenset({AuthorityRelationType.CAN_READ.value, AuthorityRelationType.CAN_WRITE.value, AuthorityRelationType.CAN_CONNECT.value, AuthorityRelationType.CAN_IMPERSONATE.value, AuthorityRelationType.CAN_AUTHENTICATE_AS.value, AuthorityRelationType.DELEGATES.value, AuthorityRelationType.HAS_CAPABILITY.value, AuthorityRelationType.EXPOSES.value}),
    CompromiseModel.CONNECTOR_TAKEOVER.value: frozenset({AuthorityRelationType.CAN_READ.value, AuthorityRelationType.CAN_WRITE.value, AuthorityRelationType.CAN_CONNECT.value, AuthorityRelationType.CAN_EXECUTE.value, AuthorityRelationType.HAS_CAPABILITY.value, AuthorityRelationType.EXPOSES.value}),
    CompromiseModel.CREDENTIAL_THEFT.value: frozenset({AuthorityRelationType.CAN_AUTHENTICATE_AS.value, AuthorityRelationType.CAN_IMPERSONATE.value, AuthorityRelationType.DELEGATES.value, AuthorityRelationType.HAS_CAPABILITY.value}),
    CompromiseModel.FULL_SUBJECT_COMPROMISE.value: frozenset(item.value for item in AuthorityRelationType),
}


def _normalize_model(value: str | CompromiseModel) -> str:
    try:
        return CompromiseModel(str(value)).value
    except ValueError as exc:
        raise ValueError(f"unsupported compromise model {value!r}") from exc


def _as_of(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    text = str(value).strip()
    if not text:
        raise ValueError("as_of must be an ISO timestamp or datetime")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _subject(store: TestamurAuthorityStore, ref: str) -> Mapping[str, Any]:
    return store.maybe_subject(ref) or {}


def _kind(store: TestamurAuthorityStore, ref: str) -> str:
    return str(_subject(store, ref).get("kind") or AuthoritySubjectKind.OTHER.value)


def _attrs(store: TestamurAuthorityStore, ref: str) -> Mapping[str, Any]:
    attrs = _subject(store, ref).get("attributes")
    return attrs if isinstance(attrs, Mapping) else {}


def _declared_only(edge: Mapping[str, Any]) -> bool:
    evidence = edge.get("evidence") or []
    if not evidence:
        return True
    classes = {str(item.get("evidence_class") or "") for item in evidence if isinstance(item, Mapping)}
    return bool(classes) and classes <= {"DECLARED"}


def _constraints(store: TestamurAuthorityStore, edge: Mapping[str, Any], at: datetime, *, attribute_ref: str | None = None) -> tuple[bool, list[str], list[str]]:
    source_ref = str(edge.get("source_ref") or "")
    target_ref = str(edge.get("target_ref") or "")
    credential_ref = attribute_ref or source_ref
    return evaluate_exact_edge_constraints(
        edge,
        credential_attributes=_attrs(store, credential_ref),
        source_subject=_subject(store, source_ref),
        target_subject=_subject(store, target_ref),
        attribute_ref=attribute_ref,
        as_of=at,
    )


def _acceptance(store: TestamurAuthorityStore, edge: Mapping[str, Any], at: datetime) -> tuple[bool, list[str], list[str], list[str], bool]:
    constraints = edge.get("constraints") if isinstance(edge.get("constraints"), Mapping) else {}
    service_ref = str(constraints.get("service_ref") or "").strip()
    if not service_ref:
        return True, [], [], [], False
    credential_ref = str(edge.get("source_ref") or "").strip()
    candidates = store.list_edges(source_ref=service_ref, target_ref=credential_ref, relation_type=AuthorityRelationType.ACCEPTS_CREDENTIAL)
    if not candidates:
        return False, [], ["credential_acceptance_not_established"], [], False
    reasons: set[str] = set()
    unresolved: set[str] = set()
    for candidate in candidates:
        ok, why, unknown = _constraints(store, candidate, at, attribute_ref=credential_ref)
        if ok:
            return True, [str(candidate["edge_id"])], [], [], _declared_only(candidate)
        reasons.update(why)
        unresolved.update(unknown)
    return False, sorted(str(c["edge_id"]) for c in candidates), sorted({"credential_acceptance_constraints_unsatisfied", *reasons}), sorted(unresolved), all(_declared_only(c) for c in candidates)


def _evidence_state(declared: bool) -> str:
    return "CONTAINS_DECLARED_ONLY_EDGE" if declared else "CORROBORATED"


def authority_reachability(store: TestamurAuthorityStore, starting_subject_ref: str, *, compromise_model: str | CompromiseModel, capability_filter: Iterable[tuple[str, str]] | None = None, max_depth: int = 8, max_paths: int = 256, expansion_budget: int = 10000, as_of: str | datetime | None = None) -> dict[str, Any]:
    start = str(starting_subject_ref or "").strip()
    if not start:
        raise ValueError("starting_subject_ref must not be empty")
    if max_depth < 0 or max_paths < 1 or expansion_budget < 1:
        raise ValueError("invalid reachability bound")
    model = _normalize_model(compromise_model)
    allowed = _MODEL_RELATIONS[model]
    at = _as_of(as_of)
    filters = None if capability_filter is None else {(str(n), str(a)) for n, a in capability_filter}
    queue = deque([{"subject_ref": start, "depth": 0, "edge_ids": [], "supporting_edge_ids": [], "visited_refs": (start,), "budget": None, "declared": False, "class": AuthorityReachabilityClass.CONTROLLED.value}])
    reachable = [{"subject_ref": start, "kind": _kind(store, start), "reachability_class": AuthorityReachabilityClass.CONTROLLED.value, "depth": 0, "path_edge_ids": [], "supporting_edge_ids": [], "boundary_refs": [], "trust_boundary_crossings": [], "evidence_state": "SEED_ASSUMPTION", "delegated_capability_budget": None}]
    actions: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = {traversal_state_identity(start, AuthorityReachabilityClass.CONTROLLED.value, None, ())}
    expansions = 0
    emitted = 1
    trunc: set[str] = set()

    while queue:
        current = queue.popleft()
        source = str(current["subject_ref"])
        depth = int(current["depth"])
        if depth >= max_depth:
            if store.edges_from(source): trunc.add("max_depth")
            continue
        for edge in store.edges_from(source):
            expansions += 1
            if expansions > expansion_budget:
                trunc.add("expansion_budget"); queue.clear(); break
            relation = str(edge.get("relation_type") or "")
            if relation not in allowed:
                continue
            target = str(edge.get("target_ref") or "")
            edge_id = str(edge.get("edge_id") or "")
            path = [*current["edge_ids"], edge_id]
            supporting = list(current.get("supporting_edge_ids") or [])
            ok, reasons, unresolved = _constraints(store, edge, at)
            support_declared = False
            if ok and relation == AuthorityRelationType.CAN_AUTHENTICATE_AS.value:
                accepted, support, why, unknown, support_declared = _acceptance(store, edge, at)
                supporting = sorted({*supporting, *support})
                if not accepted:
                    ok = False; reasons = sorted({*reasons, *why}); unresolved = sorted({*unresolved, *unknown})
            declared = bool(current["declared"]) or _declared_only(edge) or support_declared
            crossings = project_trust_boundary_crossings(store, path)
            boundary_refs = boundary_refs_from_crossings(crossings)
            if not ok:
                gates = {"approval_required", "human_confirmation_required", "mfa_required"}
                blocked.append({"edge_id": edge_id, "source_ref": source, "target_ref": target, "relation_type": relation, "path_edge_ids": path, "supporting_edge_ids": supporting, "reasons": reasons, "unresolved_constraints": unresolved, "reachability_class": AuthorityReachabilityClass.CONDITIONALLY_ACTIONABLE.value if reasons and set(reasons) <= gates else AuthorityReachabilityClass.BLOCKED.value, "evidence_state": _evidence_state(declared)})
                continue

            budget = current["budget"]
            capabilities = exercisable_capabilities(edge, budget)
            if filters is not None:
                capabilities = [c for c in capabilities if (str(c.get("namespace") or ""), str(c.get("action") or "")) in filters]
            if relation in _ACTION_RELATIONS:
                if relation == AuthorityRelationType.HAS_CAPABILITY.value and not capabilities:
                    blocked.append({"edge_id": edge_id, "source_ref": source, "target_ref": target, "relation_type": relation, "path_edge_ids": path, "supporting_edge_ids": supporting, "reasons": ["missing_explicit_or_authorized_capability"], "unresolved_constraints": [], "reachability_class": AuthorityReachabilityClass.UNKNOWN.value, "evidence_state": _evidence_state(declared)})
                for capability in capabilities:
                    key = action_result_identity(target, capability, path)
                    if key in seen: continue
                    seen.add(key)
                    actions.append({"source_ref": source, "target_ref": target, "relation_type": relation, "capability": capability, "reachability_class": AuthorityReachabilityClass.ACTIONABLE.value, "depth": depth + 1, "path_edge_ids": path, "supporting_edge_ids": supporting, "boundary_refs": boundary_refs, "trust_boundary_crossings": crossings, "evidence_state": _evidence_state(declared)})
                    emitted += 1
                    if emitted >= max_paths: trunc.add("max_paths"); queue.clear(); break
                if "max_paths" in trunc: break

            propagate = relation in _PROPAGATING_RELATIONS
            target_kind = _kind(store, target)
            next_class = AuthorityReachabilityClass.CONTROLLED.value
            next_budget = budget
            if relation == AuthorityRelationType.CAN_READ.value and target_kind in _CREDENTIAL_KINDS:
                propagate = True; next_class = AuthorityReachabilityClass.CREDENTIAL_ACQUIRED.value; next_budget = None
            elif relation == AuthorityRelationType.EXPOSES.value:
                next_class = AuthorityReachabilityClass.CREDENTIAL_ACQUIRED.value if target_kind in _CREDENTIAL_KINDS else AuthorityReachabilityClass.CONTROLLED.value
                next_budget = None
            elif relation == AuthorityRelationType.DELEGATES.value:
                next_budget = downstream_budget(edge, budget)
                if next_budget == ():
                    blocked.append({"edge_id": edge_id, "source_ref": source, "target_ref": target, "relation_type": relation, "path_edge_ids": path, "supporting_edge_ids": supporting, "reasons": ["missing_or_empty_delegated_capability_set"], "unresolved_constraints": [], "reachability_class": AuthorityReachabilityClass.UNKNOWN.value, "evidence_state": _evidence_state(declared)})
                    propagate = False
            elif relation in {AuthorityRelationType.CAN_AUTHENTICATE_AS.value, AuthorityRelationType.CAN_IMPERSONATE.value}:
                next_budget = downstream_budget(edge, None)
            if not propagate or target in current["visited_refs"]:
                continue
            state_key = traversal_state_identity(target, next_class, next_budget, path)
            if state_key not in seen:
                seen.add(state_key)
                reachable.append({"subject_ref": target, "kind": target_kind, "reachability_class": next_class, "depth": depth + 1, "path_edge_ids": path, "supporting_edge_ids": supporting, "boundary_refs": boundary_refs, "trust_boundary_crossings": crossings, "evidence_state": _evidence_state(declared), "delegated_capability_budget": project_downstream_budget(next_budget)})
                emitted += 1
                if emitted >= max_paths: trunc.add("max_paths"); queue.clear(); break
            queue.append({"subject_ref": target, "depth": depth + 1, "edge_ids": path, "supporting_edge_ids": supporting, "visited_refs": (*current["visited_refs"], target), "budget": next_budget, "declared": declared, "class": next_class})
        if trunc & {"expansion_budget", "max_paths"}: break

    by_target: dict[str, list[dict[str, Any]]] = {}
    for action in actions: by_target.setdefault(str(action["target_ref"]), []).append(action)
    all_crossings: dict[tuple[str, str], dict[str, Any]] = {}
    for item in [*reachable, *actions]:
        for crossing in item.get("trust_boundary_crossings") or []:
            all_crossings[(crossing["edge_id"], crossing["boundary_ref"])] = crossing
    crossings = sorted(all_crossings.values(), key=lambda x: (x["path_position"], x["edge_id"], x["boundary_ref"]))
    return {"schema_version": "testamur.authority-reachability.v1", "starting_subject_ref": start, "compromise_model": model, "as_of": at.isoformat().replace("+00:00", "Z"), "reachable_subjects": reachable, "actionable_capabilities": actions, "actionable_by_target": by_target, "blocked_transitions": blocked, "trust_boundary_refs": boundary_refs_from_crossings(crossings), "trust_boundary_crossings": crossings, "expansions": expansions, "truncated": bool(trunc), "truncation_reasons": sorted(trunc), "semantics": {"reachable_does_not_mean_exercised": True, "network_reachability_does_not_mean_authorization": True, "credential_presence_does_not_mean_universal_acceptance": True, "resource_action_does_not_imply_resource_control": True, "constraints_fail_closed": True, "delegation_preserves_capability_budget": True}}


def authority_blast_radius(store: TestamurAuthorityStore, compromised_refs: str | Sequence[str], *, compromise_model: str | CompromiseModel, capability_filter: Iterable[tuple[str, str]] | None = None, max_depth: int = 8, max_paths: int = 256, expansion_budget: int = 10000, as_of: str | datetime | None = None) -> dict[str, Any]:
    refs = [compromised_refs] if isinstance(compromised_refs, str) else list(compromised_refs)
    seeds = sorted({str(ref).strip() for ref in refs if str(ref).strip()})
    if not seeds: raise ValueError("compromised_refs must contain at least one subject ref")
    results = [authority_reachability(store, ref, compromise_model=compromise_model, capability_filter=capability_filter, max_depth=max_depth, max_paths=max_paths, expansion_budget=expansion_budget, as_of=as_of) for ref in seeds]
    subjects: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    actions: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    blocked: list[dict[str, Any]] = []
    crossings: dict[tuple[str, str], dict[str, Any]] = {}
    trunc: set[str] = set()
    for result in results:
        for item in result["reachable_subjects"]: subjects[(str(item["subject_ref"]), tuple(item.get("path_edge_ids") or []))] = item
        for item in result["actionable_capabilities"]: actions[(str(item["target_ref"]), capability_identity(item["capability"]), tuple(item.get("path_edge_ids") or []))] = item
        blocked.extend(result["blocked_transitions"])
        for crossing in result.get("trust_boundary_crossings") or []: crossings[(crossing["edge_id"], crossing["boundary_ref"])] = crossing
        trunc.update(result["truncation_reasons"])
    crossing_values = sorted(crossings.values(), key=lambda x: (x["edge_id"], x["boundary_ref"]))
    return {"schema_version": "testamur.authority-blast-radius.v1", "compromised_refs": seeds, "compromise_model": _normalize_model(compromise_model), "reachable_subjects": sorted(subjects.values(), key=lambda x: (int(x.get("depth") or 0), str(x.get("subject_ref") or ""), tuple(x.get("path_edge_ids") or []))), "actionable_capabilities": sorted(actions.values(), key=lambda x: (str(x.get("target_ref") or ""), capability_identity(x["capability"]), tuple(x.get("path_edge_ids") or []))), "blocked_transitions": blocked, "trust_boundary_refs": boundary_refs_from_crossings(crossing_values), "trust_boundary_crossings": crossing_values, "truncated": bool(trunc), "truncation_reasons": sorted(trunc), "semantics": {"blast_radius_is_potential_authority_not_observed_malicious_use": True, "affectedness_does_not_automatically_seed_compromise": True, "material_lineage_does_not_grant_authority": True}}


__all__ = ["CompromiseModel", "AuthorityReachabilityClass", "authority_reachability", "authority_blast_radius"]