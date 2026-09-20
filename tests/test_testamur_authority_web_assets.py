from __future__ import annotations

import unittest
from pathlib import Path


WEB_ROOT = Path(__file__).parents[1] / "testamur" / "web"


class AuthorityWebAssetsTest(unittest.TestCase):
    """Lock the Authority workbench to canonical projections and evidence semantics."""

    def test_authority_workbench_consumes_canonical_reach_projection(self) -> None:
        script = (WEB_ROOT / "authority.js").read_text(encoding="utf-8")
        self.assertIn("/v1/authority/reach", script)
        self.assertIn("candidate_capabilities", script)
        self.assertIn("inherited_capability_budget", script)
        self.assertIn("failed_constraints", script)
        self.assertIn("unresolved_constraints", script)
        self.assertIn("trust_boundary_crossings", script)

    def test_traversed_path_and_supporting_evidence_remain_separate(self) -> None:
        script = (WEB_ROOT / "authority.js").read_text(encoding="utf-8")
        self.assertIn("path_edge_ids", script)
        self.assertIn("supporting_edge_ids", script)
        self.assertIn("Authority path", script)
        self.assertIn("Supporting evidence", script)
        self.assertNotIn("path_edge_ids.concat", script)
        self.assertNotIn("supporting_edge_ids.concat", script)

    def test_ui_states_that_non_authority_graphs_do_not_grant_permission(self) -> None:
        script = (WEB_ROOT / "authority.js").read_text(encoding="utf-8")
        self.assertIn("Connectivity, material lineage, reliance and affectedness do not grant permission", script)
        self.assertIn("Unresolved — not assumed valid", script)

    def test_authority_styles_are_packaged_with_the_workbench(self) -> None:
        styles = (WEB_ROOT / "authority.css").read_text(encoding="utf-8")
        self.assertIn(".authority-query", styles)
        self.assertIn(".authority-blocked", styles)
        self.assertIn(".authority-budget", styles)
        self.assertIn(".authority-crossing", styles)


if __name__ == "__main__":
    unittest.main()
