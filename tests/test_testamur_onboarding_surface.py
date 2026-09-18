from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "testamur" / "web" / "app.js").read_text(encoding="utf-8")
ONBOARDING = (ROOT / "docs" / "TESTAMUR_ONBOARDING.md").read_text(encoding="utf-8")


def test_first_run_routes_and_help_entry_remain_reachable() -> None:
    """The checked-in Web bundle must keep the complete first-use learning path."""
    for route in ("/quickstart", "/demo", "/learn", "/docs", "/integrations"):
        assert f'href="{route}"' in APP

    for phrase in (
        "Create a project",
        "Add something you rely on",
        "Record the first observation",
        "See an example first",
    ):
        assert phrase in APP


def test_change_guidance_does_not_turn_change_into_a_verdict() -> None:
    assert "That does not mean your work is wrong." in APP
    assert "changed ≠ invalid" in APP
    assert "stale ≠ false" in APP
    assert "View recorded history" in APP
    assert "See affected work" in APP


def test_onboarding_contract_keeps_canonical_semantic_firewall() -> None:
    for distinction in (
        "recorded != verified",
        "fetched != relied",
        "changed != invalid",
        "stale != false",
        "EXPOSED_TO_MODEL != RELIED",
    ):
        assert distinction in ONBOARDING

    assert "No onboarding copy may introduce a generic trust/confidence score" in ONBOARDING


def test_demo_contract_remains_read_only() -> None:
    assert "must not write user workspace state" in ONBOARDING
    assert "deterministic" in ONBOARDING
