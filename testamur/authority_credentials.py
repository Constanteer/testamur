from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


def _set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        value = value.strip()
        return {value} if value else set()
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return {str(item).strip() for item in value if str(item).strip()}
    text = str(value).strip()
    return {text} if text else set()


def _values(source: Mapping[str, Any], aliases: tuple[str, ...]) -> set[str]:
    result: set[str] = set()
    for key in aliases:
        result.update(_set(source.get(key)))
    return result


def _time(value: Any) -> datetime | None:
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


def _at_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def credential_constraints_satisfied(
    attributes: Mapping[str, Any],
    constraints: Mapping[str, Any],
    *,
    as_of: datetime,
) -> tuple[bool, list[str], list[str]]:
    """Evaluate explicit credential requirements without creating authority.

    This function only answers whether observed credential metadata satisfies an
    already-explicit authority/acceptance edge. It must never be used to infer
    CAN_AUTHENTICATE_AS or ACCEPTS_CREDENTIAL from matching metadata alone.
    Unknown non-empty constraints fail closed.

    Constraints that need graph context (for example resource/principal matching)
    are intentionally *not* marked handled here. Until a caller evaluates them
    against an exact graph subject they remain unresolved rather than silently
    disappearing from the authority decision.
    """
    reasons: set[str] = set()
    unresolved: set[str] = set()
    at = _at_utc(as_of)

    revoked = constraints.get("revoked")
    revocation_state = str(
        constraints.get("revocation_state")
        or attributes.get("revocation_state")
        or ""
    ).strip().lower()
    if revoked is True or revocation_state in {"revoked", "invalid", "disabled"}:
        reasons.add("credential_or_edge_revoked")

    # Provider observations frequently expose an explicit active/disabled bit.
    # Only an explicit False blocks; absence is not silently interpreted as proof
    # of validity because the authority edge itself remains the authorization fact.
    if constraints.get("active") is False or attributes.get("active") is False:
        reasons.add("credential_or_edge_inactive")

    expiry_raw = constraints.get("expires_at") or attributes.get("expires_at")
    if expiry_raw is not None:
        expiry = _time(expiry_raw)
        if expiry is None:
            unresolved.add("expires_at")
        elif expiry <= at:
            reasons.add("credential_or_edge_expired")

    # nbf/not_before is a validity boundary, not lineage. A credential observed
    # before that instant exists, but is not yet exercisable authority.
    not_before_raw = (
        constraints.get("not_before")
        or constraints.get("nbf")
        or attributes.get("not_before")
        or attributes.get("nbf")
    )
    if not_before_raw is not None:
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
    )
    handled: set[str] = {
        "revoked", "revocation_state", "active", "expires_at", "not_before", "nbf",
        "approval_required", "human_confirmation_required", "mfa_required",
        # service_ref is graph-routing metadata consumed by reachability's exact
        # ACCEPTS_CREDENTIAL lookup; it is not a credential claim by itself.
        "service_ref", "service_refs",
    }
    for required_aliases, actual_aliases, label, require_subset in families:
        handled.update(required_aliases)
        required = _values(constraints, required_aliases)
        if not required:
            continue
        actual = _values(attributes, actual_aliases)
        if not actual:
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
            unresolved.add(str(key))

    return not reasons and not unresolved, sorted(reasons), sorted(unresolved)


__all__ = ["credential_constraints_satisfied"]
