from __future__ import annotations

from testamur.advisory import TestamurAdvisoryStore
from testamur.affectedness import TestamurAffectednessEngine, TestamurAffectednessStore
from testamur.component_identity import ComponentIdentity, ComponentRevisionIdentity
from testamur.lineage import TestamurLineageStore
from testamur.vendor_lineage import record_vendored_component


def test_vendored_component_advisory_stays_candidate_until_applicability_evidence(tmp_path) -> None:
    db = tmp_path / "testamur.sqlite"
    lineage = TestamurLineageStore(db)
    advisories = TestamurAdvisoryStore(db)
    assessments = TestamurAffectednessStore(db)
    engine = TestamurAffectednessEngine(lineage=lineage, assessments=assessments)

    component = ComponentIdentity.create(kind="package", namespace="pypi", name="demo")
    component_revision = ComponentRevisionIdentity.create(
        component=component,
        version="1.2.3",
        digest="sha256:vulnerable",
    )
    edge = record_vendored_component(
        lineage,
        container_revision="tst:revision:release-r1",
        component_revision=component_revision.revision_id,
        component_identity=component,
        evidence_ref="tst:sbom:release-r1",
        location={"path": "vendor/demo"},
        manifest_ref="tst:manifest:release-r1",
    )
    event = advisories.record_adverse_event(
        provider="example-security",
        external_id="CVE-2099-0001",
        event_class="VULNERABILITY_ADVISORY",
        upstream_refs=[component_revision.revision_id],
        known_affected={"versions": ["1.2.3"]},
        affected_component_or_region={"symbol": "demo.parse"},
        source_refs=["tst:source-revision:advisory-1"],
    )

    candidates = engine.find_potentially_affected(event)
    assert [item["subject_revision"] for item in candidates] == ["tst:revision:release-r1"]
    assert candidates[0]["state"] == "POTENTIALLY_AFFECTED"
    assert candidates[0]["paths"][0]["edge_ids"] == [edge["edge_id"]]
    assert candidates[0]["semantics"]["confirmed_affected_implied"] is False

    potential = engine.record_potential_candidates(event)[0]
    assert potential["state"] == "POTENTIALLY_AFFECTED"

    resolved = engine.assess_from_evidence(
        event_revision_id=event["event_revision_id"],
        subject_revision="tst:revision:release-r1",
        evidence=[
            {
                "ref": "tst:analysis:region-present",
                "evidence_class": "DERIVED",
                "signal": "MATERIAL_PRESENT",
                "analyzer": "symbol-region-map",
                "analyzer_version": "1",
                "scope": {"symbol": "demo.parse"},
            }
        ],
        basis=[
            {"kind": "advisory_revision", "ref": event["event_revision_id"]},
            {"kind": "lineage_edge", "ref": edge["edge_id"]},
            {"kind": "analysis", "ref": "tst:analysis:region-present"},
        ],
        lineage_path_edge_ids=[edge["edge_id"]],
        supersedes_assessment_id=potential["assessment_id"],
    )
    assert resolved["state"] == "CONFIRMED_AFFECTED"
    assert assessments.history(event["event_revision_id"], "tst:revision:release-r1")[1]["state"] == "POTENTIALLY_AFFECTED"


def test_vendored_component_can_be_disproven_without_erasing_lineage(tmp_path) -> None:
    db = tmp_path / "testamur.sqlite"
    lineage = TestamurLineageStore(db)
    assessments = TestamurAffectednessStore(db)
    engine = TestamurAffectednessEngine(lineage=lineage, assessments=assessments)
    component = ComponentIdentity.create(kind="package", namespace="generic", name="embedded")
    edge = record_vendored_component(
        lineage,
        container_revision="artifact@r2",
        component_revision="component@r1",
        component_identity=component,
        evidence_ref="sbom:r2",
        location={"path": "third_party/embedded"},
    )

    resolved = engine.assess_from_evidence(
        event_revision_id="advisory@r1",
        subject_revision="artifact@r2",
        evidence=[
            {
                "ref": "analysis:vulnerable-region-absent",
                "evidence_class": "DERIVED",
                "signal": "MATERIAL_ABSENT",
                "analyzer": "region-map",
                "analyzer_version": "1",
            }
        ],
        basis=[
            {"kind": "advisory_revision", "ref": "advisory@r1"},
            {"kind": "lineage_edge", "ref": edge["edge_id"]},
            {"kind": "analysis", "ref": "analysis:vulnerable-region-absent"},
        ],
        lineage_path_edge_ids=[edge["edge_id"]],
    )
    assert resolved["state"] == "DISPROVEN"
    assert lineage.get_lineage(edge["edge_id"])["relation_type"] == "CONTAINS"
