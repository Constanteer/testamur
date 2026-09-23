from __future__ import annotations

import pytest

from testamur.authority_seed import exact_subject_ref, normalize_compromise_seeds


def test_exact_subject_ref_preserves_explicit_identity() -> None:
    assert exact_subject_ref("connector:github") == "connector:github"


@pytest.mark.parametrize("value", [123, {"ref": "connector:github"}, None, object(), "   "])
def test_exact_subject_ref_rejects_coercion(value: object) -> None:
    with pytest.raises(ValueError):
        exact_subject_ref(value)


def test_compromise_seeds_are_exact_deduplicated_and_sorted() -> None:
    assert normalize_compromise_seeds(["service:b", "service:a", "service:b"]) == ["service:a", "service:b"]


@pytest.mark.parametrize(
    "value",
    [
        ["service:a", 7],
        [7],
        {"service:a": True},
        7,
        b"service:a",
        [],
    ],
)
def test_compromise_seeds_fail_closed_instead_of_stringifying(value: object) -> None:
    with pytest.raises(ValueError):
        normalize_compromise_seeds(value)  # type: ignore[arg-type]


def test_seed_normalizer_does_not_accept_affectedness_or_lineage_records() -> None:
    with pytest.raises(ValueError):
        normalize_compromise_seeds([{"subject_ref": "service:a", "affected": True}])  # type: ignore[list-item]
