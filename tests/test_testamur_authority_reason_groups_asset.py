from __future__ import annotations

import unittest
from pathlib import Path


WEB_ROOT = Path(__file__).parents[1] / "testamur" / "web"


class AuthorityReasonGroupsAssetTest(unittest.TestCase):
    def test_renderer_consumes_only_canonical_reason_groups(self) -> None:
        script = (WEB_ROOT / "authority_reason_groups.js").read_text(encoding="utf-8")
        self.assertIn("item.reason_groups", script)
        self.assertIn("credential_or_token", script)
        self.assertIn("capability_or_delegation", script)
        self.assertIn("approval_or_mfa", script)
        self.assertIn("trust_boundary_policy", script)
        self.assertIn("other", script)
        self.assertNotIn("item.reasons.includes", script)
        self.assertNotIn("startsWith", script)
        self.assertNotIn("findPath", script)
        self.assertNotIn("shortestPath", script)

    def test_unknown_reasons_have_explicit_unclassified_surface(self) -> None:
        script = (WEB_ROOT / "authority_reason_groups.js").read_text(encoding="utf-8")
        self.assertIn("Other / unclassified", script)
        self.assertIn("presentation-only", script)
        self.assertIn("does not classify reason strings", script)


if __name__ == "__main__":
    unittest.main()
