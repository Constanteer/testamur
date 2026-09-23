from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping, Sequence

from .authority import AuthorityRelationType, AuthoritySubjectKind, TestamurAuthorityStore
from .authority_blocked import blocked_transition_record
from .authority_boundaries import boundary_refs_from_crossings, project_trust_boundary_crossings
from .authority_edge_identity import exact_authority_edge_identity, exact_nonempty_string, exact_optional_constraint_ref
from .authority_filter import normalize_capability_filter
from .authority_graph_constraints import evaluate_exact_edge_constraints
from .authority_projection import capability_identity
from .authority_reachability_policy import (
    action_result_identity,
    downstream_budget,
    exercisable_capabilities,
    project_downstream_budget,
    traversal_state_identity,
)
from .authority_seed import exact_subject_ref, normalize_compromise_seeds


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
    if isinstance(value, CompromiseModel):
        return value.value
    text = exact_nonempty_string(value, field="compromise_model")
    try:
        return CompromiseModel(text).value
    except ValueError as exc:
        raise ValueError(f"unsupported compromise model {value!r}") from exc


def _as_of(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of datetime must include an explicit timezone")
        return value.astimezone(timezone.utc)
    text = exact_nonempty_string(value, field="as_of")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("as_of must be a timezone-aware ISO timestamp or datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("as_of timestamp must include an explicit timezone")
    return parsed.astimezone(timezone.utc)


def _subject(store: TestamurAuthorityStore, ref: str) -> Mapping[str, Any]:
    exact = exact_subject_ref(ref)
    subject = store.maybe_subject(exact)
    if subject is None:
        return {}
    if not isinstance(subject, Mapping):
        raise ValueError("authority subject must be a mapping")
    return subject


def _kind(store: TestamurAuthorityStore, ref: str) -> str:
    value = _subject(store, ref).get("kind")
    if value is None:
        return AuthoritySubjectKind.OTHER.value
    return exact_nonempty_string(value, field="subject.kind")


def _attrs(store: TestamurAuthorityStore, ref: str) -> Mapping[str, Any]:
    attrs = _subject(store, ref).get("attributes")
    if attrs is None:
        return {}
    if not isinstance(attrs, Mapping):
        raise ValueError("subject.attributes must be a mapping")
    return attrs


def _declared_only(edge: Mapping[str, Any]) -> bool:
    evidence = edge.get("evidence") or []
    if not evidence:
        return True
    if isinstance(evidence, (str, bytes, bytearray)) or not isinstance(evidence, Sequence):
        raise ValueError("edge.evidence must be a sequence of evidence mappings")
    classes: set[str] = set()
    for item in evidence:
        if not isinstance(item, Mapping):
            raise ValueError("edge.evidence[] must be a mapping")
        value = item.get("evidence_class")
        if value is not None:
            classes.add(exact_nonempty_string(value, field="edge.evidence[].evidence_class"))
    return bool(classes) and classes <= {"DECLARED"}


def _constraints(store: TestamurAuthorityStore, edge: Mapping[str, Any], at: datetime, *, attribute_ref: str | None = None) -> tuple[bool, list[str], list[str]]:
    _, source_ref, target_ref, _ = exact_authority_edge_identity(edge)
    credential_ref = exact_subject_ref(attribute_ref, field="attribute_ref") if attribute_ref is not None else source_ref
    return evaluate_exact_edge_constraints(
        edge,
        credential_attributes=_attrs(store, credential_ref),
        source_subject=_subject(store, source_ref),
        target_subject=_subject(store, target_ref),
        attribute_ref=attribute_ref,
        as_of=at,
    )


def _acceptance(store: TestamurAuthorityStore, edge: Mapping[str, Any], at: datetime) -> tuple[bool, list[str], list[str], list[str], bool]:
    _, credential_ref, _, _ = exact_authority_edge_identity(edge)
    raw_constraints = edge.get("constraints")
    if raw_constraints is None:
        constraints: Mapping[str, Any] = {}
    elif isinstance(raw_constraints, Mapping):
        constraints = raw_constraints
    else:
        raise ValueError("edge.constraints must be a mapping")
    service_ref = exact_optional_constraint_ref(constraints.get("service_ref"), field="constraints.service_ref")
    if service_ref is None:
        return True, [], [], [], False
    candidates = store.list_edges(source_ref=service_ref, target_ref=credential_ref, relation_type=AuthorityRelationType.ACCEPTS_CREDENTIAL)
    if not candidates:
        return False, [], ["credential_acceptance_not_established"], [], False
    reasons: set[str] = set()
    unresolved: set[str] = set()
    supporting_ids: list[str] = []
    declared_flags: list[bool] = []
    for candidate in candidates:
        candidate_id, _, _, _ = exact_authority_edge_identity(candidate)
        supporting_ids.append(candidate_id)
        declared_flags.append(_declared_only(candidate))
        ok, why, unknown = _constraints(store, candidate, at, attribute_ref=credential_ref)
        if ok:
            return True, [candidate_id], [], [], declared_flags[-1]
        reasons.update(why)
        unresolved.update(unknown)
    return False, sorted(supporting_ids), sorted({"credential_acceptance_constraints_unsatisfied", *reasons}), sorted(unresolved), all(declared_flags)


def _evidence_state(declared: bool) -> str:
    return "CONTAINS_DECLARED_ONLY_EDGE" if declared else "CORROBORATED"


def authority_reachability(store: TestamurAuthorityStore, starting_subject_ref: str, *, compromise_model: str | CompromiseModel, capability_filter: Iterable[tuple[str, str]] | None = None, max_depth: int = 8, max_paths: int = 256, expansion_budget: int = 10000, as_of: str | datetime | None = None) -> dict[str, Any]:
    start = exact_subject_ref(starting_subject_ref, field="starting_subject_ref")
    if max_depth < 0 or max_paths < 1 or expansion_budget < 1:
        raise ValueError("invalid reachability bound")
    model = _normalize_model(compromise_model)
    allowed = _MODEL_RELATIONS[model]
    at = _as_of(as_of)
    normalized_filter = normalize_capability_filter(capability_filter)
    filters = None if normalized_filter is None else set(normalized_filter)
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
        source = exact_subject_ref(current["subject_ref"], field="traversal.subject_ref")
        depth = int(current["depth"])
        if depth >= max_depth:
            if store.edges_from(source):
                trunc.add("max_depth")
            continue
        for edge in store.edges_from(source):
            expansions += 1
            if expansions > expansion_budget:
                trunc.add("expansion_budget")
                queue.clear()
                break
            edge_id, edge_source, target, relation = exact_authority_edge_identity(edge)
            if edge_source != source:
                raise ValueError("edges_from returned an authority edge whose source_ref does not match the traversal subject")
            if relation not in allowed:
                continue
            path = [*current["edge_ids"], edge_id]
            supporting = list(current.get("supporting_edge_ids") or [])
            ok, reasons, unresolved = _constraints(store, edge, at)
            support_declared = False
            if ok and relation == AuthorityRelationType.CAN_AUTHENTICATE_AS.value:
                accepted, support, why, unknown, support_declared = _acceptance(store, edge, at)
                supporting = sorted({*supporting, *support})
                if not accepted:
                    ok = False
                    reasons = sorted({*reasons, *why})
                    unresolved = sorted({*unresolved, *unknown})
            declared = bool(current["declared"]) or _declared_only(edge) or support_declared
            crossings = project_trust_boundary_crossings(store, path)
            boundary_refs = boundary_refs_from_crossings(crossings)
            if not ok:
                gates = {"approval_required", "human_confirmation_required", "mfa_required"}
                blocked.append(blocked_transition_record(
                    edge_id=edge_id, source_ref=source, target_ref=target, relation_type=relation,
                    path_edge_ids=path, supporting_edge_ids=supporting, reasons=reasons,
                    unresolved_constraints=unresolved,
                    reachability_class=AuthorityReachabilityClass.CONDITIONALLY_ACTIONABLE.value if reasons and set(reasons) <= gates else AuthorityReachabilityClass.BLOCKED.value,
                    evidence_state=_evidence_state(declared), boundary_refs=boundary_refs,
                    trust_boundary_crossings=crossings,
                ))
                continue

            budget = current["budget"]
            capabilities = exercisable_capabilities(edge, budget)
            if filters is not None:
                capabilities = [c for c in capabilities if (
                    exact_nonempty_string(c.get("namespace"), field="capability.namespace"),
                    exact_nonempty_string(c.get("action"), field="capability.action"),
                ) in filters]
            if relation in _ACTION_RELATIONS:
                if relation == AuthorityRelationType.HAS_CAPABILITY.value and not capabilities:
                    blocked.append(blocked_transition_record(
                        edge_id=edge_id, source_ref=source, target_ref=target, relation_type=relation,
                        path_edge_ids=path, supporting_edge_ids=supporting,
                        reasons=["missing_explicit_or_authorized_capability"], unresolved_constraints=[],
                        reachability_class=AuthorityReachabilityClass.UNKNOWN.value,
                        evidence_state=_evidence_state(declared), boundary_refs=boundary_refs,
                        trust_boundary_crossings=crossings,
                    ))
                for capability in capabilities:
                    key = action_result_identity(target, capability, path)
                    if key in seen:
                        continue
                    seen.add(key)
                    actions.append({"source_ref": source, "target_ref": target, "relation_type": relation, "capability": capability, "reachability_class": AuthorityReachabilityClass.ACTIONABLE.value, "depth": depth + 1, "path_edge_ids": path, "supporting_edge_ids": supporting, "boundary_refs": boundary_refs, "trust_boundary_crossings": crossings, "evidence_state": _evidence_state(declared)})
                    emitted += 1
                    if emitted >= max_paths:
                        trunc.add("max_paths")
                        queue.clear()
                        break
                if "max_paths" in trunc:
                    break

            propagate = relation in _PROPAGATING_RELATIONS
            target_kind = _kind(store, target)
            next_class = AuthorityReachabilityClass.CONTROLLED.value
            next_budget = budget
            if relation == AuthorityRelationType.CAN_READ.value and target_kind in _CREDENTIAL_KINDS:
                propagate = True
                next_class = AuthorityReachabilityClass.CREDENTIAL_ACQUIRED.value
                next_budget = budget
            elif relation == AuthorityRelationType.EXPOSES.value:
                next_class = AuthorityReachabilityClass.CREDENTIAL_ACQUIRED.value if target_kind in _CREDENTIAL_KINDS else AuthorityReachabilityClass.CONTROLLED.value
                next_budget = budget
            elif relation == AuthorityRelationType.DELEGATES.value:
                next_budget = downstream_budget(edge, budget)
                if next_budget == ():
                    blocked.append(blocked_transition_record(
                        edge_id=edge_id, source_ref=source, target_ref=target, relation_type=relation,
                        path_edge_ids=path, supporting_edge_ids=supporting,
                        reasons=["missing_or_empty_delegated_capability_set"], unresolved_constraints=[],
                        reachability_class=AuthorityReachabilityClass.UNKNOWN.value,
                        evidence_state=_evidence_state(declared), boundary_refs=boundary_refs,
                        trust_boundary_crossings=crossings,
                    ))
                    propagate = False
            elif relation in {AuthorityRelationType.CAN_AUTHENTICATE_AS.value, AuthorityRelationType.CAN_IMPERSONATE.value}:
                next_budget = downstream_budget(edge, budget)
            if not propagate or target in current["visited_refs"]:
                continue
            state_key = traversal_state_identity(target, next_class, next_budget, path)
            if state_key not in seen:
                seen.add(state_key)
                reachable.append({"subject_ref": target, "kind": target_kind, "reachability_class": next_class, "depth": depth + 1, "path_edge_ids": path, "supporting_edge_ids": supporting, "boundary_refs": boundary_refs, "trust_boundary_crossings": crossings, "evidence_state": _evidence_state(declared), "delegated_capability_budget": project_downstream_budget(next_budget)})
                emitted += 1
                if emitted >= max_paths:
                    trunc.add("max_paths")
                    queue.clear()
                    break
            queue.append({"subject_ref": target, "depth": depth + 1, "edge_ids": path, "supporting_edge_ids": supporting, "visited_refs": (*current["visited_refs"], target), "budget": next_budget, "declared": declared, "class": next_class})
        if trunc & {"expansion_budget", "max_paths"}:
            break

    by_target: dict[str, list[dict[str, Any]]] = {}
    for action in actions:
        target_ref = exact_subject_ref(action["target_ref"], field="action.target_ref")
        by_target.setdefault(target_ref, []).append(action)
    all_crossings: dict[tuple[str, str], dict[str, Any]] = {}
    for item in [*reachable, *actions]:
        for crossing in item.get("trust_boundary_crossings") or []:
            all_crossings[(crossing["edge_id"], crossing["boundary_ref"])] = crossing
    crossings = sorted(all_crossings.values(), key=lambda x: (x["path_position"], x["edge_id"], x["boundary_ref"]))
    return {"schema_version": "testamur.authority-reachability.v1", "starting_subject_ref": start, "compromise_model": model, "as_of": at.isoformat().replace("+00:00", "Z"), "reachable_subjects": reachable, "actionable_capabilities": actions, "actionable_by_target": by_target, "blocked_transitions": blocked, "trust_boundary_refs": boundary_refs_from_crossings(crossings), "trust_boundary_crossings": crossings, "expansions": expansions, "truncated": bool(trunc), "truncation_reasons": sorted(trunc), "semantics": {"reachable_does_not_mean_exercised": True, "network_reachability_does_not_mean_authorization": True, "credential_presence_does_not_mean_universal_acceptance": True, "resource_action_does_not_imply_resource_control": True, "constraints_fail_closed": True, "delegation_preserves_capability_budget": True, "identity_hops_do_not_reset_delegated_capability_budget": True, "authority_identities_are_exact_evidence": True}}


def authority_blast_radius(store: TestamurAuthorityStore, compromised_refs: str | Sequence[str], *, compromise_model: str | CompromiseModel, capability_filter: Iterable[tuple[str, str]] | None = None, max_depth: int = 8, max_paths: int = 256, expansion_budget: int = 10000, as_of: str | datetime | None = None) -> dict[str, Any]:
    seeds = normalize_compromise_seeds(compromised_refs)
    results = [authority_reachability(store, ref, compromise_model=compromise_model, capability_filter=capability_filter, max_depth=max_depth, max_paths=max_paths, expansion_budget=expansion_budget, as_of=as_of) for ref in seeds]
    subjects: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    actions: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    blocked: list[dict[str, Any]] = []
    crossings: dict[tuple[str, str], dict[str, Any]] = {}
    trunc: set[str] = set()
    for result in results:
        for item in result["reachable_subjects"]:
            subject_ref = exact_subject_ref(item["subject_ref"], field="reachable_subject.subject_ref")
            subjects[(subject_ref, tuple(item.get("path_edge_ids") or []))] = item
        for item in result["actionable_capabilities"]:
            target_ref = exact_subject_ref(item["target_ref"], field="actionable_capability.target_ref")
            actions[(target_ref, capability_identity(item["capability"]), tuple(item.get("path_edge_ids") or []))] = item
        blocked.extend(result["blocked_transitions"])
        for crossing in result.get("trust_boundary_crossings") or []:
            crossings[(crossing["edge_id"], crossing["boundary_ref"])] = crossing
        trunc.update(result["truncation_reasons"])
    crossing_values = sorted(crossings.values(), key=lambda x: (x["edge_id"], x["boundary_ref"]))
    return {"schema_version": "testamur.authority-blast-radius.v1", "compromised_refs": seeds, "compromise_model": _normalize_model(compromise_model), "reachable_subjects": sorted(subjects.values(), key=lambda x: (int(x.get("depth") or 0), exact_subject_ref(x.get("subject_ref"), field="reachable_subject.subject_ref"), tuple(x.get("path_edge_ids") or []))), "actionable_capabilities": sorted(actions.values(), key=lambda x: (exact_subject_ref(x.get("target_ref"), field="actionable_capability.target_ref"), capability_identity(x["capability"]), tuple(x.get("path_edge_ids") or []))), "blocked_transitions": blocked, "trust_boundary_refs": boundary_refs_from_crossings(crossing_values), "trust_boundary_crossings": crossing_values, "truncated": bool(trunc), "truncation_reasons": sorted(trunc), "semantics": {"blast_radius_is_potential_authority_not_observed_malicious_use": True, "affectedness_does_not_automatically_seed_compromise": True, "material_lineage_does_not_grant_authority": True, "compromise_seeds_are_explicit_authority_assumptions": True, "authority_identities_are_exact_evidence": True}}


__all__ = ["CompromiseModel", "AuthorityReachabilityClass", "authority_reachability", "authority_blast_radius"]