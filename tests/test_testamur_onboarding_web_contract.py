from pathlib import Path


WEB_ROOT = Path(__file__).parents[1] / "testamur" / "web"
APP = (WEB_ROOT / "app.js").read_text(encoding="utf-8")


def test_help_menu_exposes_first_run_learning_surfaces():
    for route in ("/quickstart", "/demo", "/learn", "/docs", "/integrations"):
        assert f'href="{route}"' in APP

    assert "5-minute quickstart" in APP
    assert "Example project" in APP
    assert "What is Testamur?" in APP
    assert "Concept reference" in APP


def test_dashboard_onboarding_is_progressive_and_actionable():
    assert "function onboardingProgress" in APP
    assert "Make Testamur useful in three steps." in APP
    assert "Create a project" in APP
    assert "Add something you rely on" in APP
    assert "Record the first observation" in APP
    assert "Open 5-minute quickstart" in APP


def test_first_change_guidance_does_not_turn_change_into_a_verdict():
    assert "function changedGuidance" in APP
    assert "A monitored source changed. That does not mean your work is wrong." in APP
    assert "View recorded history" in APP
    assert "See affected work" in APP
    assert "changed ≠ invalid · stale ≠ false" in APP


def test_demo_walks_the_user_through_history_compare_impact_and_revalidation():
    assert "function demoPage" in APP
    for stage in ("overview", "history", "compare", "impact", "revalidate"):
        assert f"'{stage}'" in APP

    assert "mechanical text diff" in APP
    assert "Affectedness narrows attention." in APP
    assert "Revalidation recorded" in APP
    assert "no workspace data is changed" in APP


def test_object_inspection_exposes_compare_impact_and_explicit_revalidation():
    assert "async function objectPage" in APP
    assert "async function historyPanel" in APP
    assert "async function impactPanel" in APP
    assert "function revalidationPanel" in APP
    assert "Revalidation is where judgment belongs." in APP
    assert "A change does not automatically make downstream work invalid." in APP


def test_integration_onboarding_preserves_exposure_and_reliance_boundary():
    assert "Codex" in APP
    assert "Any MCP client" in APP
    assert "testamur-gateway-mcp" in APP
    assert "EXPOSED_TO_MODEL ≠ RELIED" in APP
    assert "fetched ≠ relied" in APP


def test_launch_surfaces_do_not_introduce_generic_trust_score():
    launch_start = APP.index("function learnPage")
    launch_end = APP.index("async function statusPage")
    launch_surface = APP[launch_start:launch_end].lower()

    assert "it is not a global trust score" in launch_surface
    assert "trust score:" not in launch_surface
    assert "data-trust-score" not in launch_surface
    assert "confidence score" not in launch_surface
    assert "recorded ≠ verified" in launch_surface
    assert "changed ≠ invalid" in launch_surface
    assert "stale ≠ false" in launch_surface
