from __future__ import annotations

import unittest
from pathlib import Path

from testamur.web_app import dispatch_web_get


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

    def test_blast_radius_uses_repeated_exact_authority_seed_refs(self) -> None:
        script = (WEB_ROOT / "authority.js").read_text(encoding="utf-8")
        self.assertIn("/v1/authority/blast-radius", script)
        self.assertIn("refs.forEach(ref => query.append('ref', ref))", script)
        self.assertIn("Single-subject reachability requires exactly one authority subject", script)
        self.assertIn("Use blast-radius mode for multiple explicit compromise seeds", script)
        self.assertNotIn("lineage_ref", script)
        self.assertNotIn("affected_ref", script)
        self.assertNotIn("reliance_ref", script)

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

    def test_production_router_serves_authority_route_and_assets(self) -> None:
        # Static/SPA reads do not consult the ProductService; passing None makes
        # accidental API coupling fail loudly if routing changes later.
        page = dispatch_web_get(None, "/authority")  # type: ignore[arg-type]
        script = dispatch_web_get(None, "/authority.js")  # type: ignore[arg-type]
        styles = dispatch_web_get(None, "/authority.css")  # type: ignore[arg-type]

        self.assertEqual(page["status"], 200)
        self.assertEqual(script["status"], 200)
        self.assertEqual(styles["status"], 200)
        self.assertIn(b"Testamur", page["body"])
        self.assertIn(b"/v1/authority/reach", script["body"])
        self.assertIn(b".authority-query", styles["body"])
        self.assertEqual(script["headers"]["Content-Type"], "text/javascript; charset=utf-8")
        self.assertEqual(styles["headers"]["Content-Type"], "text/css; charset=utf-8")

        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/authority.css"', index)
        self.assertIn('src="/authority.js"', index)


if __name__ == "__main__":
    unittest.main()
