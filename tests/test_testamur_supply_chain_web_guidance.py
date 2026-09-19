from pathlib import Path


WEB = Path(__file__).parents[1] / "testamur" / "web"


def test_supply_chain_guidance_is_loaded_and_semantically_bounded() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "supply-chain-guidance.js").read_text(encoding="utf-8")
    assert "/supply-chain-guidance.js" in index
    assert "/supply-chain-guidance.css" in index
    assert "Copy import command" in script
    assert "package identity match is not an affectedness verdict" in script
    assert "verified" not in script.casefold()
