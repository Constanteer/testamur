from __future__ import annotations

from pathlib import Path

from testamur.affectedness import (
    AffectednessState,
    ApplicabilitySignal,
    TestamurAffectednessEngine,
    TestamurAffectednessStore,
)
from testamur.lineage import (
    LineageEvidenceClass,
    LineageRelationType,
    TestamurLineageStore,
)


def test_gate_c_lineage_candidate_is_not_vulnerability_verdict(tmp_path: Path) -> None:
    db = tmp_path / "testamur.sqlite3"
    lineage = TestamurLineageStore(db)
    assessments = TestamurAffectednessStore(db)
    engine = TestamurAffectednessEngine(lineage=lineage, assessments=assessments)

    edge = lineage.record_lineage(
        "revision:vendor-fork",
        LineageRelationType.DERIVED_FROM,
        "revision:upstream-vulnerable",
        evidence=[
            {
                "ref": "source:vendor-manifest",
                "evidence_class": LineageEvidenceClass.OBSERVED.value,
            }
        ],
    )
    event = {
        "event_revision_id": "advisory:revision:1",
        "upstream_refs": ["revision:upstream-vulnerable"],
    }

    potential = engine.record_potential_candidates(event)
    assert len(potential) == 1
    assert potential[0]["subject_revision"] == "revision:vendor-fork"
    assert potential[0]["state"] == AffectednessState.POTENTIALLY_AFFECTED.value
    assert potential[0]["semantics"]["lineage_propagation_is_verdict"] is False
    assert potential[0]["semantics"]["potentially_affected_is_confirmed_affected"] is False
    assert potential[0]["lineage_path_edge_ids"] == [edge["edge_id"]]

    unknown = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="revision:vendor-fork",
        evidence=[
            {
                "ref": "scanner:run:1",
                "signal": ApplicabilitySignal.SCANNER_NO_MATCH.value,
                "evidence_class": LineageEvidenceClass.DERIVED.value,
                "analyzer": "fixture-scanner",
                "analyzer_version": "1",
            }
        ],
        basis=[{"kind": "scanner_run", "ref": "scanner:run:1"}],
        lineage_path_edge_ids=[edge["edge_id"]],
        supersedes_assessment_id=potential[0]["assessment_id"],
    )
    assert unknown["state"] == AffectednessState.UNKNOWN.value
    assert unknown["explanation"]["reason"] == "analysis_did_not_establish_presence_or_absence"
    assert unknown["semantics"]["scanner_non_detection_is_disproof"] is False

    confirmed = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="revision:vendor-fork",
        evidence=[
            {
                "ref": "inspection:material-present",
                "signal": ApplicabilitySignal.MATERIAL_PRESENT.value,
                "evidence_class": LineageEvidenceClass.OBSERVED.value,
            }
        ],
        basis=[{"kind": "inspection", "ref": "inspection:material-present"}],
        lineage_path_edge_ids=[edge["edge_id"]],
        supersedes_assessment_id=unknown["assessment_id"],
    )
    assert confirmed["state"] == AffectednessState.CONFIRMED_AFFECTED.value
    assert confirmed["explanation"]["reason"] == "event_relevant_material_or_condition_present"
    history = assessments.history(event["event_revision_id"], "revision:vendor-fork")
    assert {item["state"] for item in history} == {
        AffectednessState.POTENTIALLY_AFFECTED.value,
        AffectednessState.UNKNOWN.value,
        AffectednessState.CONFIRMED_AFFECTED.value,
    }
