from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping, Sequence

from .authority import (
    AuthorityRelationType,
    AuthoritySubjectKind,
    TestamurAuthorityStore,
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
    AuthorityRelationType.CAN_CONNECT.value,
    AuthorityRelationType.HAS_CAPABILITY.value,
}

_PROPAGATING_RELATIONS = {
    AuthorityRelationType.EXPOSES.value,
    AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
    AuthorityRelationType.CAN_IMPERSONATE.value,
    AuthorityRelationType.DELEGATES.value,
    AuthorityRelationType.CAN_EXECUTE.value,
}

_MODEL_RELATIONS: dict[str, frozenset[str]] = {
    CompromiseModel.READ_ONLY_COMPROMISE.value: frozenset(
        {
            AuthorityRelationType.CAN_READ.value,
            AuthorityRelationType.EXPOSES.value,
        }
    ),
    CompromiseModel.PROCESS_CODE_EXECUTION.value: frozenset(
        {
            AuthorityRelationType.CAN_READ.value,
            AuthorityRelationType.CAN_WRITE.value,
            AuthorityRelationType.CAN_EXECUTE.value,
            AuthorityRelationType.CAN_CONNECT.value,
            AuthorityRelationType.CAN_IMPERSONATE.value,
            AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
            AuthorityRelationType.DELEGATES.value,
            AuthorityRelationType.HAS_CAPABILITY.value,
            AuthorityRelationType.EXPOSES.value,
        }
    ),
    CompromiseModel.ACCOUNT_SESSION_TAKEOVER.value: frozenset(
        {
            AuthorityRelationType.CAN_READ.value,
            AuthorityRelationType.CAN_WRITE.value,
            AuthorityRelationType.CAN_CONNECT.value,
            AuthorityRelationType.CAN_IMPERSONATE.value,
            AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
            AuthorityRelationType.DELEGATES.value,
            AuthorityRelationType.HAS_CAPABILITY.value,
            AuthorityRelationType.EXPOSES.value,
        }
    ),
    CompromiseModel.CONNECTOR_TAKEOVER.value: frozenset(
        {
            AuthorityRelationType.CAN_READ.value,
            AuthorityRelationType.CAN_WRITE.value,
            AuthorityRelationType.CAN_CONNECT.value,
            AuthorityRelationType.CAN_EXECUTE.value,
            AuthorityRelationType.HAS_CAPABILITY.value,
            AuthorityRelationType.EXPOSES.value,
        }
    ),
    CompromiseModel.CREDENTIAL_THEFT.value: frozenset(
        {
            AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
            AuthorityRelationType.CAN_IMPERSONATE.value,
            AuthorityRelationType.DELEGATES.value,
            AuthorityRelationType.HAS_CAPABILITY.value,
        }
    ),
    CompromiseModel.FULL_SUBJECT_COMPROMISE.value: frozenset(
        item.value for item in AuthorityRelationType
    ),
}


def _normalize_model(value: str | CompromiseModel) -> str:
    try:
        return CompromiseModel(str(value)).value
    except ValueError as exc:
        allowed = ", ".join(item.value for item in CompromiseModel)
        raise ValueError(
            f"unsupported compromise model {value!r}; expected one of: {allowed}"
        ) from exc


