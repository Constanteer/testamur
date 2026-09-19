from __future__ import annotations

import unittest

from testamur.authority_web_api import dispatch_authority_web_api


class _FakeAuthorityService:
    def authority_subject(self, ref):
        return {
            "ok": True,
            "schema": "testamur.product.authority-subject.v1",
            "subject": {"subject_ref": ref, "kind": "credential"},
            "incoming_edges": [{"edge_id": "edge:exposes", "target_ref": ref}],
            "outgoing_edges": [{"edge_id": "edge:auth", "source_ref": ref}],
            "semantics": {"lineage_is_not_authority": True, "connectivity_is_not_authorization": True},
        }

    def authority_explain(self, edge_ids, *, starting_ref=None, expected_target_ref=None, supporting_edge_ids=None):
        return {
            "ok": True,
            "schema": "testamur.product.authority-path-explanation.v1",
            "result": {
                "edge_ids": list(edge_ids),
                "starting_ref": starting_ref,
                "expected_target_ref": expected_target_ref,
                "supporting_edge_ids": list(supporting_edge_ids or []),
            },
        }

    def authority_reach(self, ref, *, compromise_model, max_depth=8, max_paths=256, expansion_budget=10000, as_of=None):
        return {
            "ok": True,
            "schema": "testamur.product.authority-reachability.v1",
            "result": {
                "schema_version": "testamur.authority-reachability.v1",
                "mode": "reachability",
                "starting_subject_ref": ref,
                "reachable_subjects": [ref],
                "actionable_capabilities": [],
                "blocked_transitions": [{
                    "edge_id": "edge:blocked",
                    "source_ref": ref,
                    "target_ref": "repo:private",
                    "relation": "CAN_ACT_AS",
                    "failure_reasons": ["audience_mismatch"],
                    "unresolved_constraints": ["device_binding"],
                    "path_edge_ids": [],
                    "supporting_edge_ids": ["edge:accepts-token"],
                    "evidence_state": "blocked",
                }],
                "trust_boundary_crossings": [],
            },
        }

    def authority_blast(self, refs, *, compromise_model, max_depth=8, max_paths=256, expansion_budget=10000, as_of=None):
        return {
            "ok": True,
            "schema": "testamur.product.authority-blast-radius.v1",
            "result": {
                "schema_version": "testamur.authority-blast-radius.v1",
                "mode": "blast_radius",
                "compromised_refs": list(refs),
                "reachable_subjects": list(refs),
                "actionable_capabilities": [],
                "blocked_transitions": [],
                "trust_boundary_crossings": [],
            },
        }


class AuthorityWebApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = _FakeAuthorityService()

    def test_subject_returns_canonical_edges_without_reachability_inference(self) -> None:
        result = dispatch_authority_web_api(self.service, "/v1/authority/subject?ref=credential%3Astolen")
        assert result is not None
        self.assertEqual(result["schema"], "testamur.product.authority-subject.v1")
        self.assertEqual(result["subject"]["subject_ref"], "credential:stolen")
        self.assertEqual(result["incoming_edges"][0]["edge_id"], "edge:exposes")
        self.assertTrue(result["semantics"]["connectivity_is_not_authorization"])

    def test_explain_requires_exact_edge_ids_and_keeps_support_separate(self) -> None:
        result = dispatch_authority_web_api(
            self.service,
            "/v1/authority/explain?edge_id=edge%3Aread&edge_id=edge%3Aauth&support_edge_id=edge%3Aaccepts&start=runtime%3A1&target=session%3A1",
        )
        assert result is not None
        explanation = result["result"]
        self.assertEqual(explanation["edge_ids"], ["edge:read", "edge:auth"])
        self.assertEqual(explanation["supporting_edge_ids"], ["edge:accepts"])
        self.assertEqual(explanation["starting_ref"], "runtime:1")
        self.assertEqual(explanation["expected_target_ref"], "session:1")

    def test_explain_rejects_empty_or_missing_path_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one edge_id"):
            dispatch_authority_web_api(self.service, "/v1/authority/explain?start=a")
        with self.assertRaisesRegex(ValueError, "non-empty"):
            dispatch_authority_web_api(self.service, "/v1/authority/explain?edge_id=")

    def test_subject_and_explain_reject_unknown_semantic_shortcuts(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not accept"):
            dispatch_authority_web_api(self.service, "/v1/authority/subject?ref=a&lineage=true")
        with self.assertRaisesRegex(ValueError, "does not accept"):
            dispatch_authority_web_api(self.service, "/v1/authority/explain?edge_id=e&connected=true")

    def test_reach_returns_stable_web_projection_with_exact_block_reason(self) -> None:
        result = dispatch_authority_web_api(
            self.service,
            "/v1/authority/reach?ref=credential%3Astolen&compromise_model=credential_theft",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["schema"], "testamur.web.authority-view.v1")
        blocked = result["blocked_transitions"][0]
        self.assertEqual(blocked["reasons"], ["audience_mismatch"])
        self.assertEqual(blocked["unresolved_constraints"], ["device_binding"])
        self.assertEqual(blocked["path_edge_ids"], [])
        self.assertEqual(blocked["supporting_edge_ids"], ["edge:accepts-token"])
        self.assertTrue(result["semantics"]["connectivity_is_not_authorization"])
        self.assertTrue(result["semantics"]["lineage_is_not_authority"])

    def test_blast_requires_explicit_refs_and_preserves_only_those_seeds(self) -> None:
        result = dispatch_authority_web_api(
            self.service,
            "/v1/authority/blast-radius?ref=credential%3Aa&ref=principal%3Ab&compromise_model=credential_theft",
        )
        assert result is not None
        self.assertEqual(result["compromised_refs"], ["credential:a", "principal:b"])
        self.assertTrue(result["semantics"]["affectedness_does_not_seed_compromise"])

    def test_reach_rejects_multiple_refs_instead_of_merging_identity(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly one"):
            dispatch_authority_web_api(
                self.service,
                "/v1/authority/reach?ref=a&ref=b&compromise_model=credential_theft",
            )

    def test_runtime_budgets_are_bounded_and_unknown_fields_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_depth"):
            dispatch_authority_web_api(
                self.service,
                "/v1/authority/reach?ref=a&compromise_model=x&max_depth=0",
            )
        with self.assertRaisesRegex(ValueError, "does not accept"):
            dispatch_authority_web_api(
                self.service,
                "/v1/authority/reach?ref=a&compromise_model=x&affected=true",
            )

    def test_non_authority_route_is_not_claimed(self) -> None:
        self.assertIsNone(dispatch_authority_web_api(self.service, "/v1/impact?ref=x"))


if __name__ == "__main__":
    unittest.main()
