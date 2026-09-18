from __future__ import annotations

import unittest

from testamur.advisory_assessment import assess_advisory_revision


class _CapturingEngine:
    def __init__(self) -> None:
        self.kwargs = None

    def assess_from_evidence(self, **kwargs):
        self.kwargs = kwargs
        return {"state": "UNKNOWN", "captured": kwargs}


class AdvisoryAssessmentWorkflowTests(unittest.TestCase):
    def test_resolved_identity_evidence_survives_into_assessment_basis(self) -> None:
        engine = _CapturingEngine()
        revision = {
            "event_id": "advisory:event",
            "event_revision_id": "advisory:revision",
            "upstream_refs": ["pkg:npm/example@1.2.3#sha256:abc"],
            "identity_resolution": {
                "status": "resolved_exact",
                "upstream_identity": {"ecosystem": "npm", "name": "example", "version": "1.2.3"},
                "evidence": [
                    {
                        "ref": "evidence:registry-resolution",
                        "kind": "registry_manifest",
                        "digest": "sha256:abc",
                    }
                ],
            },
        }

        result = assess_advisory_revision(
            engine,
            revision,
            subject_revision="git:subject@deadbeef",
            evidence=[
                {
                    "ref": "evidence:scanner",
                    "signal": "INCONCLUSIVE",
                    "evidence_class": "DERIVED",
                    "analyzer": "scanner",
                    "analyzer_version": "1",
                }
            ],
            basis=[{"kind": "scanner_run", "ref": "scan:1"}],
            lineage_path_edge_ids=["edge:1"],
        )

        self.assertEqual(result["state"], "UNKNOWN")
        self.assertIsNotNone(engine.kwargs)
        basis = engine.kwargs["basis"]
        self.assertIn(
            {"kind": "advisory_revision", "ref": "advisory:revision"}, basis
        )
        resolution_entries = [
            item for item in basis if item.get("kind") == "advisory_identity_resolution"
        ]
        self.assertEqual(len(resolution_entries), 1)
        self.assertEqual(
            resolution_entries[0]["ref"], "evidence:registry-resolution"
        )
        self.assertFalse(
            resolution_entries[0]["semantics"]["identity_resolution_is_affectedness_verdict"]
        )
        self.assertIn({"kind": "scanner_run", "ref": "scan:1"}, basis)
        self.assertEqual(engine.kwargs["event_id"], "advisory:event")
        self.assertEqual(engine.kwargs["lineage_path_edge_ids"], ["edge:1"])

    def test_already_exact_advisory_adds_no_synthetic_resolution_evidence(self) -> None:
        engine = _CapturingEngine()
        assess_advisory_revision(
            engine,
            {
                "event_revision_id": "advisory:revision",
                "upstream_refs": ["git:upstream@abc"],
                "identity_resolution": {"status": "already_exact"},
            },
            subject_revision="git:subject@def",
            evidence=[],
            basis=[{"kind": "manual_review", "ref": "review:1"}],
        )
        self.assertEqual(
            engine.kwargs["basis"],
            [
                {"kind": "advisory_revision", "ref": "advisory:revision"},
                {"kind": "manual_review", "ref": "review:1"},
            ],
        )

    def test_missing_event_revision_id_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "event_revision.event_revision_id"):
            assess_advisory_revision(
                _CapturingEngine(),
                {"upstream_refs": ["git:upstream@abc"]},
                subject_revision="git:subject@def",
                evidence=[],
                basis=[{"kind": "manual_review", "ref": "review:1"}],
            )


if __name__ == "__main__":
    unittest.main()
