# Contributing to Testamur

Testamur is a provenance and revalidation system. Contributions are welcome, but
the semantic boundaries are part of the API—not just documentation wording.

## Development setup

Testamur requires Python 3.11 or newer. A typical editable development setup is:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip install pytest
python -m pytest -q
```

For Web changes, also run a JavaScript syntax check when Node.js is available:

```bash
node --check testamur/web/app.js
```

GitHub Actions may provide the same checks, but local verification is still
useful when hosted runners are unavailable.

## Semantic firewall

Do not introduce shortcuts that collapse distinct Testamur concepts:

- `recorded != verified`
- `fetched != relied`
- `changed != invalid`
- `stale != false`
- `EXPOSED_TO_MODEL != RELIED`
- lineage is not an affectedness verdict.

In particular:

- do not add a generic trust score;
- do not infer durable reliance from source visibility or model exposure;
- do not turn package/advisory name or version matches into affectedness;
- do not treat a changed upstream revision as proof that downstream work failed.

When adding a derived projection, make the evidence basis and the non-implications
inspectable.

## Architecture boundaries

The `testamur` package is the canonical owner of core identities, storage and
product semantics. Integrations should consume canonical APIs rather than
reimplement them.

The hosted repository carries a synchronized bundle of shared Testamur Web/core
files. Canonical changes belong here first; hosted-specific authentication,
multi-tenant state, billing and deployment concerns remain downstream.

The static marketing site is a separate product/documentation surface and must
not become a second runtime implementation.

## Pull requests

Keep changes scoped and testable. For behavior changes:

1. add or update tests that express the intended contract;
2. update user-facing docs or onboarding when the workflow changes;
3. state semantic non-implications where a result could otherwise be
   misinterpreted;
4. avoid unrelated formatting churn.

For UI work, prefer a complete user workflow over exposing another raw internal
object. Source → Revision → Compare → Impact → Revalidation should remain
understandable without inventing a second ontology.
