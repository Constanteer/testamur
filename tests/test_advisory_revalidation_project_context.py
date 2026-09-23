from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "testamur" / "web" / "advisory-revalidation-ui.js"


def test_project_revalidation_handoff_preserves_originating_project_context():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "let latestProjectContext = null" in text
    assert "const projectContext = url =>" in text
    assert "for (const key of ['project', 'project_id'])" in text
    assert "latestProjectContext = projectContext(url)" in text
    assert "Object.entries(latestProjectContext || {})" in text
    assert "params.set(key, value)" in text


def test_project_context_is_navigation_only_not_a_verdict():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "Change is a review trigger, not a verdict." in text
    assert "Changed ≠ invalid; stale ≠ false." in text
    assert "does not establish affectedness, validity, safety, or reliance" in text
