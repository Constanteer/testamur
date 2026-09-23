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


def test_integration_smoke_does_not_claim_evidence_semantics() -> None:
    guidance = GUIDANCE.read_text(encoding="utf-8")

    assert "does not verify any source or establish reliance" in guidance
    assert "does not infer" in guidance
    assert "verification, reliance, affectedness, validity, or trust" in guidance
