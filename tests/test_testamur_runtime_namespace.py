from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from testamur.runtime_protocol import (
    LEGACY_PROTOCOL_VERSION,
    PROTOCOL_VERSION,
    RunState,
    RuntimeProtocol,
    RuntimeRun,
    canonical_hash,
    canonical_json,
)
from testamur.runtime_store import TestamurProtocolLedger


class _SQLiteStore:
    """Minimal storage boundary required by the canonical runtime ledger."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def _request(operation: str, key: str, **extra) -> dict:
    request = {
        "protocol": PROTOCOL_VERSION,
        "client_id": "namespace:test",
        "request_id": f"req-{key}",
        "idempotency_key": key,
        "operation": operation,
        "payload": extra.pop("payload", {}),
    }
    request.update(extra)
    return request


def _seed_legacy_active_run(path: Path) -> str:
    """Create the pre-Testamur persisted layout without importing legacy code."""

    client_id = "namespace:test"
    payload = {"purpose": "historical-runtime-compatibility"}
    identity = {
        "protocol": LEGACY_PROTOCOL_VERSION,
        "client_id": client_id,
        "idempotency_key": "historical-begin",
        "payload": payload,
    }
    run_id = f"wtn:run:{canonical_hash(identity)}"
    empty = RuntimeRun(
        run_id=run_id,
        client_id=client_id,
        begin_payload=payload,
        state=RunState.ACTIVE,
        events=(),
        protocol=LEGACY_PROTOCOL_VERSION,
    )

    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE witness_runtime_runs(
              run_id TEXT PRIMARY KEY,
              client_id TEXT NOT NULL,
              begin_payload_json TEXT NOT NULL,
              created_record_digest TEXT NOT NULL
            );
            CREATE TABLE witness_runtime_events(
              event_id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL REFERENCES witness_runtime_runs(run_id),
              sequence INTEGER NOT NULL,
              operation TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              UNIQUE(run_id, sequence)
            );
            """
        )
        conn.execute(
            "INSERT INTO witness_runtime_runs VALUES(?,?,?,?)",
            (run_id, client_id, canonical_json(payload), empty.record_digest),
        )
    return run_id


class TestamurRuntimeNamespaceTest(unittest.TestCase):
    def test_runtime_store_is_owned_by_testamur(self) -> None:
        self.assertTrue(TestamurProtocolLedger.__module__.startswith("testamur."))
        self.assertNotIn("Witness", TestamurProtocolLedger.__name__)
        self.assertTrue(RuntimeProtocol.__module__.startswith("testamur."))

    def test_canonical_runtime_reopens_current_layout_without_legacy_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.sqlite3"
            store = _SQLiteStore(path)
            protocol = RuntimeProtocol(TestamurProtocolLedger(store))

            started = protocol.call(
                _request("begin_run", "begin", payload={"purpose": "namespace-migration"})
            )
            run_id = started["result"]["run_id"]
            self.assertTrue(run_id.startswith("tst:run:"))
            finished = protocol.call(
                _request(
                    "finish_run",
                    "finish",
                    run_id=run_id,
                    sequence=1,
                    payload={"outcome": "success", "exit_code": 0},
                )
            )

            reopened = RuntimeProtocol(TestamurProtocolLedger(_SQLiteStore(path)))
            record = reopened.call(_request("get_run", "get", run_id=run_id))["result"]

            self.assertEqual(record["record_digest"], finished["result"]["record_digest"])
            self.assertEqual(record["protocol"], PROTOCOL_VERSION)
            self.assertEqual(record["state"], "finished")

    def test_historical_witness_layout_reopens_read_only_and_new_writes_use_testamur_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.sqlite3"
            legacy_run_id = _seed_legacy_active_run(path)

            runtime = RuntimeProtocol(TestamurProtocolLedger(_SQLiteStore(path)))
            historical = runtime.call(
                _request("get_run", "historical-get", run_id=legacy_run_id)
            )
            self.assertEqual(historical["protocol"], PROTOCOL_VERSION)
            self.assertEqual(historical["result"]["protocol"], LEGACY_PROTOCOL_VERSION)
            self.assertEqual(historical["result"]["run_id"], legacy_run_id)

            mutation = runtime.safe_call(
                _request(
                    "observe_input",
                    "historical-mutation",
                    run_id=legacy_run_id,
                    sequence=1,
                    payload={"source": "legacy"},
                )
            )
            self.assertFalse(mutation["ok"])
            self.assertEqual(mutation["error"]["code"], "run_state_conflict")

            current = runtime.call(
                _request("begin_run", "current-begin", payload={"purpose": "new-write"})
            )
            self.assertEqual(current["protocol"], PROTOCOL_VERSION)
            self.assertTrue(current["result"]["run_id"].startswith("tst:run:"))


if __name__ == "__main__":
    unittest.main()
