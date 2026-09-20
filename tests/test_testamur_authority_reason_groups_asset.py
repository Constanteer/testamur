from __future__ import annotations

import unittest
from pathlib import Path

from testamur.web_app import dispatch_web_get


WEB_ROOT = Path(__file__).parents[1] / "testamur" / "web"


class AuthorityReasonGroupsAssetTest(unittest.TestCase):
    def test_renderer_consumes_only_canonical_reason_groups_for_classification(self) -> None:
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

    def test_raw_denial_reasons_are_audit_only_and_preserved_separately(self) -> None:
        script = (WEB_ROOT / "authority_reason_groups.js").read_text(encoding="utf-8")
        self.assertIn("Raw canonical denial reasons", script)
        self.assertIn("renderRawReasons", script)
        self.assertIn("renderBlockedReasons", script)
        self.assertIn("Raw reasons are audit-only", script)
        self.assertIn("never\n  // inspected to derive a category, permission, validity, or reachability", script)
        self.assertNotIn("failure_reasons.includes", script)

    def test_renderer_is_a_real_production_asset_loaded_before_authority_ui(self) -> None:
        response = dispatch_web_get(None, "/authority_reason_groups.js")  # type: ignore[arg-type]
        self.assertEqual(200, response["status"])
        self.assertEqual("text/javascript; charset=utf-8", response["headers"]["Content-Type"])
        body = bytes(response["body"]).decode("utf-8")
        self.assertIn("testamurAuthorityReasonGroups", body)

        index = bytes(dispatch_web_get(None, "/")["body"]).decode("utf-8")  # type: ignore[arg-type]
        helper = index.index('/authority_reason_groups.js')
        workbench = index.index('/authority.js')
        self.assertLess(helper, workbench)

    def test_blocked_cards_delegate_grouping_to_canonical_renderer(self) -> None:
        script = (WEB_ROOT / "authority.js").read_text(encoding="utf-8")
        self.assertIn("testamurAuthorityReasonGroups", script)
        self.assertIn("renderBlockedReasons(item, esc)", script)
        self.assertIn("no client-side classification is attempted", script)
        self.assertNotIn("const reasons = list(item.reasons", script)
        self.assertNotIn("failure_reasons).map", script)
        self.assertNotIn("reason.startsWith", script)
        self.assertNotIn("reason.includes", script)


if __name__ == "__main__":
    unittest.main()
