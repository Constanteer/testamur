from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from testamur.policy import PolicyStore
from testamur.product_adapters import canonical_product_extensions
from testamur.product_service import TestamurProductService
from testamur.temporal_model import (
    TemporalAssertion,
    TemporalBasis,
    TemporalEvent,
    TemporalProjection,
)
from testamur.temporal_store import TemporalStore
from testamur.work_session import WorkSessionStore


class _RelianceView:
    def get(self, ref: str):
        return None

    def blast_radius(self, *, scope_ref: str, changed_object_refs):
        changed = list(changed_object_refs)
        return {
            "scope_ref": scope_ref,
            "changed_object_refs": changed,
            "affected_receipt_count": 1,
            "affected_reliant_refs": ["tst:record:downstream"],
            "semantics": {
                "actual_reliance_only": True,
                "change_implies_reconsideration": True,
                "change_implies_false": False,
            },
        }


def _observed(value: str) -> TemporalAssertion:
    return TemporalAssertion(value, basis=TemporalBasis.OBSERVED)


class TestamurProductAdaptersTest(unittest.TestCase):
    def test_policy_work_session_and_temporal_are_canonically_wired(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "testamur.sqlite3"
            sessions = WorkSessionStore(database)
            extensions = canonical_product_extensions(
                database, work_session_store=sessions
            )
            service = TestamurProductService(database, extensions=extensions)

            policy = PolicyStore(database).register(
                scope_ref="scope:fixture",
                purpose="release.use",
                target_kind="demo.result",
                definition={"required_assurances": []},
            )
            session = sessions.start_session(
                initiating_actor_ref="actor:fixture",
                host_environment="test",
            )

            policy_result = service.get_object(policy["policy_id"])
            session_result = service.get_object(session.session_id)

            self.assertTrue(policy_result["ok"])
            self.assertEqual(policy_result["object"]["kind"], "policy")
            self.assertEqual(policy_result["data"]["policy_id"], policy["policy_id"])
            self.assertTrue(session_result["ok"])
            self.assertEqual(session_result["object"]["kind"], "work_session")
            self.assertEqual(
                session_result["data"]["session_id"], session.session_id
            )
            self.assertFalse(extensions.capabilities()["impact"])
            self.assertTrue(extensions.capabilities()["temporal"])
            self.assertTrue(extensions.capabilities()["temporal_events"])
            self.assertNotIn("reliance", extensions.capabilities()["object_kinds"])

            temporal = service.temporal(
                policy["policy_id"],
                {"clauses": [{"mode": "KNOWN_AT", "at": "2030-01-01T00:00:00Z"}]},
            )
            self.assertTrue(temporal["ok"])
            self.assertEqual(temporal["items"], [])
            self.assertFalse(temporal["semantics"]["generic_as_of_used"])
            self.assertTrue(temporal["semantics"]["object_ref_scoped"])
            self.assertTrue(temporal["semantics"]["perspective_fail_closed"])
            self.assertFalse(temporal["semantics"]["time_cut_selects_perspective"])
            sessions.close()

    def test_temporal_product_read_scopes_perspective_before_time_cut(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "testamur.sqlite3"
            extensions = canonical_product_extensions(database)
            service = TestamurProductService(database, extensions=extensions)
            store = TemporalStore(database)
            target = "tst:record:target"
            other = "tst:record:other"

            store.append_projection(
                TemporalProjection(
                    target,
                    _observed("2025-01-01T10:00:00Z"),
                    perspective="node:A",
                )
            )
            store.append_projection(
                TemporalProjection(
                    other,
                    _observed("2025-01-01T10:00:00Z"),
                    perspective="node:B",
                )
            )

            query = {
                "clauses": [
                    {"mode": "KNOWN_AT", "at": "2025-01-02T00:00:00Z"}
                ]
            }
            scoped = service.temporal(target, query)
            self.assertTrue(scoped["ok"])
            self.assertEqual(len(scoped["items"]), 1)
            self.assertEqual(
                scoped["items"][0]["projection"]["object_ref"], target
            )
            self.assertEqual(
                scoped["items"][0]["projection"]["perspective"], "node:A"
            )

            store.append_projection(
                TemporalProjection(
                    target,
                    _observed("2025-01-01T12:00:00Z"),
                    perspective="node:B",
                )
            )
            ambiguous = service.temporal(
                target,
                {
                    "clauses": [
                        {"mode": "KNOWN_AT", "at": "2025-01-01T11:00:00Z"}
                    ]
                },
            )
            self.assertFalse(ambiguous["ok"])
            self.assertEqual(
                ambiguous["error"]["code"], "invalid_temporal_query"
            )
            self.assertIn("multiple perspectives", ambiguous["error"]["message"])

            explicit = service.temporal(
                target,
                {
                    **query,
                    "perspective": "node:A",
                },
            )
            self.assertTrue(explicit["ok"])
            self.assertEqual(len(explicit["items"]), 1)
            self.assertEqual(
                explicit["items"][0]["projection"]["perspective"], "node:A"
            )

    def test_temporal_events_are_separate_subject_scoped_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "testamur.sqlite3"
            extensions = canonical_product_extensions(database)
            service = TestamurProductService(database, extensions=extensions)
            store = TemporalStore(database)
            target = "tst:record:target"
            other = "tst:record:other"

            store.append_event(
                TemporalEvent(
                    "late_observation",
                    target,
                    _observed("2025-01-01T10:00:00Z"),
                    event_time=TemporalAssertion(
                        "2020-01-01T00:00:00Z",
                        basis=TemporalBasis.ARCHIVE_OBSERVATION,
                        source_ref="archive:1",
                    ),
                    perspective="node:A",
                )
            )
            store.append_event(
                TemporalEvent(
                    "late_observation",
                    other,
                    _observed("2025-01-01T10:00:00Z"),
                    perspective="node:B",
                )
            )

            ordinary = service.temporal(
                target,
                {"clauses": [{"mode": "KNOWN_AT", "at": "2030-01-01T00:00:00Z"}]},
            )
            self.assertTrue(ordinary["ok"])
            self.assertEqual(ordinary["items"], [])

            events = service.temporal_events(target)
            self.assertTrue(events["ok"])
            self.assertEqual(events["schema"], "testamur.product.temporal-events.v1")
            self.assertEqual(len(events["items"]), 1)
            self.assertEqual(events["items"][0]["event"]["subject_ref"], target)
            self.assertEqual(events["items"][0]["event"]["perspective"], "node:A")
            self.assertEqual(
                events["items"][0]["event"]["event_time"]["instant"],
                "2020-01-01T00:00:00.000000Z",
            )
            self.assertTrue(events["semantics"]["separate_from_state_view"])
            self.assertFalse(events["semantics"]["recorded_time_is_event_time"])

            store.append_event(
                TemporalEvent(
                    "retrospective_correction",
                    target,
                    _observed("2025-01-01T12:00:00Z"),
                    perspective="node:B",
                )
            )
            ambiguous = service.temporal_events(
                target,
                {"recorded_by": "2025-01-01T11:00:00Z"},
            )
            self.assertFalse(ambiguous["ok"])
            self.assertEqual(
                ambiguous["error"]["code"], "invalid_temporal_event_query"
            )
            self.assertIn("multiple perspectives", ambiguous["error"]["message"])

            kind_scoped = service.temporal_events(
                target,
                {"event_kinds": "late_observation"},
            )
            self.assertTrue(kind_scoped["ok"])
            self.assertEqual(len(kind_scoped["items"]), 1)
            self.assertEqual(kind_scoped["items"][0]["event"]["kind"], "late_observation")

            explicit = service.temporal_events(
                target,
                {"perspective": "node:A"},
            )
            self.assertTrue(explicit["ok"])
            self.assertEqual(len(explicit["items"]), 1)
            self.assertEqual(explicit["items"][0]["event"]["perspective"], "node:A")

    def test_reliance_is_not_fabricated_without_explicit_policy_evidence_view(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "testamur.sqlite3"
            sessions = WorkSessionStore(database)
            extensions = canonical_product_extensions(
                database, work_session_store=sessions
            )
            service = TestamurProductService(database, extensions=extensions)
            result = service.get_object("tst:reliance:missing")
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["code"], "unsupported_object_kind")
            sessions.close()

    def test_explicit_reliance_scope_wires_exact_product_impact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "testamur.sqlite3"
            extensions = canonical_product_extensions(
                database,
                reliance_store=_RelianceView(),
                impact_scope_ref="scope:fixture",
            )
            service = TestamurProductService(database, extensions=extensions)
            result = service.impact("tst:record:upstream")
            self.assertTrue(result["ok"])
            self.assertEqual(result["schema"], "testamur.product.impact.v1")
            self.assertEqual(result["impact"]["scope_ref"], "scope:fixture")
            self.assertEqual(
                result["impact"]["changed_object_refs"], ["tst:record:upstream"]
            )
            self.assertEqual(
                result["impact"]["affected_reliant_refs"],
                ["tst:record:downstream"],
            )
            self.assertTrue(result["semantics"]["actual_durable_reliance_only"])
            self.assertFalse(result["semantics"]["change_implies_invalid"])
            self.assertFalse(result["semantics"]["stale_implies_false"])

    def test_integrated_extensions_expose_registered_monitor_target_providers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "testamur.sqlite3"
            extensions = canonical_product_extensions(
                database,
                monitor_target_providers={
                    "fixture": lambda config: {
                        "locator": f"https://example.invalid/{config['target']}"
                    }
                },
            )
            self.assertEqual(
                extensions.capabilities()["monitor_target_providers"],
                ["fixture"],
            )
            resolved = extensions.monitor_target_provider("fixture")({"target": "spec"})
            self.assertEqual(resolved["locator"], "https://example.invalid/spec")

    def test_impact_scope_without_reliance_store_does_not_fabricate_capability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "testamur.sqlite3"
            extensions = canonical_product_extensions(
                database, impact_scope_ref="scope:fixture"
            )
            self.assertFalse(extensions.capabilities()["impact"])


if __name__ == "__main__":
    unittest.main()
