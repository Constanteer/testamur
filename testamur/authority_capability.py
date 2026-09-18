from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


CapabilityBudget = tuple[dict[str, Any], ...]


def _constraints(value: Mapping[str, Any]) -> dict[str, Any]:
    raw = value.get("constraints")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {value} if value else set()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return {str(item) for item in value if str(item)}
    return {str(value)}


def _constraint_set(constraints: Mapping[str, Any], *aliases: str) -> set[str]:
    """Read synonymous set-valued constraints without treating spelling as authority.

    Providers commonly project `scope` vs `scopes` and `audience` vs `audiences`.
    They are semantic aliases, not independent gates. If more than one spelling is
    present we conservatively union the values; attenuation still requires the child
    set to be a non-empty subset of the parent's effective set.
    """
    result: set[str] = set()
    for key in aliases:
        result.update(_set(constraints.get(key)))
    return result


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
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _resource_within(child: str | None, parent: str | None, parent_pattern: str | None) -> bool:
    if parent_pattern:
        return child is not None and fnmatch.fnmatchcase(child, parent_pattern)
    if parent is None:
        return True
    return child == parent


def capability_is_attenuation(child: Mapping[str, Any], parent: Mapping[str, Any]) -> bool:
    """Return True only when child cannot exercise more authority than parent.

    This is deliberately fail-closed. Namespace/action must be identical. Set-valued
    identity/scope constraints may narrow, boolean gates may be added but never
    removed, expiry may move earlier but never later, and unknown non-empty provider
    constraints must be preserved exactly. A parent resource pattern may be
    instantiated to a matching concrete resource; pattern-to-pattern reasoning is not
    guessed and therefore requires exact preservation.
    """
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

    set_aliases = (
        ("scope", "scopes"),
        ("audience", "audiences"),
        ("principal", "principals"),
        ("service_ref", "service_refs"),
        ("network_zone", "network_zones"),
        ("source_ip", "source_ips"),
        ("device_binding", "device_bindings"),
        ("session_binding", "session_bindings"),
    )
    gate_keys = {"approval_required", "human_confirmation_required", "mfa_required"}
    handled = {alias for group in set_aliases for alias in group} | gate_keys | {
        "resource_pattern", "expires_at"
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
        # Invalid/unknown expiry cannot establish attenuation.
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
    """Intersect a delegated capability set with its inherited authority budget."""
    candidates = [dict(item) for item in capabilities]
    if inherited is None:
        result = candidates
    else:
        result = [
            item
            for item in candidates
            if any(capability_is_attenuation(item, parent) for parent in inherited)
        ]
    result.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return tuple(result)


def capability_allowed(capability: Mapping[str, Any], budget: CapabilityBudget | None) -> bool:
    return budget is None or any(
        capability_is_attenuation(capability, parent) for parent in budget
    )


def project_budget(budget: CapabilityBudget | None) -> list[dict[str, Any]] | None:
    """Stable JSON projection for reachability/CLI/ProductService/Web surfaces."""
    if budget is None:
        return None
    return [dict(item) for item in budget]


__all__ = [
    "CapabilityBudget",
    "capability_is_attenuation",
    "attenuate_budget",
    "capability_allowed",
    "project_budget",
]
