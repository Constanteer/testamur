from __future__ import annotations

import unittest

from testamur.web_app import dispatch_web_get


class _FakeProductService:
    def authority_subject(self, ref):
        return {
            "ok": True,
            "schema": "testamur.product.authority-subject.v1",
            "subject": {"subject_ref": ref, "kind": "credential"},
            "incoming_edges": [],
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


class AuthorityWebRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = _FakeProductService()

    def test_dispatch_web_get_routes_subject_as_canonical_inspection(self) -> None:
        response = dispatch_web_get(self.service, "/v1/authority/subject?ref=credential%3Astolen")
        self.assertEqual(response["status"], 200)
        body = response["body"]
        self.assertEqual(body["schema"], "testamur.product.authority-subject.v1")
        self.assertEqual(body["subject"]["subject_ref"], "credential:stolen")
        self.assertTrue(body["semantics"]["connectivity_is_not_authorization"])

    def test_dispatch_web_get_routes_exact_path_explanation_without_merging_support(self) -> None:
        response = dispatch_web_get(
            self.service,
            "/v1/authority/explain?edge_id=edge%3Aread&edge_id=edge%3Aauth&support_edge_id=edge%3Aaccepts&start=runtime%3A1&target=session%3A1",
        )
        self.assertEqual(response["status"], 200)
        result = response["body"]["result"]
        self.assertEqual(result["edge_ids"], ["edge:read", "edge:auth"])
        self.assertEqual(result["supporting_edge_ids"], ["edge:accepts"])

    def test_dispatch_web_get_routes_reach_through_stable_authority_projection(self) -> None:
        response = dispatch_web_get(
            self.service,
            "/v1/authority/reach?ref=credential%3Astolen&compromise_model=credential_theft",
        )
        self.assertEqual(response["status"], 200)
        body = response["body"]
        self.assertEqual(body["schema"], "testamur.web.authority-view.v1")
        blocked = body["blocked_transitions"][0]
        self.assertEqual(blocked["reasons"], ["audience_mismatch"])
        self.assertEqual(blocked["unresolved_constraints"], ["device_binding"])
        self.assertEqual(blocked["path_edge_ids"], [])
        self.assertEqual(blocked["supporting_edge_ids"], ["edge:accepts-token"])
        self.assertTrue(body["semantics"]["connectivity_is_not_authorization"])
        self.assertTrue(body["semantics"]["lineage_is_not_authority"])

    def test_dispatch_web_get_routes_blast_with_explicit_seeds_only(self) -> None:
        response = dispatch_web_get(
            self.service,
            "/v1/authority/blast-radius?ref=credential%3Aa&ref=principal%3Ab&compromise_model=credential_theft",
        )
        self.assertEqual(response["status"], 200)
        body = response["body"]
        self.assertEqual(body["compromised_refs"], ["credential:a", "principal:b"])
        self.assertTrue(body["semantics"]["affectedness_does_not_seed_compromise"])

    def test_authority_validation_errors_become_normal_web_api_errors(self) -> None:
        response = dispatch_web_get(
            self.service,
            "/v1/authority/reach?ref=a&ref=b&compromise_model=credential_theft",
        )
        self.assertEqual(response["status"], 400)
        self.assertEqual(response["body"]["error"]["code"], "invalid_argument")

        response = dispatch_web_get(self.service, "/v1/authority/explain?edge_id=")
        self.assertEqual(response["status"], 400)
        self.assertEqual(response["body"]["error"]["code"], "invalid_argument")

    def test_affectedness_query_cannot_be_used_as_implicit_compromise_evidence(self) -> None:
        response = dispatch_web_get(
            self.service,
            "/v1/authority/blast-radius?ref=a&compromise_model=credential_theft&affected=true",
        )
        self.assertEqual(response["status"], 400)
        self.assertIn("does not accept", response["body"]["error"]["message"])


if __name__ == "__main__":
    unittest.main()
