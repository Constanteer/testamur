from __future__ import annotations

from pathlib import Path


def test_web_project_route_uses_advisory_aware_projection():
    """Keep the hosted Project surface on the canonical advisory review projection.

    This is intentionally a source-level wiring guard: the HTTP dispatcher is a
    thin adapter and must not duplicate advisory/affectedness semantics.
    """
    web_app = Path(__file__).parents[1] / "testamur" / "web_app.py"
    source = web_app.read_text(encoding="utf-8")

    assert "from .project_review_surface import project_with_advisory_reviews" in source
    assert 'return _json(project_with_advisory_reviews(service, _one(query, "ref") or ""))' in source
    assert 'return _json(service.project(_one(query, "ref") or ""))' not in source
