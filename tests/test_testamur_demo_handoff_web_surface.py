from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "testamur" / "web"


def test_demo_handoff_assets_are_loaded():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert '/demo-handoff.css' in index
    assert '/demo-handoff.js' in index


def test_demo_handoff_moves_user_to_real_project_without_semantic_shortcuts():
    script = (WEB / "demo-handoff.js").read_text(encoding="utf-8")
    for phrase in (
        'Create real project',
        '/projects/new',
        'Connect Codex / MCP',
        '/integrations',
        'recorded ≠ verified',
        'fetched ≠ relied',
        'changed ≠ invalid',
        'stale ≠ false',
        'recorded observation is evidence, not a verification verdict',
    ):
        assert phrase in script
    lowered = script.lower()
    assert 'trust score' not in lowered
    assert 'confidence score' not in lowered
