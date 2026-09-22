from __future__ import annotations

import pytest

from testamur.authority_filter import normalize_capability_filter


def test_none_means_no_selector_but_explicit_empty_stays_empty() -> None:
    assert normalize_capability_filter(None) is None
    assert normalize_capability_filter([]) == []
    assert normalize_capability_filter(()) == []


def test_exact_string_pairs_are_trimmed_without_broadening() -> None:
    assert normalize_capability_filter([(" repo ", " write "), ("issues", "read")]) == [
        ("repo", "write"),
        ("issues", "read"),
    ]


@pytest.mark.parametrize(
    "value",
    [
        "repo:write",
        {"namespace": "repo", "action": "write"},
        [(1, "write")],
        [("repo", 2)],
        [("", "write")],
        [("repo", "")],
        [("repo",)],
        [("repo", "write", "extra")],
    ],
)
def test_malformed_or_implicitly_stringifiable_filters_fail_closed(value: object) -> None:
    with pytest.raises(ValueError):
        normalize_capability_filter(value)  # type: ignore[arg-type]
