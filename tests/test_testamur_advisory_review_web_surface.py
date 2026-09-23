from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "testamur" / "web"


def test_project_web_loads_advisory_review_surface_before_app():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert html.index('/advisory-review-ui.js') < html.index('/app.js')


def test_advisory_review_surface_uses_canonical_projection_without_score():
    source = (WEB / "advisory-review-ui.js").read_text(encoding="utf-8")
    assert "testamur.product.advisory-review.v1" in source
    assert "advisory_review_required_count" in source
    assert "advisory_competing_count" in source
    assert "competing heads" in source.lower()
    assert "immutable recorded conclusions" in source
    assert "not generic verification" in source
    assert "trust scores" in source
    assert "score =" not in source
    assert "candidate_status === 'affected'" not in source


def test_advisory_review_surface_records_evidence_not_verdicts():
    source = (WEB / "advisory-review-ui.js").read_text(encoding="utf-8")
    assert "/v1/advisory-assessments" in source
    assert "event_revision_id" in source
    assert "subject_revision" in source
    assert "evidence_class" in source
    assert "manual_review" in source
    assert "supersedes_assessment_id" in source
    assert "History / Compare" in source
    assert ">Impact<" in source
    assert ">Revalidation<" in source
    assert "payload.state" not in source
    assert "payload.verdict" not in source
    assert "payload.trust_score" not in source


def test_advisory_review_surface_coalesces_external_mutations_only():
    source = (WEB / "advisory-review-ui.js").read_text(encoding="utf-8")
    assert "renderQueued" in source
    assert "queueRender" in source
    assert "queueMicrotask(render)" not in source
    assert "new MutationObserver(render)" not in source
    assert "data-advisory-review-state" in source
