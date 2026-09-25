from pathlib import Path


WEB = Path(__file__).parents[1] / "testamur" / "web"


def test_supply_chain_guidance_is_loaded_and_semantically_bounded() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "supply-chain-guidance.js").read_text(encoding="utf-8")
    css = (WEB / "supply-chain-guidance.css").read_text(encoding="utf-8")
    assert "/supply-chain-guidance.js" in index
    assert "/supply-chain-guidance.css" in index
    assert "Copy import command" in script
    assert "package identity match is not an affectedness verdict" in script
    assert "upgraded" in script
    assert "downgraded" in script
    assert "version-changed" in script
    assert "An upgrade is not a safety verdict" in script
    assert "a changed dependency is not therefore invalid or affected" in script
    assert "inspect impact and advisory candidates" in script
    assert "supply-chain-transition-row" in script
    assert "versionFrom(item, 'before')" in script
    assert "versionFrom(item, 'after')" in script
    assert "version_transition" in script
    assert "supply-chain-transition-kind" in css
    assert "verified" not in script.casefold()
