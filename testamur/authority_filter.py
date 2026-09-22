from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def normalize_capability_filter(
    value: Iterable[tuple[str, str]] | None,
) -> list[tuple[str, str]] | None:
    """Normalize an explicit capability selector without manufacturing authority.

    ``None`` means no selector was supplied. An explicit empty iterable remains
    empty and therefore selects no capabilities; it is never promoted to a
    wildcard. Entries must be exact non-empty string namespace/action pairs.
    Arbitrary scalar/object values are rejected rather than stringified.
    """
    if value is None:
        return None
    if isinstance(value, (str, bytes, dict)):
        raise ValueError("capability_filter must be an iterable of namespace/action pairs")

    normalized: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError("capability_filter entries must be namespace/action pairs")
        namespace, action = item
        if (
            not isinstance(namespace, str)
            or not namespace.strip()
            or not isinstance(action, str)
            or not action.strip()
        ):
            raise ValueError("capability_filter namespace/action values must be non-empty strings")
        normalized.append((namespace.strip(), action.strip()))
    return normalized


__all__ = ["normalize_capability_filter"]
