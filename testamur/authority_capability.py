from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


CapabilityBudget = tuple[dict[str, Any], ...]

_NO_IMPLICIT_CAPABILITY_RELATIONS = frozenset({
    "CAN_CONNECT",
    "HAS_CAPABILITY",
    "DELEGATES",
    "ACCEPTS_CREDENTIAL",
})


def _constraints(value: Mapping[str, Any]) -> dict[str, Any]:
    raw = value.get("constraints")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _well_formed(capability: Mapping[str, Any]) -> bool:
    """Reject malformed authority observations instead of treating them as wildcards."""
    namespace = capability.get("namespace")
    action = capability.get("action")
    if not (
        isinstance(namespace, str)
        and bool(namespace.strip())
        and isinstance(action, str)
        and bool(action.strip())
    ):
        return False

    if "resource" in capability:
        resource = capability.get("resource")
        if resource is not None and (not isinstance(resource, str) or not resource.strip()):
            return False

    raw_constraints = capability.get("constraints")
    if raw_constraints is not None and not isinstance(raw_constraints, Mapping):
        return False
    constraints = _constraints(capability)

    if "expires_at" in constraints and _parse_time(constraints.get("expires_at")) is None:
        return False

    for key in ("approval_required", "human_confirmation_required", "mfa_required"):
        if key in constraints and not isinstance(constraints[key], bool):
            return False

    selection = constraints.get("repository_selection")
    if selection is not None:
        if selection not in {"all", "selected", "unresolved"}:
            return False
        refs = _constraint_set(constraints, "repository_ref", "repository_refs")
        if selection == "selected" and not refs:
            return False
        if selection in {"all", "unresolved"} and refs:
            return False

    return True


def _set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return {str(item) for item in value if str(item)}
    return {str(value)}


def _constraint_set(constraints: Mapping[str, Any], *aliases: str) -> set[str]:
    result: set[str] = set()
    for key in aliases:
        result.update(_set(constraints.get(key)))
    return result


def _resource_within(child: str | None, parent: str | None, parent_pattern: str | None) -> bool:
    if parent_pattern:
        return child is not None and fnmatch.fnmatchcase(child, parent_pattern)
    if parent is None:
        return True
    return child == parent


def _repository_scope_is_attenuation(
    child_constraints: Mapping[str, Any], parent_constraints: Mapping[str, Any]
) -> bool:
    """Compare provider repository-selection scope without turning absence into `all`.

    `unresolved` is deliberately not an authority wildcard. It may only remain
    unresolved downstream; any operation that names a repository must first have an
    exact selected set or an explicit provider observation of `all` repositories.
    """
    parent_selection = parent_constraints.get("repository_selection")
    if parent_selection is None:
        return True

    child_selection = child_constraints.get("repository_selection")
    parent_refs = _constraint_set(parent_constraints, "repository_ref", "repository_refs")
    child_refs = _constraint_set(child_constraints, "repository_ref", "repository_refs")

    if parent_selection == "unresolved":
        return child_selection == "unresolved" and not child_refs
    if parent_selection == "selected":
        return child_selection == "selected" and bool(child_refs) and child_refs <= parent_refs
    if parent_selection == "all":
        if child_selection == "all":
            return not child_refs
        if child_selection == "selected":
            return bool(child_refs)
        return False
    return False


