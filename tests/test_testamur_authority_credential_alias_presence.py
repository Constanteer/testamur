from datetime import datetime, timezone

import pytest

from testamur.authority_credentials import credential_constraints_satisfied


AT = datetime(2026, 9, 24, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("label", "constraints", "attributes"),
    [
        ("audience", {"audience": "svc:a"}, {"audience": None, "audiences": ["svc:a"]}),
        ("scope", {"scope": "repo.read"}, {"scope": None, "scopes": ["repo.read"]}),
        ("issuer", {"issuer": "issuer:a"}, {"issuer": None, "issuers": ["issuer:a"]}),
        ("tenant", {"tenant": "tenant:a"}, {"tenant": None, "tenants": ["tenant:a"]}),
        (
            "repository_selection",
            {"repository_selection": "repo:a"},
            {"repository_selection": None, "repositories": ["repo:a"]},
        ),
    ],
)
def test_explicit_null_actual_alias_cannot_fall_through_to_valid_alias(
    label: str,
    constraints: dict[str, object],
    attributes: dict[str, object],
) -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        attributes, constraints, as_of=AT
    )

    assert ok is False
    assert reasons == []
    assert unresolved == [label]


@pytest.mark.parametrize(
    ("label", "constraints", "attributes"),
    [
        ("audience", {"audience": None, "required_audience": "svc:a"}, {"audience": "svc:a"}),
        ("scope", {"scope": None, "required_scope": "repo.read"}, {"scope": "repo.read"}),
        ("issuer", {"issuer": None, "required_issuer": "issuer:a"}, {"issuer": "issuer:a"}),
        ("tenant", {"tenant": None, "tenant_id": "tenant:a"}, {"tenant": "tenant:a"}),
        (
            "repository_selection",
            {"repository_selection": None, "required_repositories": ["repo:a"]},
            {"repositories": ["repo:a"]},
        ),
    ],
)
def test_explicit_null_required_alias_cannot_disappear_into_another_encoding(
    label: str,
    constraints: dict[str, object],
    attributes: dict[str, object],
) -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        attributes, constraints, as_of=AT
    )

    assert ok is False
    assert reasons == []
    assert unresolved == [label]


def test_absent_alias_still_allows_one_exact_encoding() -> None:
    ok, reasons, unresolved = credential_constraints_satisfied(
        {"audiences": ["svc:a"]},
        {"required_audience": "svc:a"},
        as_of=AT,
    )

    assert ok is True
    assert reasons == []
    assert unresolved == []
