from __future__ import annotations

import io
import json

from testamur import front_router
from testamur import project_advisory_cli


def test_front_router_exposes_project_advisory_review_without_product_ontology(monkeypatch):
    seen = {}

    def fake_dispatch(argv):
        seen["argv"] = list(argv)
        return 0

    monkeypatch.setattr(front_router, "project_advisory_dispatch", fake_dispatch)
    assert front_router.main(["project", "advisory-review", "demo"]) == 0
    assert seen["argv"] == ["demo"]


def test_advisory_cli_delegates_to_canonical_project_review_projection(monkeypatch, tmp_path):
    expected = {
        "ok": True,
        "supply_chain": {
            "advisory_revalidation": {
                "requires_revalidation": True,
                "semantics": {
                    "changed_implies_invalid": False,
                    "stale_implies_false": False,
                    "recorded_assessment_is_verification": False,
                },
            }
        },
    }

    class FakeService:
        @classmethod
        def integrated(cls, *args, **kwargs):
            return object()

    class Registry:
        providers = {}
        specs = {}

    monkeypatch.setattr(project_advisory_cli, "TestamurProductService", FakeService)
    monkeypatch.setattr(project_advisory_cli, "load_monitor_provider_registry", lambda: Registry())
    monkeypatch.setattr(project_advisory_cli, "project_with_advisory_reviews", lambda service, ref: expected)
    out = io.StringIO()
    code = project_advisory_cli.dispatch(["demo", "--database", str(tmp_path / "db.sqlite")], stdout=out)

    assert code == 0
    assert json.loads(out.getvalue()) == expected
    semantics = json.loads(out.getvalue())["supply_chain"]["advisory_revalidation"]["semantics"]
    assert semantics["changed_implies_invalid"] is False
    assert semantics["stale_implies_false"] is False
    assert semantics["recorded_assessment_is_verification"] is False
