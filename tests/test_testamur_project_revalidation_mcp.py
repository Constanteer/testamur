from __future__ import annotations

import unittest
from unittest.mock import patch

from testamur import source_gateway_mcp as base
from testamur import source_gateway_project_mcp as project_mcp


class ProjectRevalidationMcpTests(unittest.TestCase):
    def test_tool_contract_preserves_semantic_boundaries(self) -> None:
        tool = project_mcp.PROJECT_REVALIDATION_TOOL
        self.assertEqual(tool["name"], "testamur.project_advisory_revalidation")
        description = tool["description"].lower()
        self.assertIn("not an invalidity", description)
        self.assertIn("not generic verification", description)

    def test_projection_delegates_to_canonical_project_surface(self) -> None:
        detail = {
            "ok": True,
            "project": {"project_id": "prj_1"},
            "supply_chain": {
                "advisory_revalidation": {
                    "work_items": [{"reason": "affectedness-review-required"}],
                    "work_item_count": 1,
                }
            },
        }
        with patch.object(base.TestamurProductService, "integrated", return_value=object()), patch.object(
            base, "project_with_advisory_reviews", return_value=detail
        ) as canonical:
            payload = project_mcp._project_revalidation({"project_ref": "prj_1"})
        canonical.assert_called_once()
        self.assertEqual(payload["advisory_revalidation"]["work_item_count"], 1)
        semantics = payload["semantics"]
        self.assertTrue(semantics["changed_is_not_invalid"])
        self.assertTrue(semantics["changed_is_not_affectedness_verdict"])
        self.assertTrue(semantics["stale_is_not_false"])
        self.assertFalse(semantics["generic_trust_score_used"])

    def test_install_adds_tool_without_replacing_existing_tools(self) -> None:
        before = {tool["name"] for tool in base.TOOLS}
        project_mcp._install()
        after = {tool["name"] for tool in base.TOOLS}
        self.assertTrue(before.issubset(after))
        self.assertIn("testamur.project_advisory_revalidation", after)


if __name__ == "__main__":
    unittest.main()
