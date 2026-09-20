from __future__ import annotations

from pathlib import Path


WEB = Path(__file__).parents[1] / "testamur" / "web"
ASSET = WEB / "authority_constraint_semantics.js"
PRODUCTION_ASSET = WEB / "authority_reason_groups.js"


def _assert_projection_only(source: str) -> None:
    assert "recorded_constraint_semantics" in source
    assert "recorded does not mean valid" in source
    assert "omitted does not mean unrestricted" in source
    # The browser must not become an authorization evaluator.
    assert "item.constraints" not in source
    assert ".includes(" not in source
    assert "startsWith(" not in source
    assert "findPath" not in source
    assert "shortestPath" not in source


def test_constraint_semantics_renderer_is_projection_only_and_fail_closed():
    _assert_projection_only(ASSET.read_text(encoding="utf-8"))


def test_production_authority_renderer_exposes_same_projection_only_semantics():
    source = PRODUCTION_ASSET.read_text(encoding="utf-8")
    _assert_projection_only(source)
    assert "renderRecordedConstraintSemantics" in source
    assert "validate" in source  # explanatory comment only: validation is forbidden here


def test_constraint_semantics_renderer_has_explicit_credential_and_connector_fields():
    for source in (
        ASSET.read_text(encoding="utf-8"),
        PRODUCTION_ASSET.read_text(encoding="utf-8"),
    ):
        for field in (
            "audiences",
            "scopes",
            "issuer",
            "tenant",
            "binding",
            "expires_at",
            "repositories",
            "resources",
            "mfa_required",
            "approval_required",
        ):
            assert f"{field}:" in source
