from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "evidence-demo"


class EvidenceDemoContractTests(unittest.TestCase):
    def test_manifest_describes_offline_source_to_revalidation_flow(self) -> None:
        manifest = json.loads((DEMO / "demo.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "testamur.demo.evidence-flow.v1")
        self.assertTrue(manifest["project"]["disposable"])
        self.assertFalse(manifest["project"]["network_required"])
        self.assertEqual([item["id"] for item in manifest["source"]["revisions"]], ["baseline", "current"])
        self.assertEqual(manifest["compare"]["from"], "baseline")
        self.assertEqual(manifest["compare"]["to"], "current")
        self.assertTrue(manifest["impact"]["requires_explicit_affectedness_decision"])
        self.assertTrue(manifest["revalidation"]["explicit"])
        self.assertFalse(manifest["revalidation"]["automatic_invalidity_from_change"])

    def test_manifest_paths_and_expected_change_match_fixture(self) -> None:
        manifest = json.loads((DEMO / "demo.json").read_text(encoding="utf-8"))
        revision_paths = {item["id"]: DEMO / item["path"] for item in manifest["source"]["revisions"]}
        baseline = revision_paths["baseline"].read_text(encoding="utf-8")
        current = revision_paths["current"].read_text(encoding="utf-8")
        self.assertIn("30 days", baseline)
        self.assertIn("14 days", current)
        self.assertNotEqual(baseline, current)
        candidate = DEMO / manifest["impact"]["candidate"]
        self.assertTrue(candidate.is_file())
        downstream = candidate.read_text(encoding="utf-8")
        self.assertIn("30-day", downstream)

    def test_semantic_boundaries_remain_explicit(self) -> None:
        manifest = json.loads((DEMO / "demo.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(manifest["semantic_boundaries"]),
            {
                "recorded != verified",
                "fetched != relied",
                "changed != invalid",
                "stale != false",
                "EXPOSED_TO_MODEL != RELIED",
                "recorded reliance provenance != affectedness",
            },
        )


if __name__ == "__main__":
    unittest.main()
