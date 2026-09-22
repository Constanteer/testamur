from pathlib import Path


def test_five_minute_quickstart_uses_installed_cli_surface() -> None:
    quickstart = (Path(__file__).parents[1] / "docs" / "TESTAMUR_5_MINUTE_QUICKSTART.md").read_text()

    expected = (
        "testamur project import . --name demo-project",
        "testamur project bind-repo demo-project .",
        "testamur-project-repo show demo-project",
        "testamur project scan demo-project",
        "testamur project supply-chain demo-project",
        "testamur project supply-chain-history demo-project",
        "testamur project supply-chain-diff demo-project",
    )
    for command in expected:
        assert command in quickstart

    # `product` is accepted for product-kernel reads, but the public Project
    # commands in the launch path are routed directly by `testamur`.
    assert "testamur product project" not in quickstart


def test_quickstart_keeps_semantic_guardrails_visible() -> None:
    quickstart = (Path(__file__).parents[1] / "docs" / "TESTAMUR_5_MINUTE_QUICKSTART.md").read_text()

    for distinction in (
        "recorded != verified",
        "fetched != relied",
        "changed != invalid",
        "stale != false",
        "EXPOSED_TO_MODEL != RELIED",
    ):
        assert distinction in quickstart
    assert "generic trust score" in quickstart
