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


def test_readme_uses_public_project_cli_surface() -> None:
    readme = (Path(__file__).parents[1] / "README.md").read_text()
    for command in (
        "testamur project import . --name demo-project",
        "testamur project bind-repo demo-project .",
        "testamur-project-repo show demo-project",
        "testamur project scan demo-project",
        "testamur project supply-chain demo-project",
    ):
        assert command in readme
    assert "testamur product project" not in readme


def test_quickstart_names_only_current_project_mcp_tools() -> None:
    quickstart = (Path(__file__).parents[1] / "docs" / "TESTAMUR_5_MINUTE_QUICKSTART.md").read_text()
    for tool in (
        "testamur.project_repository_binding",
        "testamur.set_project_repository_binding_enabled",
        "testamur.project_repository_unbind",
        "testamur.project_scan",
        "testamur.project_supply_chain",
        "testamur.project_supply_chain_diff",
        "testamur.project_advisory_revalidation",
        "testamur.record_project_advisory_assessment",
    ):
        assert tool in quickstart
    assert "testamur.project_advisories" not in quickstart
