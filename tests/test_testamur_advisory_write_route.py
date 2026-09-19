from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from testamur.advisory import AdverseEventClass, TestamurAdvisoryStore
from testamur.advisory_write_route import record_advisory_assessment
from testamur.product_service import TestamurProductService


def test_write_handler_records_engine_state_without_accepting_verdict() -> None:
    with TemporaryDirectory() as temporary:
        database = Path(temporary) / "testamur.sqlite3"
        revision = TestamurAdvisoryStore(database).record_adverse_event(
            provider="test",
            external_id="TEST-WRITE-1",
            event_class=AdverseEventClass.VULNERABILITY_ADVISORY,
            upstream_refs=["pkg:npm/example@1.2.3#sha256:abc"],
            source_refs=["https://example.invalid/advisory/write"],
        )
        service = TestamurProductService.integrated(database)
        assessment = record_advisory_assessment(
            service,
            {
                "event_revision_id": revision["event_revision_id"],
                "subject_revision": "component:demo@1",
                "evidence": [],
                "basis": [{"kind": "manual_review", "ref": "review:write"}],
            },
        )
        assert assessment["state"] == "UNKNOWN"
        assert assessment["event_revision_id"] == revision["event_revision_id"]
        assert "trust_score" not in assessment


def test_write_handler_rejects_conclusion_fields_before_engine_call() -> None:
    with TemporaryDirectory() as temporary:
        service = TestamurProductService.integrated(Path(temporary) / "testamur.sqlite3")
        for forbidden in ("state", "verdict", "trust_score"):
            with pytest.raises(ValueError, match="caller-supplied conclusion"):
                record_advisory_assessment(
                    service,
                    {
                        "event_revision_id": "advisory:any",
                        "subject_revision": "component:any",
                        "evidence": [],
                        "basis": [],
                        forbidden: "CONFIRMED_AFFECTED",
                    },
                )


def test_write_handler_rejects_unknown_revision_fail_closed() -> None:
    with TemporaryDirectory() as temporary:
        service = TestamurProductService.integrated(Path(temporary) / "testamur.sqlite3")
        with pytest.raises(ValueError, match="recorded immutable advisory revision"):
            record_advisory_assessment(
                service,
                {
                    "event_revision_id": "advisory:missing",
                    "subject_revision": "component:any",
                    "evidence": [],
                    "basis": [],
                },
            )
