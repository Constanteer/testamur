from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from testamur.advisory import AdverseEventClass, TestamurAdvisoryStore
from testamur.affectedness import TestamurAffectednessStore
from testamur.product_advisory_actions import assess_advisory_candidate


def _revision(database: Path) -> dict:
    return TestamurAdvisoryStore(database).record_adverse_event(
        provider="test",
        external_id="TEST-2026-1",
        event_class=AdverseEventClass.VULNERABILITY_ADVISORY,
        upstream_refs=["pkg:npm/example@1.2.3#sha256:abc"],
        source_refs=["https://example.invalid/advisory/1"],
    )


def test_product_action_records_engine_resolved_assessment() -> None:
    with TemporaryDirectory() as temporary:
        database = Path(temporary) / "testamur.sqlite3"
        revision = _revision(database)

        assessment = assess_advisory_candidate(
            database,
            event_revision_id=revision["event_revision_id"],
            subject_revision="component:demo@1",
            evidence=[],
            basis=[{"kind": "manual_review", "ref": "review:demo"}],
        )

        assert assessment["event_revision_id"] == revision["event_revision_id"]
        assert assessment["subject_revision"] == "component:demo@1"
        assert assessment["state"] == "UNKNOWN"
        assert {"kind": "advisory_revision", "ref": revision["event_revision_id"]} in assessment["basis"]
        assert {"kind": "manual_review", "ref": "review:demo"} in assessment["basis"]
        assert TestamurAffectednessStore(database).get_assessment(assessment["assessment_id"]) == assessment
        assert "trust_score" not in assessment


def test_product_action_requires_existing_immutable_advisory_revision() -> None:
    with TemporaryDirectory() as temporary:
        database = Path(temporary) / "testamur.sqlite3"
        with pytest.raises(KeyError):
            assess_advisory_candidate(
                database,
                event_revision_id="advisory:missing",
                subject_revision="component:demo@1",
                evidence=[],
                basis=[],
            )
