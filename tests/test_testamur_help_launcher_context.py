from __future__ import annotations

from pathlib import Path


HELP = Path(__file__).resolve().parents[1] / "testamur" / "web" / "help-launcher.js"


def test_help_launcher_prioritizes_context_without_new_semantics() -> None:
    source = HELP.read_text(encoding="utf-8")

    assert "data-contextual-help" in source
    assert "Inspect recorded reliance before deciding what a scan change means" in source
    assert "Separate source identity from recorded observations" in source
    assert "Trace explicit recorded reliance before scoped revalidation" in source
    assert "Run the 5-minute quickstart" in source

    for boundary in (
        "recorded ≠ verified",
        "fetched ≠ relied",
        "changed ≠ invalid",
        "stale ≠ false",
        "EXPOSED_TO_MODEL ≠ RELIED",
    ):
        assert boundary in source

    lowered = source.lower()
    assert "data-trust-score" not in lowered
    assert "trust score:" not in lowered
