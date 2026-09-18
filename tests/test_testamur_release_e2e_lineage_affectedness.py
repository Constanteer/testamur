from __future__ import annotations

from testamur.advisory import TestamurAdvisoryStore
from testamur.affectedness import TestamurAffectednessEngine, TestamurAffectednessStore
from testamur.affectedness_reliance import RevisionPinnedRelianceResolver
from testamur.lineage import TestamurLineageStore


def _observed(ref: str) -> list[dict[str, str]]:
    return [{"ref": ref, "evidence_class": "OBSERVED"}]


def _derived(ref: str, signal: str) -> dict[str, str]:
    return {
        "ref": ref,
        "evidence_class": "DERIVED",
        "signal": signal,
        "analyzer": "release-e2e-region-map",
        "analyzer_version": "1",
    }


class _Reliance:
    def list(self, *, scope_ref, reliant_ref=None, object_ref=None):
        assert scope_ref == "scope:release"
        return [
            {
                "receipt_id": "receipt:release-api",
                "reliant_ref": "service:release-api",
                "reliant_revision_ref": "service:release-api@4",
                "object_ref": "component:vendored",
                "purpose": "runtime_dependency",
                "pinned_revisions": {"component:vendored": "vendored@c"},
                "policy_ids": ["policy:release"],
                "object_ref": "component:vendored",
                "stale": False,
                "current_admissible": True,
            }
        ]


def test_release_gate_c_lineage_attention_requires_evidence_before_verdict(tmp_path) -> None:
    database = tmp_path / "release-c.sqlite"
    lineage = TestamurLineageStore(database)
    affectedness = TestamurAffectednessStore(database)
    advisories = TestamurAdvisoryStore(database)
    engine = TestamurAffectednessEngine(lineage=lineage, assessments=affectedness)

    lineage.record_lineage(
        "fork@b", "DERIVED_FROM", "upstream@a", evidence=_observed("git:fork-point")
    )
    lineage.record_lineage(
        "vendored@c", "TRANSFORMS", "fork@b", evidence=_observed("build:vendor-copy")
    )
    event = advisories.record_adverse_event(
        provider="release-security-feed",
        external_id="ADV-RELEASE-C",
        event_class="VULNERABILITY_ADVISORY",
        upstream_refs=["upstream@a"],
        source_refs=["tst:source-revision:release-advisory"],
    )

    candidates = engine.record_potential_candidates(event)
    vendor_candidate = next(item for item in candidates if item["subject_revision"] == "vendored@c")
    assert vendor_candidate["state"] == "POTENTIALLY_AFFECTED"
    assert vendor_candidate["lineage_path_edge_ids"]

    # Lineage propagation creates an attention candidate only. It is not itself
    # a vulnerability verdict and therefore must not yet create relied impact.
    resolver = RevisionPinnedRelianceResolver(_Reliance(), "scope:release")
    before_verdict = engine.affected_reliance_blast_radius(
        event["event_revision_id"], resolver=resolver, policy_ref="policy:release"
    )
    assert before_verdict["affected_receipt_count"] == 0
    assert before_verdict["affected_reliant_refs"] == []

    confirmed = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="vendored@c",
        evidence=[_derived("analysis:vulnerable-region-present", "MATERIAL_PRESENT")],
        basis=[
            {"kind": "advisory_revision", "ref": event["event_revision_id"]},
            {"kind": "analysis", "ref": "analysis:vulnerable-region-present"},
        ],
        lineage_path_edge_ids=vendor_candidate["lineage_path_edge_ids"],
        supersedes_assessment_id=vendor_candidate["assessment_id"],
    )
    assert confirmed["state"] == "CONFIRMED_AFFECTED"

    impact = engine.affected_reliance_blast_radius(
        event["event_revision_id"], resolver=resolver, policy_ref="policy:release"
    )
    assert impact["affected_reliant_refs"] == ["service:release-api"]
    assert impact["affected_receipt_count"] == 1
    assert impact["semantics"]["review_obligation_only"] is True

    disproven = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="vendored@c",
        evidence=[_derived("analysis:vulnerable-region-absent", "MATERIAL_ABSENT")],
        basis=[
            {"kind": "advisory_revision", "ref": event["event_revision_id"]},
            {"kind": "analysis", "ref": "analysis:vulnerable-region-absent"},
        ],
        lineage_path_edge_ids=vendor_candidate["lineage_path_edge_ids"],
        supersedes_assessment_id=confirmed["assessment_id"],
    )
    assert disproven["state"] == "DISPROVEN"

    after_disproof = engine.affected_reliance_blast_radius(
        event["event_revision_id"], resolver=resolver, policy_ref="policy:release"
    )
    assert after_disproof["affected_receipt_count"] == 0
    assert after_disproof["affected_reliant_refs"] == []
