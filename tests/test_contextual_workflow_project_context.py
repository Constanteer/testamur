from pathlib import Path


ASSET = Path("testamur/web/contextual-guide.js")


def _source() -> str:
    return ASSET.read_text(encoding="utf-8")


def test_contextual_workflow_preserves_project_context_across_stages() -> None:
    source = _source()

    assert "function projectContext()" in source
    assert "for (const key of ['project', 'project_id'])" in source
    assert "const query = projectContext();" in source
    assert "if (stage !== 'source') query.set('tab', stage);" in source
    assert "return suffix ? `${base}?${suffix}` : base;" in source


def test_contextual_workflow_surfaces_review_context() -> None:
    source = _source()

    assert "function reviewContextLabel(objectRef)" in source
    assert "`Reviewing ${objectRef}${projectPart}`" in source
    assert "esc(reviewContextLabel(objectRef))" in source


def test_revalidation_return_uses_originating_project() -> None:
    source = _source()

    assert "function projectReturnHref()" in source
    assert "const params = projectContext();" in source
    assert "params.get('project') || params.get('project_id')" in source
    assert "`/projects/${encodeURIComponent(project)}`" in source


def test_contextual_workflow_keeps_semantic_boundaries_explicit() -> None:
    source = _source()

    for boundary in (
        "recorded ≠ verified",
        "fetched ≠ relied",
        "changed ≠ invalid",
        "stale ≠ false",
        "EXPOSED_TO_MODEL ≠ RELIED",
    ):
        assert boundary in source

    assert "generic trust score" not in source.lower()
