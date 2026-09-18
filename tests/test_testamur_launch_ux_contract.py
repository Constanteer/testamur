from __future__ import annotations

from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parents[1] / "testamur" / "web"


def _app() -> str:
    return (WEB_ROOT / "app.js").read_text(encoding="utf-8")


def test_first_run_and_learning_surfaces_remain_reachable() -> None:
    app = _app()

    for route in ("/quickstart", "/demo", "/learn", "/docs", "/integrations"):
        assert f"href=\"{route}\"" in app or f"path === '{route}'" in app

    assert "5-minute quickstart" in app
    assert "Example project" in app
    assert "Make Testamur useful in three steps." in app
    assert "Create first project" in app
    assert "Add first monitor" in app
    assert "Run the first check" in app


def test_change_review_flow_stays_visible_as_one_product_workflow() -> None:
    app = _app()

    # These are user-facing stages, not a second ontology. A launch regression
    # must not strand change detection without the history/compare/impact/review
    # path that explains what to do next.
    assert "View recorded history" in app
    assert "Compare recorded versions" in app
    assert "Open impact" in app
    assert "Revalidation is where judgment belongs." in app
    assert "Review, rerun, or reconsider" in app
    assert "Record the new evidence explicitly" in app


def test_launch_copy_preserves_semantic_firewall() -> None:
    app = _app()

    for boundary in (
        "recorded ≠ verified",
        "fetched ≠ relied",
        "changed ≠ invalid",
        "stale ≠ false",
        "EXPOSED_TO_MODEL ≠ RELIED",
    ):
        assert boundary in app

    # Do not collapse Testamur into a generic scalar verdict during onboarding.
    lowered = app.lower()
    assert "trust score" not in lowered
    assert "validity score" not in lowered


def test_agent_install_surface_keeps_reliance_explicit() -> None:
    app = _app()

    assert "codex plugin marketplace add Constanteer/testamur-plugins" in app
    assert "testamur-gateway-mcp" in app
    assert "Fetch exact evidence" in app
    assert "Inspect provenance" in app
    assert "exposure remains distinct from durable reliance" in app
