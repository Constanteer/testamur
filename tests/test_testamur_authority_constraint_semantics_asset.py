from __future__ import annotations

from pathlib import Path


ASSET = Path(__file__).parents[1] / "testamur" / "web" / "authority_constraint_semantics.js"


def test_constraint_semantics_renderer_is_projection_only_and_fail_closed():
    source = ASSET.read_text(encoding="utf-8")
    assert "recorded_constraint_semantics" in source
    assert "recorded does not mean valid" in source
    assert "omitted does not mean unrestricted" in source
    # The browser must not become an authorization evaluator.
    assert "item.constraints" not in source
    assert ".includes(" not in source
    assert "startsWith(" not in source
    assert "findPath" not in source
    assert "shortestPath" not in source


def test_constraint_semantics_renderer_has_explicit_credential_and_connector_fields():
    source = ASSET.read_text(encoding="utf-8")
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
