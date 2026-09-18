# Quick launch

This repository is a **Testamur / MathHub transition workspace**. Do not use the retired Witness release path or treat GitHub Actions as required release infrastructure.

For product ownership and boundaries, start with [`README.md`](README.md) and [`docs/TESTAMUR_COMPLETION_SPEC.md`](docs/TESTAMUR_COMPLETION_SPEC.md).

## 1. Validate the exact checkout

After updating the branch you intend to run:

```bash
git pull --ff-only
bash scripts/testamur_local_gate.sh smoke
```

Before treating a Testamur checkout as a release candidate, run the repository-local release gate on that **exact head**:

```bash
bash scripts/testamur_local_gate.sh release
```

GitHub Actions may also execute checks when configured, but Actions being deleted, unavailable, queued, or runner-starved is not itself a release blocker. An unexecuted check is never evidence of success; use the local gate instead.

## 2. Run Testamur locally

Install the current package in the environment you want to test, then use the canonical entrypoints:

```bash
testamur --help
testamur status
testamur-web
```

The Web surface is a projection over the same Testamur product semantics as the CLI/local core; it is not a second evidence engine.

Do not expose a local Testamur or MathHub process directly to the public Internet merely because it starts successfully. Authentication, hosted authorization, billing, retention administration, production database orchestration, and deployment secrets belong to the separate hosted service-plane boundary described in the completion specification.

## 3. MathHub

MathHub remains a distinct mathematical knowledge/proof-graph project in this transition repository. Its canonical product description is [`docs/MATHHUB_PRODUCT.md`](docs/MATHHUB_PRODUCT.md).

The canonical MathHub entrypoint must remain independent of the retired Witness runtime. Testamur and MathHub may share provenance infrastructure, but neither should require a hidden Witness package to start.

## 4. Public preview / hosted deployment

There is intentionally no canonical production-hosting recipe in this transition document. A disposable local preview is not equivalent to a supported hosted deployment, and old machine-specific runner/tunnel instructions are not release requirements.

When the repository split is performed, deployment instructions should live with the private hosted/service-plane repository and describe the actual authenticated edge, worker, database, retention, and secret-management topology used there.

## Release rule

A Testamur release candidate is supported by an executed local release gate for its exact commit plus the structural namespace/repository audit. Do not substitute stale green results from an older SHA, and do not block unrelated cleanup solely because GitHub Actions is unavailable.
