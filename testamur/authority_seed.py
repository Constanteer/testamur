from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def exact_subject_ref(value: Any, *, field: str = "subject_ref") -> str:
    """Return one authority subject ref without manufacturing identity by coercion."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an exact non-empty string")
    return value.strip()


def normalize_compromise_seeds(compromised_refs: str | Sequence[str]) -> list[str]:
    """Normalize explicit blast-radius seeds only.

    Blast-radius seeding is an authority assumption, not a material-lineage or
    affectedness inference. Every seed must therefore already be an explicit
    authority subject ref; integers, mappings, objects, and mixed sequences fail
    closed instead of being stringified into new graph identities.
    """
    if isinstance(compromised_refs, str):
        refs: Sequence[Any] = (compromised_refs,)
    elif isinstance(compromised_refs, Sequence) and not isinstance(compromised_refs, (bytes, bytearray)):
        refs = compromised_refs
    else:
        raise ValueError("compromised_refs must be an exact subject ref or sequence of exact subject refs")

    seeds = sorted({exact_subject_ref(ref, field="compromised_refs[]") for ref in refs})
    if not seeds:
        raise ValueError("compromised_refs must contain at least one subject ref")
    return seeds


__all__ = ["exact_subject_ref", "normalize_compromise_seeds"]
