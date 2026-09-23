from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDANCE = ROOT / "testamur" / "web" / "integration-install-guidance.js"
MCP = ROOT / "testamur" / "source_gateway_mcp.py"


def test_integration_smoke_uses_current_discovery_surface() -> None:
    guidance = GUIDANCE.read_text(encoding="utf-8")
    mcp = MCP.read_text(encoding="utf-8")

    assert '"method":"server/discover"' in guidance
    assert '"method":"initialize"' not in guidance
    assert "supportedVersions and capabilities" in guidance
    assert 'if method == "server/discover"' in mcp


def test_integration_state_probe_reaches_read_only_tool_layer() -> None:
    guidance = GUIDANCE.read_text(encoding="utf-8")
    mcp = MCP.read_text(encoding="utf-8")

    assert '"method":"tools/call"' in guidance
    assert '"name":"testamur.project_supply_chain"' in guidance
    assert "__testamur_diagnostic_missing_project__" in guidance
    assert "database/open/schema error" in guidance
    assert 'if method == "tools/call"' in mcp
    assert 'if name == "testamur.project_supply_chain"' in mcp


def test_integration_codex_guidance_exposes_packaged_doctor() -> None:
    guidance = GUIDANCE.read_text(encoding="utf-8")

    assert "python plugins/testamur-codex/scripts/doctor.py" in guidance
    assert "same environment that launches Codex" in guidance
    assert "project/repository-binding MCP surfaces" in guidance
    assert "successful doctor proves host wiring only" in guidance


def test_integration_smoke_does_not_claim_evidence_semantics() -> None:
    guidance = GUIDANCE.read_text(encoding="utf-8")

    assert "does not verify any source or establish reliance" in guidance
    assert "does not infer" in guidance
    assert "verification, reliance, affectedness, validity, or trust" in guidance
    assert "does not create a Project, fetch a Source, record reliance, or verify anything" in guidance
