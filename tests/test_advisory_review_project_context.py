from pathlib import Path


ASSET = Path("testamur/web/advisory-review-ui.js")


def _source() -> str:
    return ASSET.read_text(encoding="utf-8")


def test_advisory_review_links_preserve_originating_project_context() -> None:
    source = _source()

    # Project-scoped advisory work must not lose its originating project when the
    # reviewer moves into History/Compare, Impact, or Revalidation.
    assert "function projectContext()" in source
    assert "latestProjectUrl" in source
    assert "project" in source
    assert "project_id" in source
    assert "objectTab(ref, 'history')" in source
    assert "objectTab(ref, 'impact')" in source
    assert "objectTab(ref, 'revalidate')" in source


def test_advisory_review_keeps_identity_overlap_separate_from_affectedness() -> None:
    source = _source()

    assert "Identity overlap only nominates work for review" in source
    assert "not a verdict" in source
    assert "generic verification, validity, or trust scores" in source
