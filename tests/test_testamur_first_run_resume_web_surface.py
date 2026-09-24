from pathlib import Path


WEB_ROOT = Path(__file__).resolve().parents[1] / "testamur" / "web"


def test_first_run_resume_ignores_its_own_dom_mutations() -> None:
    script = (WEB_ROOT / "first-run-resume.js").read_text(encoding="utf-8")

    assert "function onlyResumeMutations(records)" in script
    assert "if (onlyResumeMutations(records)) return;" in script
    assert "queueMicrotask(() =>" in script


def test_first_run_resume_keeps_semantic_boundary_copy() -> None:
    script = (WEB_ROOT / "first-run-resume.js").read_text(encoding="utf-8")

    assert "never infers verification, reliance, affectedness, validity, or truth" in script
    assert "Visiting them does not assert that any object was revalidated" in script


def test_first_run_resume_prefers_last_real_object_for_review_steps() -> None:
    script = (WEB_ROOT / "first-run-resume.js").read_text(encoding="utf-8")

    assert "LAST_OBJECT_KEY" in script
    assert "function continuationHref(step)" in script
    assert "value.startsWith('/object/')" in script
    assert "`${objectPath}?tab=${tab}`" in script
    assert "Continue with your object" in script
