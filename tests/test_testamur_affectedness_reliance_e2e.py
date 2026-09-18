from __future__ import annotations

from testamur.advisory import TestamurAdvisoryStore
from testamur.affectedness import TestamurAffectednessEngine, TestamurAffectednessStore
from testamur.affectedness_reliance import RevisionPinnedRelianceResolver
from testamur.lineage import TestamurLineageStore


def observed(ref: str):
    return [{"ref": ref, "evidence_class": "OBSERVED"}]


def derived(ref: str, signal: str):
    return {
        "ref": ref,
        "evidence_class": "DERIVED",
        "signal": signal,
        "analyzer": "region-map",
        "analyzer_version": "1.0",
    }


class RelianceStoreFixture:
    def list(self, *, scope_ref, reliant_ref=None, object_ref=None):
        assert scope_ref == "scope:production"
        return [
            {
                "receipt_id": "receipt:api",
                "reliant_ref": "service:api",
                "reliant_revision_ref": "service:api@9",
                "object_ref": "component:vendor",
                "purpose": "runtime_dependency",
                "pinned_revisions": {"component:vendor": "vendor@c"},
                "policy_ids": ["policy:prod"],
                "stale": False,
                "current_admissible": True,
            },
            {
                "receipt_id": "receipt:unrelated",
                "reliant_ref": "service:worker",
                "object_ref": "component:other",
                "purpose": "runtime_dependency",
                "pinned_revisions": {"component:other": "other@7"},
                "policy_ids": ["policy:prod"],
            },
        ]


def test_advisory_to_lineage_to_actual_reliance_review_obligation(tmp_path) -> None:
    database = tmp_path / "w5.sqlite"
    lineage = TestamurLineageStore(database)
    assessments = TestamurAffectednessStore(database)
    advisories = TestamurAdvisoryStore(database)
    engine = TestamurAffectednessEngine(lineage=lineage, assessments=assessments)

    lineage.record_lineage(
        "fork@b", "DERIVED_FROM", "upstream@a", evidence=observed("git:parent")
    )
    lineage.record_lineage(
        "vendor@c", "TRANSFORMS", "fork@b", evidence=observed("vendor:copy")
    )
    event = advisories.record_adverse_event(
        provider="example-security",
        external_id="ADV-E2E",
        event_class="VULNERABILITY_ADVISORY",
        upstream_refs=["upstream@a"],
        source_refs=["tst:source-revision:advisory"],
    )
    candidates = engine.record_potential_candidates(event)
    vendor_candidate = next(
        item for item in candidates if item["subject_revision"] == "vendor@c"
    )

    confirmed = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="vendor@c",
        evidence=[derived("analysis:material-present", "MATERIAL_PRESENT")],
        basis=[
            {"kind": "advisory_revision", "ref": event["event_revision_id"]},
            {"kind": "analysis", "ref": "analysis:material-present"},
        ],
        lineage_path_edge_ids=vendor_candidate["lineage_path_edge_ids"],
        supersedes_assessment_id=vendor_candidate["assessment_id"],
    )
    assert confirmed["state"] == "CONFIRMED_AFFECTED"

    resolver = RevisionPinnedRelianceResolver(
        RelianceStoreFixture(), "scope:production"
    )
    blast = engine.affected_reliance_blast_radius(
        event["event_revision_id"],
        resolver=resolver,
        policy_ref="policy:prod",
    )
    assert blast["affected_reliant_refs"] == ["service:api"]
    assert blast["affected_receipt_count"] == 1
    assert blast["semantics"]["review_obligation_only"] is True

    disproven = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="vendor@c",
        evidence=[derived("analysis:material-absent", "MATERIAL_ABSENT")],
        basis=[
            {"kind": "advisory_revision", "ref": event["event_revision_id"]},
            {"kind": "analysis", "ref": "analysis:material-absent"},
        ],
        lineage_path_edge_ids=vendor_candidate["lineage_path_edge_ids"],
        supersedes_assessment_id=confirmed["assessment_id"],
    )
    assert disproven["state"] == "DISPROVEN"

    blast_after_disproof = engine.affected_reliance_blast_radius(
        event["event_revision_id"],
        resolver=resolver,
        policy_ref="policy:prod",
    )
    assert blast_after_disproof["affected_receipt_count"] == 0
    assert blast_after_disproof["affected_reliant_refs"] == []
