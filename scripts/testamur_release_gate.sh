#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON_BIN="${PYTHON_BIN:-python3}"

command -v "$PYTHON_BIN" >/dev/null

# Structural production/package boundary first: Testamur is the only shipped
# Python namespace. Additional Testamur-owned entrypoints (such as testamur-web)
# are projections over the same canonical runtime, never a second semantic model.
"$PYTHON_BIN" - <<'PY'
from pathlib import Path
from testamur.release_gate import audit_release_surface

result = audit_release_surface(Path.cwd())
if not result["ok"]:
    raise SystemExit("release surface failed: " + repr(result["violations"]))
PY

# Browser code is intentionally dependency-free. Syntax-check it when Node is
# available; the Python/package gates remain runnable on machines without Node.
if command -v node >/dev/null 2>&1; then
  node --check testamur/web/app.js
fi

# Release-critical tests are named explicitly so deleting/renaming one cannot
# silently narrow the semantic contract. After verifying their presence, run
# the complete current Testamur regression suite exactly once so newly-added
# tests automatically become release-blocking.
required_tests=(
  tests/test_testamur_release_e2e_gate_c.py
  tests/test_testamur_release_e2e_source_history_compare.py
  tests/test_testamur_release_e2e_temporal.py
  tests/test_testamur_release_e2e_temporal_nonleakage.py
  tests/test_testamur_release_e2e_policy.py
  tests/test_testamur_release_e2e_policy_context.py
  tests/test_testamur_release_e2e_reliance.py
  tests/test_testamur_release_e2e_reliance_staleness.py
  tests/test_testamur_release_e2e_work_session.py
  tests/test_testamur_release_e2e_worksession_reliance.py
  tests/test_testamur_release_e2e_affectedness.py
  tests/test_testamur_release_e2e_lineage_affectedness.py
  tests/test_testamur_authority_graph.py
  tests/test_testamur_release_gate.py
  tests/test_testamur_namespace_dependency_guard.py
  tests/test_testamur_production_namespace_gate.py
  tests/test_testamur_agent_wrapper_namespace.py
  tests/test_testamur_fresh_install.py
  tests/test_testamur_product_service.py
  tests/test_testamur_web_app.py
)

for test_file in "${required_tests[@]}"; do
  if [[ ! -f "$test_file" ]]; then
    echo "missing release-critical test: $test_file" >&2
    exit 1
  fi
done

"$PYTHON_BIN" -m pytest -q tests/test_testamur_*.py

printf '%s\n' 'Testamur full current regression suite and release-critical semantic gates passed.'
