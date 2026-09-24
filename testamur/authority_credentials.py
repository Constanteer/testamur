from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _explicit_string_set(value: Any) -> tuple[set[str], bool]:
    """Return explicit string claims and whether their representation is valid."""
    if isinstance(value, str):
        text = value.strip()
        return ({text}, True) if text else (set(), False)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        if not value:
            return set(), False
        result: set[str] = set()
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return set(), False
            result.add(item.strip())
        return result, bool(result)
    return set(), False


def _alias_values(source: Mapping[str, Any], aliases: tuple[str, ...]) -> tuple[set[str], bool, bool]:
    """Read alternate encodings of one logical claim without unioning grants."""
    observed: list[set[str]] = []
    for key in aliases:
        if key not in source or source.get(key) is None:
            continue
        values, valid = _explicit_string_set(source.get(key))
        if not valid:
            return set(), True, False
        observed.append(values)
    if not observed:
        return set(), False, True
    first = observed[0]
    if any(values != first for values in observed[1:]):
        return set(), True, False
    return set(first), True, True


def _time(value: Any) -> datetime | None:
    """Parse an explicitly zoned credential timestamp without coercion."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _at_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("authority credential observation instant requires an explicit timezone")
    return value.astimezone(timezone.utc)


def _explicit_state(value: Any) -> tuple[str, bool]:
    if value is None:
        return "", True
    if not isinstance(value, str) or not value.strip():
        return "", False
    return value.strip().lower(), True


def _first_present(source: Mapping[str, Any], aliases: tuple[str, ...]) -> tuple[Any, bool]:
    """Return the first explicitly present claim, preserving malformed evidence.

    Authority constraints must not use Python truthiness as precedence. An explicit
    false/zero/empty/typed value is evidence that must be validated and fail closed;
    it must never disappear merely because a fallback attribute looks valid.
    """
    for key in aliases:
        if key in source:
            return source.get(key), True
    return None, False


def _explicit_bool(source: Mapping[str, Any], key: str) -> tuple[bool | None, bool, bool]:
    """Read a boolean authority claim without truthiness or scalar coercion."""
    if key not in source:
        return None, False, True
    value = source.get(key)
    if type(value) is not bool:
        return None, True, False
    return value, True, True


def credential_constraints_satisfied(
    attributes: Mapping[str, Any],
    constraints: Mapping[str, Any],
    *,
    as_of: datetime,
) -> tuple[bool, list[str], list[str]]:
    """Evaluate explicit credential requirements without creating authority.

    This only evaluates metadata on an already-explicit authority/acceptance
    edge. It never infers CAN_AUTHENTICATE_AS or ACCEPTS_CREDENTIAL. Claim aliases
    are alternate encodings, not additive grants: malformed or conflicting
    audience/scope/issuer/tenant/resource-selection evidence remains unresolved
    and fails closed. Graph-bound constraints such as service_ref are deliberately
    left unresolved for the exact-edge graph-context evaluator; they are never
    decorative metadata.
    """
    reasons: set[str] = set()
    unresolved: set[str] = set()
    at = _at_utc(as_of)

    # Boolean authority state is exact evidence. Strings such as "false", integers,
    # mappings, and nulls must not be interpreted through Python truthiness or be
    # silently ignored. Edge and credential state are independent restrictions:
    # either one may revoke/deactivate, while neither may grant authority.
    for source in (constraints, attributes):
        revoked, revoked_present, revoked_valid = _explicit_bool(source, "revoked")
        if revoked_present and not revoked_valid:
            unresolved.add("revoked")
        elif revoked is True:
            reasons.add("credential_or_edge_revoked")

        active, active_present, active_valid = _explicit_bool(source, "active")
        if active_present and not active_valid:
            unresolved.add("active")
        elif active is False:
            reasons.add("credential_or_edge_inactive")

    revocation_raw, revocation_present = _first_present(constraints, ("revocation_state",))
    if not revocation_present:
        revocation_raw, revocation_present = _first_present(attributes, ("revocation_state",))
    if revocation_present:
        revocation_state, revocation_valid = _explicit_state(revocation_raw)
        if not revocation_valid or not revocation_state:
            unresolved.add("revocation_state")
        elif revocation_state in {"revoked", "invalid", "disabled"}:
            reasons.add("credential_or_edge_revoked")

    expiry_raw, expiry_present = _first_present(constraints, ("expires_at",))
    if not expiry_present:
        expiry_raw, expiry_present = _first_present(attributes, ("expires_at",))
    if expiry_present:
        expiry = _time(expiry_raw)
        if expiry is None:
            unresolved.add("expires_at")
        elif expiry <= at:
            reasons.add("credential_or_edge_expired")

    not_before_raw, not_before_present = _first_present(constraints, ("not_before", "nbf"))
    if not not_before_present:
        not_before_raw, not_before_present = _first_present(attributes, ("not_before", "nbf"))
    if not_before_present:
        not_before = _time(not_before_raw)
        if not_before is None:
            unresolved.add("not_before")
        elif at < not_before:
            reasons.add("credential_or_edge_not_yet_valid")

    families = (
        (("audience", "audiences", "required_audience", "required_audiences"), ("audience", "audiences"), "audience", False),
        (("scope", "scopes", "required_scope", "required_scopes"), ("scope", "scopes"), "scope", True),
        (("issuer", "issuers", "required_issuer", "required_issuers"), ("issuer", "issuers"), "issuer", False),
        (("tenant", "tenants", "tenant_id", "tenant_ids"), ("tenant", "tenants", "tenant_id", "tenant_ids"), "tenant", False),
        (("repository_selection", "required_repository_selection", "required_repositories"), ("repository_selection", "repositories", "repository_refs"), "repository_selection", True),
    )
    handled: set[str] = {
        "revoked", "revocation_state", "active", "expires_at", "not_before", "nbf",
        "approval_required", "human_confirmation_required", "mfa_required",
    }
    for required_aliases, actual_aliases, label, require_subset in families:
        handled.update(required_aliases)
        required, required_present, required_valid = _alias_values(constraints, required_aliases)
        if required_present and not required_valid:
            unresolved.add(label)
            continue
        if not required_present:
            continue
        actual, actual_present, actual_valid = _alias_values(attributes, actual_aliases)
        if not actual_present or not actual_valid:
            unresolved.add(label)
        elif require_subset:
            if not required <= actual:
                reasons.add(f"{label}_mismatch")
        elif not required.intersection(actual):
            reasons.add(f"{label}_mismatch")

    for gate in ("approval_required", "human_confirmation_required", "mfa_required"):
        if constraints.get(gate) is True:
            reasons.add(gate)

    for key, value in constraints.items():
        if key in handled:
            continue
        if value not in (None, False, "", [], {}, ()):
            if not isinstance(key, str) or not key.strip():
                raise ValueError("authority constraint keys must be exact non-empty strings")
            unresolved.add(key.strip())

    return not reasons and not unresolved, sorted(reasons), sorted(unresolved)


__all__ = ["credential_constraints_satisfied"]
