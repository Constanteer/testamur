from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from testamur.receipt_store import TestamurReceiptStore
from testamur.runtime_protocol import canonical_hash


_HASH = "sha256:" + ("a" * 64)


def _symlink(directory: Path, target: Path) -> None:
    try:
        directory.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"directory symlinks are unavailable: {exc}")


def _snapshot(path: Path) -> dict[str, object]:
    return {"kind": "file", "path": str(path), "content_hash": _HASH, "size": 3}


def _receipt(*, root: Path, run_id: str, path: Path, declared_path: str) -> dict[str, object]:
    return {
        "run_id": run_id,
        "state": "finished",
        "argv": ["tool", declared_path],
        "cwd": str(root),
        "exit_code": 0,
        "record_digest": f"sha256:{run_id}",
        "verification_implied": False,
        "replayed": False,
        "git_context": {"before": {}, "after": {}},
        "worktree_delta": {"status": "disabled"},
        "input_artifacts": [
            {
                "role": "input",
                "declared_path": declared_path,
                "resolved_path": str(path),
                "status": "captured",
                "snapshot": _snapshot(path),
            }
        ],
        "output_artifacts": [],
    }


def test_artifact_lookup_treats_filesystem_alias_as_one_path_identity() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        real_root = base / "real"
        real_root.mkdir()
        alias_root = base / "alias"
        _symlink(alias_root, real_root)
        real_source = real_root / "source.txt"
        real_source.write_text("v1\n", encoding="utf-8")
        alias_source = alias_root / "source.txt"

        store = TestamurReceiptStore(real_root / "testamur.sqlite3")
        store.record(
            _receipt(
                root=alias_root,
                run_id="wtn:run:path-alias",
                path=alias_source,
                declared_path=str(alias_source),
            )
        )

        expected_id = "tst:obs:" + canonical_hash(
            {"run_id": "wtn:run:path-alias", "role": "input", "ordinal": 0}
        )
        by_real = store.observations_for_path(real_source, root=real_root)
        by_alias = store.observations_for_path(alias_source, root=alias_root)
        assert [item["observation_id"] for item in by_real] == [expected_id]
        assert [item["observation_id"] for item in by_alias] == [expected_id]
        assert by_real[0]["resolved_path"] == str(real_source.resolve())


def test_legacy_noncanonical_resolved_path_remains_queryable() -> None:
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        real_root = base / "real"
        real_root.mkdir()
        alias_root = base / "alias"
        _symlink(alias_root, real_root)
        source = real_root / "legacy.txt"
        source.write_text("legacy\n", encoding="utf-8")

        store = TestamurReceiptStore(real_root / "testamur.sqlite3")
        store.record(
            _receipt(
                root=real_root,
                run_id="wtn:run:legacy-alias",
                path=source,
                declared_path="legacy.txt",
            )
        )

        with sqlite3.connect(store.path) as conn:
            conn.execute("DROP TRIGGER testamur_artifact_observations_no_update")
            conn.execute(
                "UPDATE testamur_artifact_observations SET resolved_path=? WHERE run_id=?",
                (str(alias_root / "legacy.txt"), "wtn:run:legacy-alias"),
            )
            conn.execute(
                """CREATE TRIGGER testamur_artifact_observations_no_update
                   BEFORE UPDATE ON testamur_artifact_observations BEGIN
                     SELECT RAISE(ABORT, 'Testamur artifact observations are immutable');
                   END"""
            )

        observations = store.observations_for_path(source, root=real_root)
        assert len(observations) == 1
        assert observations[0]["run_id"] == "wtn:run:legacy-alias"