def capability_is_attenuation(child: Mapping[str, Any], parent: Mapping[str, Any]) -> bool:
    """Return True only when child cannot exercise more authority than parent."""
    if not _well_formed(child) or not _well_formed(parent):
        return False
    if str(child.get("namespace") or "") != str(parent.get("namespace") or ""):
        return False
    if str(child.get("action") or "") != str(parent.get("action") or ""):
        return False

    pc = _constraints(parent)
    cc = _constraints(child)
    if not _resource_within(
        None if child.get("resource") is None else str(child.get("resource")),
        None if parent.get("resource") is None else str(parent.get("resource")),
        None if pc.get("resource_pattern") is None else str(pc.get("resource_pattern")),
    ):
        return False

    if not _repository_scope_is_attenuation(cc, pc):
        return False

    set_aliases = (
        ("scope", "scopes", "required_scope", "required_scopes"),
        ("audience", "audiences", "required_audience", "required_audiences"),
        ("principal", "principals"),
        ("service_ref", "service_refs"),
        ("network_zone", "network_zones"),
        ("source_ip", "source_ips"),
        ("device_binding", "device_bindings"),
        ("session_binding", "session_bindings"),
        ("issuer", "issuers", "required_issuer", "required_issuers"),
        ("tenant", "tenants", "tenant_id", "tenant_ids"),
    )
    gate_keys = {"approval_required", "human_confirmation_required", "mfa_required"}
    handled = {alias for group in set_aliases for alias in group} | gate_keys | {
        "resource_pattern", "expires_at", "repository_selection", "repository_ref", "repository_refs"
    }

    for aliases in set_aliases:
        parent_values = _constraint_set(pc, *aliases)
        if not parent_values:
            continue
        child_values = _constraint_set(cc, *aliases)
        if not child_values or not child_values <= parent_values:
            return False

    for key in gate_keys:
        if pc.get(key) is True and cc.get(key) is not True:
            return False

    if pc.get("expires_at") is not None:
        parent_expiry = _parse_time(pc.get("expires_at"))
        child_expiry = _parse_time(cc.get("expires_at"))
        if parent_expiry is None or child_expiry is None or child_expiry > parent_expiry:
            return False

    if pc.get("resource_pattern") is not None:
        child_resource = child.get("resource")
        child_pattern = cc.get("resource_pattern")
        if child_resource is None and child_pattern != pc.get("resource_pattern"):
            return False

    for key, value in pc.items():
        if key in handled or value in (None, False, "", [], {}, ()):
            continue
        if key not in cc or cc[key] != value:
            return False
    return True


def attenuate_budget(capabilities: Sequence[Mapping[str, Any]], inherited: CapabilityBudget | None) -> CapabilityBudget:
    candidates = [dict(item) for item in capabilities if _well_formed(item)]
    if inherited is None:
        result = candidates
    else:
        valid_inherited = tuple(item for item in inherited if _well_formed(item))
        result = [
            item
            for item in candidates
            if any(capability_is_attenuation(item, parent) for parent in valid_inherited)
        ]
    result.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return tuple(result)


def capability_allowed(capability: Mapping[str, Any], budget: CapabilityBudget | None) -> bool:
    if not _well_formed(capability):
        return False
    return budget is None or any(
        capability_is_attenuation(capability, parent) for parent in budget
    )


def edge_capabilities(
    edge: Mapping[str, Any],
    *,
    budget: CapabilityBudget | None,
    implicit_capability: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Project only capabilities exercisable within an inherited delegation budget."""
    raw = [
        dict(item)
        for item in edge.get("capabilities") or []
        if isinstance(item, Mapping) and _well_formed(item)
    ]
    relation = str(edge.get("relation_type") or "")
    if (
        not raw
        and implicit_capability is not None
        and _well_formed(implicit_capability)
        and relation not in _NO_IMPLICIT_CAPABILITY_RELATIONS
    ):
        raw.append(dict(implicit_capability))
    return [item for item in raw if capability_allowed(item, budget)]


def delegation_budget(
    edge: Mapping[str, Any],
    inherited: CapabilityBudget | None,
    *,
    delegation_relation: str = "DELEGATES",
) -> CapabilityBudget | None:
    """Return the effective downstream budget for an authority edge."""
    capabilities = [
        dict(item)
        for item in edge.get("capabilities") or []
        if isinstance(item, Mapping) and _well_formed(item)
    ]
    if not capabilities:
        return () if str(edge.get("relation_type") or "") == delegation_relation else inherited
    return attenuate_budget(capabilities, inherited)


def project_budget(budget: CapabilityBudget | None) -> list[dict[str, Any]] | None:
    if budget is None:
        return None
    return [dict(item) for item in budget if _well_formed(item)]


__all__ = [
    "CapabilityBudget",
    "capability_is_attenuation",
    "attenuate_budget",
    "capability_allowed",
    "edge_capabilities",
    "delegation_budget",
    "project_budget",
]
