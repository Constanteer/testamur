from __future__ import annotations

import unittest

from testamur.contracts import (
    ObjectKind,
    classify_object_ref,
    durable_object_kind,
    error_envelope,
    object_envelope,
)


class TestamurContractsTest(unittest.TestCase):
    def test_known_durable_prefixes_classify_without_store_lookup(self) -> None:
        cases = {
            "tst:run:canonical": ObjectKind.RUN,
            "wtn:run:historical": ObjectKind.RUN,
            "tst:obs:def": ObjectKind.OBSERVATION,
            "tst:verification:ghi": ObjectKind.VERIFICATION,
            "tst:source:src": ObjectKind.SOURCE,
            "tst:revision:rev": ObjectKind.REVISION,
            "tst:snapshot:snap": ObjectKind.SNAPSHOT,
            "tst:record:record": ObjectKind.RECORD,
            "tst:record-revision:r2": ObjectKind.RECORD_REVISION,
            "tst:relation:edge": ObjectKind.RELATION,
            "tst:watch:watch": ObjectKind.WATCH,
            "tst:watch-revision:r2": ObjectKind.WATCH_REVISION,
            "tst:watch-eval:e1": ObjectKind.WATCH_EVALUATION,
            "tst:alert:a1": ObjectKind.ALERT,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                ref = classify_object_ref(raw)
                self.assertEqual(ref.kind, expected)
                self.assertTrue(ref.durable)
                self.assertEqual(ref.value, raw)
                self.assertEqual(durable_object_kind(raw), expected)

    def test_canonical_and_historical_run_refs_are_both_readable(self) -> None:
        canonical = classify_object_ref("tst:run:abc")
        historical = classify_object_ref("wtn:run:abc")
        self.assertEqual(canonical.kind, ObjectKind.RUN)
        self.assertEqual(historical.kind, ObjectKind.RUN)
        self.assertTrue(canonical.durable)
        self.assertTrue(historical.durable)

    def test_longer_prefixes_win_for_revision_kinds(self) -> None:
        record = classify_object_ref("tst:record-revision:abc")
        self.assertEqual(record.kind, ObjectKind.RECORD_REVISION)
        watch = classify_object_ref("tst:watch-revision:abc")
        self.assertEqual(watch.kind, ObjectKind.WATCH_REVISION)
        evaluation = classify_object_ref("tst:watch-eval:abc")
        self.assertEqual(evaluation.kind, ObjectKind.WATCH_EVALUATION)

    def test_non_durable_values_remain_generic_targets(self) -> None:
        for raw in ("result.json", "claim:alpha", "nested/path.txt"):
            with self.subTest(raw=raw):
                ref = classify_object_ref(raw)
                self.assertEqual(ref.kind, ObjectKind.TARGET)
                self.assertFalse(ref.durable)
                self.assertIsNone(durable_object_kind(raw))

    def test_empty_or_prefix_only_refs_fail_explicitly(self) -> None:
        with self.assertRaises(ValueError):
            classify_object_ref("")
        for raw in (
            "tst:run:",
            "wtn:run:",
            "tst:obs:",
            "tst:verification:",
            "tst:source:",
            "tst:revision:",
            "tst:snapshot:",
            "tst:record:",
            "tst:record-revision:",
            "tst:relation:",
            "tst:watch:",
            "tst:watch-revision:",
            "tst:watch-eval:",
            "tst:alert:",
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    classify_object_ref(raw)

    def test_error_envelope_is_stable_and_does_not_hide_details(self) -> None:
        value = error_envelope(
            "not_found",
            "object does not exist",
            details={"ref": "tst:obs:missing"},
        )
        self.assertEqual(value["ok"], False)
        self.assertEqual(value["schema"], "testamur.error.v1")
        self.assertEqual(value["error"]["code"], "not_found")
        self.assertEqual(value["error"]["details"]["ref"], "tst:obs:missing")

    def test_object_envelope_preserves_reference_and_payload(self) -> None:
        ref = classify_object_ref("tst:obs:abc")
        value = object_envelope(ref, {"status": "captured"})
        self.assertTrue(value["ok"])
        self.assertEqual(value["schema"], "testamur.object.v1")
        self.assertEqual(
            value["object"],
            {"kind": "observation", "ref": "tst:obs:abc", "durable": True},
        )
        self.assertEqual(value["data"], {"status": "captured"})


if __name__ == "__main__":
    unittest.main()
