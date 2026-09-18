#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
MODE="${1:-smoke}"

# Make local gate logs self-identifying so release evidence cannot accidentally
# be attributed to a different checkout. Git metadata is diagnostic only: an
# exported source tree without .git remains fully testable.
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GATE_HEAD="$(git rev-parse HEAD)"
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    GATE_TREE_STATE="dirty-tracked"
  else
    GATE_TREE_STATE="clean-tracked"
  fi
  printf 'testamur-gate head=%s tree=%s mode=%s\n' "$GATE_HEAD" "$GATE_TREE_STATE" "$MODE"
  if [[ "$MODE" == "release" && "$GATE_TREE_STATE" != "clean-tracked" ]]; then
    echo "release mode requires a clean tracked checkout so evidence identifies an exact commit" >&2
    exit 2
  fi
else
  printf 'testamur-gate head=unavailable tree=exported mode=%s\n' "$MODE"
fi

command -v "$PYTHON_BIN" >/dev/null || {
  echo "missing Python executable: $PYTHON_BIN" >&2
  exit 127
}

"$PYTHON_BIN" - <<'PY'
import importlib.util
import sys
print(f"python={sys.executable}")
print(f"version={sys.version.split()[0]}")
if importlib.util.find_spec("pytest") is None:
    raise SystemExit("pytest is not installed in this Python environment")
PY

compile_core() {
  # Compile the whole shipped package rather than a hand-maintained subset. This
  # catches syntax/import-surface regressions in runtime, revision compatibility,
  # ProductService and Web modules before pytest starts.
  "$PYTHON_BIN" -m compileall -q testamur
  "$PYTHON_BIN" -m py_compile mathhub.py
}

run_smoke() {
  compile_core
  "$PYTHON_BIN" -m pytest -q -x \
    tests/test_testamur_contracts.py \
    tests/test_testamur_source_store.py \
    tests/test_testamur_record_store.py \
    tests/test_testamur_record_source.py \
    tests/test_testamur_blob_diff.py \
    tests/test_testamur_watch_store.py \
    tests/test_testamur_environment.py \
    tests/test_testamur_environment_status.py \
    tests/test_testamur_receipts.py \
    tests/test_testamur_verification_store.py \
    tests/test_testamur_entrypoint.py \
    tests/test_testamur_cli_e2e.py
}

case "$MODE" in
  smoke)
    run_smoke
    ;;
  release)
    compile_core
    PYTHON_BIN="$PYTHON_BIN" bash scripts/testamur_release_gate.sh
    ;;
  full)
    compile_core
    "$PYTHON_BIN" -m pytest -q tests/test_testamur_*.py
    ;;
  *)
    echo "usage: $0 [smoke|release|full]" >&2
    exit 2
    ;;
esac
