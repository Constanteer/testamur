from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parents[1] / "testamur" / "web"


def test_first_run_resume_ignores_its_own_dom_mutations() -> None:
    script = (WEB_ROOT / "first-run-resume.js").read_text(encoding="utf-8")

    assert "function onlyResumeMutations(records)" in script
    assert "if (onlyResumeMutations(records)) return;" in script
    assert "queueMicrotask(render);" in script


def test_first_run_resume_keeps_semantic_boundary_copy() -> None:
    script = (WEB_ROOT / "first-run-resume.js").read_text(encoding="utf-8")

    assert "never infers verification, reliance, affectedness, validity, or truth" in script
    assert "Visiting them does not assert that any object was revalidated" in script