def _parse_time(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_of(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("as_of must be an ISO timestamp or datetime")
    return _parse_time(value)


def _string_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        text = value.strip()
        return {text} if text else set()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {str(value).strip()} if str(value).strip() else set()


def _credential_attributes(
    store: TestamurAuthorityStore,
    subject_ref: str,
) -> dict[str, Any]:
    subject = store.maybe_subject(subject_ref)
    if subject is None:
        return {}
    attributes = subject.get("attributes")
    return dict(attributes) if isinstance(attributes, Mapping) else {}


def _edge_is_declared_only(edge: Mapping[str, Any]) -> bool:
    evidence = edge.get("evidence") or []
    if not evidence:
        return True
    classes = {
        str(item.get("evidence_class") or "")
        for item in evidence
        if isinstance(item, Mapping)
    }
    return bool(classes) and classes <= {"DECLARED"}


def _check_constraints(
    store: TestamurAuthorityStore,
    edge: Mapping[str, Any],
    *,
    at: datetime,
) -> tuple[bool, list[str], list[str]]:
    constraints = edge.get("constraints")
    constraints = dict(constraints) if isinstance(constraints, Mapping) else {}
    source_ref = str(edge.get("source_ref") or "")
    attributes = _credential_attributes(store, source_ref)
    reasons: list[str] = []
    unresolved: list[str] = []

    revoked = constraints.get("revoked")
    revocation_state = str(
        constraints.get("revocation_state")
        or attributes.get("revocation_state")
        or ""
    ).strip().lower()
    if revoked is True or revocation_state in {"revoked", "invalid", "disabled"}:
        reasons.append("credential_or_edge_revoked")

    expiry = constraints.get("expires_at") or attributes.get("expires_at")
    if expiry:
        try:
            if _parse_time(str(expiry)) <= at:
                reasons.append("credential_or_edge_expired")
        except (TypeError, ValueError):
            unresolved.append("expires_at")

    required_audience = _string_set(
        constraints.get("audience") or constraints.get("audiences")
    )
    if required_audience:
        actual_audience = _string_set(
            attributes.get("audience") or attributes.get("audiences")
        )
        if not actual_audience:
            unresolved.append("audience")
        elif not (required_audience & actual_audience):
            reasons.append("audience_mismatch")

    required_scope = _string_set(
        constraints.get("scope")
        or constraints.get("scopes")
        or constraints.get("required_scope")
        or constraints.get("required_scopes")
    )
    if required_scope:
        actual_scope = _string_set(attributes.get("scope") or attributes.get("scopes"))
        if not actual_scope:
            unresolved.append("scope")
        elif not required_scope <= actual_scope:
            reasons.append("scope_mismatch")

    if constraints.get("approval_required") is True:
        reasons.append("approval_required")
    if constraints.get("human_confirmation_required") is True:
        reasons.append("human_confirmation_required")
    if constraints.get("mfa_required") is True:
        reasons.append("mfa_required")

    evaluated = {
        "revoked",
        "revocation_state",
        "expires_at",
        "audience",
        "audiences",
        "scope",
        "scopes",
        "required_scope",
        "required_scopes",
        "approval_required",
        "human_confirmation_required",
        "mfa_required",
        "resource",
        "resource_pattern",
        "principal",
    }
    for key, raw in constraints.items():
        if key in evaluated:
            continue
        if raw not in (None, False, "", [], {}, ()):
            unresolved.append(str(key))

    return not reasons and not unresolved, sorted(set(reasons)), sorted(set(unresolved))


def _implicit_capability(edge: Mapping[str, Any]) -> dict[str, Any] | None:
    relation = str(edge.get("relation_type") or "")
    action = {
        AuthorityRelationType.CAN_READ.value: "read",
        AuthorityRelationType.CAN_WRITE.value: "write",
        AuthorityRelationType.CAN_EXECUTE.value: "execute",
        AuthorityRelationType.CAN_CONNECT.value: "connect",
    }.get(relation)
    if action is None:
        return None
    return {
        "namespace": "testamur",
        "action": action,
        "resource": str(edge.get("target_ref") or ""),
        "constraints": {},
    }


def _capability_key(capability: Mapping[str, Any]) -> tuple[str, str, str | None]:
    return (
        str(capability.get("namespace") or ""),
        str(capability.get("action") or ""),
        None
        if capability.get("resource") is None
        else str(capability.get("resource")),
    )


def _capability_allowed_by_budget(
    capability: Mapping[str, Any],
    budget: tuple[tuple[str, str, str | None], ...] | None,
) -> bool:
    if budget is None:
        return True
    namespace, action, resource = _capability_key(capability)
    for b_namespace, b_action, b_resource in budget:
        if namespace != b_namespace or action != b_action:
            continue
        if b_resource is None or b_resource == resource:
            return True
    return False


def _edge_capabilities(
    edge: Mapping[str, Any],
    *,
    budget: tuple[tuple[str, str, str | None], ...] | None,
) -> list[dict[str, Any]]:
    raw = [
        dict(item)
        for item in edge.get("capabilities") or []
        if isinstance(item, Mapping)
    ]
    implicit = _implicit_capability(edge)
    if implicit is not None and not raw:
        raw.append(implicit)
    return [
        item for item in raw if _capability_allowed_by_budget(item, budget)
    ]


def _delegation_budget(
    edge: Mapping[str, Any],
    inherited: tuple[tuple[str, str, str | None], ...] | None,
) -> tuple[tuple[str, str, str | None], ...] | None:
    capabilities = [
        dict(item)
        for item in edge.get("capabilities") or []
        if isinstance(item, Mapping)
    ]
    if not capabilities:
        return () if str(edge.get("relation_type")) == AuthorityRelationType.DELEGATES.value else inherited
    keys = tuple(
        sorted(
            {_capability_key(item) for item in capabilities},
            key=lambda item: (item[0], item[1], "" if item[2] is None else item[2]),
        )
    )
    if inherited is None:
        return keys
    result = tuple(
        item
        for item in keys
        if any(
            item[0] == old[0]
            and item[1] == old[1]
            and (old[2] is None or old[2] == item[2])
            for old in inherited
        )
    )
    return result


def _subject_kind(
    store: TestamurAuthorityStore,
    subject_ref: str,
) -> str:
    subject = store.maybe_subject(subject_ref)
    return (
        AuthoritySubjectKind.OTHER.value
        if subject is None
        else str(subject.get("kind") or AuthoritySubjectKind.OTHER.value)
    )


def _path_evidence_state(
    declared_only_edge_seen: bool,
) -> str:
    return "CONTAINS_DECLARED_ONLY_EDGE" if declared_only_edge_seen else "CORROBORATED"


def authority_reachability(
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
    """Compute bounded evidence-backed authority reachability.

    This is deliberately not generic transitive closure. Only relation classes
    explicitly allowed by the compromise model are exercised, constraints fail
    closed, and resource actions do not imply control of the resource.
    """

    start = str(starting_subject_ref or "").strip()
    if not start:
        raise ValueError("starting_subject_ref must not be empty")
    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")
    if max_paths < 1:
        raise ValueError("max_paths must be >= 1")
    if expansion_budget < 1:
        raise ValueError("expansion_budget must be >= 1")

    model = _normalize_model(compromise_model)
    allowed_relations = _MODEL_RELATIONS[model]
    at = _as_of(as_of)
    filter_set = None if capability_filter is None else {
        (str(namespace), str(action)) for namespace, action in capability_filter
    }

    queue = deque(
        [
            {
                "subject_ref": start,
                "depth": 0,
                "edge_ids": [],
                "visited_refs": (start,),
                "budget": None,
                "declared_only_edge_seen": False,
                "reachability_class": AuthorityReachabilityClass.CONTROLLED.value,
            }
        ]
    )

    reachable: list[dict[str, Any]] = [
        {
            "subject_ref": start,
            "kind": _subject_kind(store, start),
            "reachability_class": AuthorityReachabilityClass.CONTROLLED.value,
            "depth": 0,
            "path_edge_ids": [],
            "boundary_refs": [],
            "evidence_state": "SEED_ASSUMPTION",
        }
    ]
    actions: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    paths_emitted = 1
    expansions = 0
    truncation_reasons: set[str] = set()
    seen_result_keys: set[tuple[Any, ...]] = {
        (start, AuthorityReachabilityClass.CONTROLLED.value, ())
    }

    while queue:
        current = queue.popleft()
        subject_ref = str(current["subject_ref"])
        depth = int(current["depth"])
        if depth >= max_depth:
            if store.edges_from(subject_ref):
                truncation_reasons.add("max_depth")
            continue

        for edge in store.edges_from(subject_ref):
            expansions += 1
            if expansions > expansion_budget:
                truncation_reasons.add("expansion_budget")
                queue.clear()
                break

            relation = str(edge["relation_type"])
            if relation not in allowed_relations:
                continue

            target_ref = str(edge["target_ref"])
            edge_id = str(edge["edge_id"])
            next_path = [*current["edge_ids"], edge_id]
            boundaries = sorted(
                {
                    boundary
                    for path_edge_id in next_path
                    for boundary in (
                        store.get_edge(path_edge_id).get("boundary_refs") or []
                    )
                }
            )
            ok, reasons, unresolved = _check_constraints(store, edge, at=at)
            declared_only_seen = bool(current["declared_only_edge_seen"]) or _edge_is_declared_only(edge)

            if not ok:
                blocked.append(
                    {
                        "edge_id": edge_id,
                        "source_ref": subject_ref,
                        "target_ref": target_ref,
                        "relation_type": relation,
                        "path_edge_ids": next_path,
                        "reasons": reasons,
                        "unresolved_constraints": unresolved,
                        "reachability_class": (
                            AuthorityReachabilityClass.CONDITIONALLY_ACTIONABLE.value
                            if reasons and set(reasons)
                            <= {
                                "approval_required",
                                "human_confirmation_required",
                                "mfa_required",
                            }
                            else AuthorityReachabilityClass.BLOCKED.value
                        ),
                        "evidence_state": _path_evidence_state(declared_only_seen),
                    }
                )
                continue

            budget = current["budget"]
            capabilities = _edge_capabilities(edge, budget=budget)
            if filter_set is not None:
                capabilities = [
                    capability
                    for capability in capabilities
                    if (
                        str(capability.get("namespace") or ""),
                        str(capability.get("action") or ""),
                    )
                    in filter_set
                ]

            if relation in _ACTION_RELATIONS:
                if relation == AuthorityRelationType.HAS_CAPABILITY.value and not capabilities:
                    blocked.append(
                        {
                            "edge_id": edge_id,
                            "source_ref": subject_ref,
                            "target_ref": target_ref,
                            "relation_type": relation,
                            "path_edge_ids": next_path,
                            "reasons": ["missing_explicit_capability"],
                            "unresolved_constraints": [],
                            "reachability_class": AuthorityReachabilityClass.UNKNOWN.value,
                            "evidence_state": _path_evidence_state(declared_only_seen),
                        }
                    )
                else:
                    for capability in capabilities:
                        action_key = (
                            target_ref,
                            *_capability_key(capability),
                            tuple(next_path),
                        )
                        if action_key in seen_result_keys:
                            continue
                        seen_result_keys.add(action_key)
                        actions.append(
                            {
                                "source_ref": subject_ref,
                                "target_ref": target_ref,
                                "relation_type": relation,
                                "capability": capability,
                                "reachability_class": AuthorityReachabilityClass.ACTIONABLE.value,
                                "depth": depth + 1,
                                "path_edge_ids": next_path,
                                "boundary_refs": boundaries,
                                "evidence_state": _path_evidence_state(declared_only_seen),
                            }
                        )
                        paths_emitted += 1
                        if paths_emitted >= max_paths:
                            truncation_reasons.add("max_paths")
                            queue.clear()
                            break
                    if "max_paths" in truncation_reasons:
                        break

            should_propagate = relation in _PROPAGATING_RELATIONS
            target_kind = _subject_kind(store, target_ref)
            next_class = AuthorityReachabilityClass.CONTROLLED.value
            next_budget = budget

            if relation == AuthorityRelationType.CAN_READ.value and target_kind in _CREDENTIAL_KINDS:
                should_propagate = True
                next_class = AuthorityReachabilityClass.CREDENTIAL_ACQUIRED.value
                next_budget = None
            elif relation == AuthorityRelationType.EXPOSES.value:
                next_class = (
                    AuthorityReachabilityClass.CREDENTIAL_ACQUIRED.value
                    if target_kind in _CREDENTIAL_KINDS
                    else AuthorityReachabilityClass.CONTROLLED.value
                )
                next_budget = None
            elif relation == AuthorityRelationType.DELEGATES.value:
                next_budget = _delegation_budget(edge, budget)
                if next_budget == ():
                    blocked.append(
                        {
                            "edge_id": edge_id,
                            "source_ref": subject_ref,
                            "target_ref": target_ref,
                            "relation_type": relation,
                            "path_edge_ids": next_path,
                            "reasons": ["missing_or_empty_delegated_capability_set"],
                            "unresolved_constraints": [],
                            "reachability_class": AuthorityReachabilityClass.UNKNOWN.value,
                            "evidence_state": _path_evidence_state(declared_only_seen),
                        }
                    )
                    should_propagate = False
            elif relation in {
                AuthorityRelationType.CAN_AUTHENTICATE_AS.value,
                AuthorityRelationType.CAN_IMPERSONATE.value,
            }:
                next_budget = _delegation_budget(edge, None)

            if not should_propagate:
                continue
            if target_ref in current["visited_refs"]:
                continue

            result_key = (target_ref, next_class, tuple(next_path))
            if result_key not in seen_result_keys:
                seen_result_keys.add(result_key)
                reachable.append(
                    {
                        "subject_ref": target_ref,
                        "kind": target_kind,
                        "reachability_class": next_class,
                        "depth": depth + 1,
                        "path_edge_ids": next_path,
                        "boundary_refs": boundaries,
                        "evidence_state": _path_evidence_state(declared_only_seen),
                        "delegated_capability_budget": (
                            None
                            if next_budget is None
                            else [
                                {
                                    "namespace": item[0],
                                    "action": item[1],
                                    "resource": item[2],
                                }
                                for item in next_budget
                            ]
                        ),
                    }
                )
                paths_emitted += 1
                if paths_emitted >= max_paths:
                    truncation_reasons.add("max_paths")
                    queue.clear()
                    break

            queue.append(
                {
                    "subject_ref": target_ref,
                    "depth": depth + 1,
                    "edge_ids": next_path,
                    "visited_refs": (*current["visited_refs"], target_ref),
                    "budget": next_budget,
                    "declared_only_edge_seen": declared_only_seen,
                    "reachability_class": next_class,
                }
            )

        if "expansion_budget" in truncation_reasons or "max_paths" in truncation_reasons:
            break

    actionable_by_target: dict[str, list[dict[str, Any]]] = {}
    for action in actions:
        actionable_by_target.setdefault(str(action["target_ref"]), []).append(action)
    for target in actionable_by_target:
        actionable_by_target[target].sort(
            key=lambda item: (
                str(item["capability"].get("namespace") or ""),
                str(item["capability"].get("action") or ""),
                str(item["capability"].get("resource") or ""),
                tuple(item["path_edge_ids"]),
            )
        )

    all_boundaries = sorted(
        {
            boundary
            for item in [*reachable, *actions]
            for boundary in item.get("boundary_refs") or []
        }
    )

    return {
        "schema_version": "testamur.authority-reachability.v1",
        "starting_subject_ref": start,
        "compromise_model": model,
        "as_of": at.isoformat().replace("+00:00", "Z"),
        "reachable_subjects": reachable,
        "actionable_capabilities": actions,
        "actionable_by_target": actionable_by_target,
        "blocked_transitions": blocked,
        "trust_boundary_refs": all_boundaries,
        "expansions": expansions,
        "truncated": bool(truncation_reasons),
        "truncation_reasons": sorted(truncation_reasons),
        "semantics": {
            "reachable_does_not_mean_exercised": True,
            "network_reachability_does_not_mean_authorization": True,
            "credential_presence_does_not_mean_universal_acceptance": True,
            "resource_action_does_not_imply_resource_control": True,
            "constraints_fail_closed": True,
            "delegation_preserves_capability_budget": True,
        },
    }


def authority_blast_radius(
    store: TestamurAuthorityStore,
    compromised_refs: str | Sequence[str],
    *,
    compromise_model: str | CompromiseModel,
    capability_filter: Iterable[tuple[str, str]] | None = None,
    max_depth: int = 8,
    max_paths: int = 256,
    expansion_budget: int = 10000,
    as_of: str | datetime | None = None,
) -> dict[str, Any]:
    refs = [compromised_refs] if isinstance(compromised_refs, str) else list(compromised_refs)
    seeds = sorted({str(ref).strip() for ref in refs if str(ref).strip()})
    if not seeds:
        raise ValueError("compromised_refs must contain at least one subject ref")

    results = [
        authority_reachability(
            store,
            ref,
            compromise_model=compromise_model,
            capability_filter=capability_filter,
            max_depth=max_depth,
            max_paths=max_paths,
            expansion_budget=expansion_budget,
            as_of=as_of,
        )
        for ref in seeds
    ]

    subjects: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    actions: dict[
        tuple[str, str, str, str | None, tuple[str, ...]], dict[str, Any]
    ] = {}
    blocked: list[dict[str, Any]] = []
    boundaries: set[str] = set()
    truncation_reasons: set[str] = set()

    for result in results:
        for item in result["reachable_subjects"]:
            key = (str(item["subject_ref"]), tuple(item.get("path_edge_ids") or []))
            subjects[key] = item
        for item in result["actionable_capabilities"]:
            capability = item["capability"]
            key = (
                str(item["target_ref"]),
                str(capability.get("namespace") or ""),
                str(capability.get("action") or ""),
                None if capability.get("resource") is None else str(capability.get("resource")),
                tuple(item.get("path_edge_ids") or []),
            )
            actions[key] = item
        blocked.extend(result["blocked_transitions"])
        boundaries.update(result["trust_boundary_refs"])
        truncation_reasons.update(result["truncation_reasons"])

    return {
        "schema_version": "testamur.authority-blast-radius.v1",
        "compromised_refs": seeds,
        "compromise_model": _normalize_model(compromise_model),
        "reachable_subjects": sorted(
            subjects.values(),
            key=lambda item: (
                int(item.get("depth") or 0),
                str(item.get("subject_ref") or ""),
                tuple(item.get("path_edge_ids") or []),
            ),
        ),
        "actionable_capabilities": sorted(
            actions.values(),
            key=lambda item: (
                str(item.get("target_ref") or ""),
                str(item["capability"].get("namespace") or ""),
                str(item["capability"].get("action") or ""),
                str(item["capability"].get("resource") or ""),
                tuple(item.get("path_edge_ids") or []),
            ),
        ),
        "blocked_transitions": blocked,
        "trust_boundary_refs": sorted(boundaries),
        "truncated": bool(truncation_reasons),
        "truncation_reasons": sorted(truncation_reasons),
        "semantics": {
            "blast_radius_is_potential_authority_not_observed_malicious_use": True,
            "affectedness_does_not_automatically_seed_compromise": True,
        },
    }


__all__ = [
    "CompromiseModel",
    "AuthorityReachabilityClass",
    "authority_reachability",
    "authority_blast_radius",
]
