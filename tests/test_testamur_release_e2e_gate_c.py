from __future__ import annotations

from testamur.advisory import TestamurAdvisoryStore
from testamur.affectedness import TestamurAffectednessEngine, TestamurAffectednessStore
from testamur.affectedness_reliance import RevisionPinnedRelianceResolver
from testamur.lineage import TestamurLineageStore


def _observed(ref: str):
    return [{"ref": ref, "evidence_class": "OBSERVED"}]


def _derived(ref: str, signal: str):
    return {
        "ref": ref,
        "evidence_class": "DERIVED",
        "signal": signal,
        "analyzer": "fixture-region-map",
        "analyzer_version": "1",
    }


class RelianceFixture:
    def list(self, *, scope_ref, reliant_ref=None, object_ref=None):
        assert scope_ref == "scope:release"
        return [
            {
                "receipt_id": "tst:reliance:api",
                "reliant_ref": "tst:record:api",
                "reliant_revision_ref": "tst:record-revision:api-v1",
                "object_ref": "tst:component:vendor",
                "purpose": "runtime_dependency",
                "pinned_revisions": {"tst:component:vendor": "revision:vendor-v1"},
                "policy_ids": ["tst:policy:release"],
                "stale": False,
                "current_admissible": True,
            }
        ]


def test_gate_c_vendor_advisory_resolution_drives_review_obligation_only(tmp_path) -> None:
    db = tmp_path / "testamur.sqlite3"
    lineage = TestamurLineageStore(db)
    assessments = TestamurAffectednessStore(db)
    advisories = TestamurAdvisoryStore(db)
    engine = TestamurAffectednessEngine(lineage=lineage, assessments=assessments)

    lineage.record_lineage(
        "revision:fork-v1", "DERIVED_FROM", "revision:upstream-vuln",
        evidence=_observed("git:fork-parent"),
    )
    lineage.record_lineage(
        "revision:vendor-v1", "TRANSFORMS", "revision:fork-v1",
        evidence=_observed("vendor:copy-receipt"),
    )
    event = advisories.record_adverse_event(
        provider="fixture-security",
        external_id="ADV-GATE-C",
        event_class="VULNERABILITY_ADVISORY",
        upstream_refs=["revision:upstream-vuln"],
        source_refs=["tst:source-revision:advisory-v1"],
    )

    candidates = engine.record_potential_candidates(event)
    vendor = next(item for item in candidates if item["subject_revision"] == "revision:vendor-v1")
    assert vendor["state"] == "POTENTIALLY_AFFECTED"
    assert vendor["semantics"]["lineage_propagation_is_verdict"] is False

    unknown = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="revision:vendor-v1",
        evidence=[_derived("scanner:no-match", "SCANNER_NO_MATCH")],
        basis=[{"kind": "scanner_run", "ref": "scanner:no-match"}],
        lineage_path_edge_ids=vendor["lineage_path_edge_ids"],
        supersedes_assessment_id=vendor["assessment_id"],
    )
    assert unknown["state"] == "UNKNOWN"
    assert unknown["semantics"]["scanner_non_detection_is_disproof"] is False

    confirmed = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="revision:vendor-v1",
        evidence=[_derived("analysis:material-present", "MATERIAL_PRESENT")],
        basis=[{"kind": "analysis", "ref": "analysis:material-present"}],
        lineage_path_edge_ids=vendor["lineage_path_edge_ids"],
        supersedes_assessment_id=unknown["assessment_id"],
    )
    assert confirmed["state"] == "CONFIRMED_AFFECTED"

    resolver = RevisionPinnedRelianceResolver(RelianceFixture(), "scope:release")
    impact = engine.affected_reliance_blast_radius(
        event["event_revision_id"], resolver=resolver, policy_ref="tst:policy:release"
    )
    assert impact["affected_receipt_count"] == 1
    assert impact["affected_reliant_refs"] == ["tst:record:api"]
    assert impact["semantics"]["review_obligation_only"] is True
    assert impact["semantics"]["affectedness_implies_downstream_false"] is False

    disproven = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="revision:vendor-v1",
        evidence=[_derived("analysis:material-absent", "MATERIAL_ABSENT")],
        basis=[{"kind": "analysis", "ref": "analysis:material-absent"}],
        lineage_path_edge_ids=vendor["lineage_path_edge_ids"],
        supersedes_assessment_id=confirmed["assessment_id"],
    )
    assert disproven["state"] == "DISPROVEN"
    cleared = engine.affected_reliance_blast_radius(
        event["event_revision_id"], resolver=resolver, policy_ref="tst:policy:release"
    )
    assert cleared["affected_receipt_count"] == 0
