# Testamur / MathHub transition repository

This repository is currently the transition workspace for **Testamur** and the existing **MathHub** codebase.

The two products are related by provenance/verification infrastructure, but they are **not one product and not one ontology**.

## Testamur

**Testamur records what work depended on, what changed, and what must be revalidated.**

The canonical runtime/package in the current release line is `testamur*`.

Core local loop:

```text
SourceRevision
  -> WorkSession
  -> explicit reconciliation
  -> Policy
  -> Reliance
  -> Watch/change
  -> impact / affectedness
  -> revalidation
```

Important semantic boundaries:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
lineage != affectedness verdict
```

The current Web surface is a GitHub-like workspace over the same `TestamurProductService` boundary. User-facing "projects" are presentations of tracked Sources; they do not introduce a second durable Project ontology.

### Local entrypoints

```bash
testamur
testamur-web
```

### Release validation without GitHub Actions

GitHub Actions is optional execution infrastructure, not a release dependency. If Actions is missing, deleted, queued, or runner-starved, validate the exact checkout locally:

```bash
bash scripts/testamur_local_gate.sh smoke
bash scripts/testamur_local_gate.sh release
```

An unavailable/unexecuted Actions run is not green, but it is also not a blocker by itself.

### Canonical release documents

Use this authority order:

1. [`docs/TESTAMUR_COMPLETION_SPEC.md`](docs/TESTAMUR_COMPLETION_SPEC.md) — completion scope and repository/product boundaries
2. [`docs/TESTAMUR_CONVERGENCE.md`](docs/TESTAMUR_CONVERGENCE.md) — semantic ownership and invariants
3. [`docs/TESTAMUR_RELEASE_READINESS.md`](docs/TESTAMUR_RELEASE_READINESS.md) — executable release checklist
4. [`docs/TESTAMUR_IMPLEMENTATION_GAPS.md`](docs/TESTAMUR_IMPLEMENTATION_GAPS.md) — operational landed/open/stacked tracker

Supporting contracts include [`docs/TESTAMUR_PRODUCT_API.md`](docs/TESTAMUR_PRODUCT_API.md), [`docs/TESTAMUR_AGENT_WORKFLOW.md`](docs/TESTAMUR_AGENT_WORKFLOW.md), and [`docs/TESTAMUR_LINEAGE_ENGINE.md`](docs/TESTAMUR_LINEAGE_ENGINE.md).

Historical worker prompts and retired Witness execution plans are intentionally not part of the active authority chain; Git history is their archive.

## MathHub

MathHub remains the Lean-backed mathematical knowledge/proof graph project. Its product overview has been preserved separately while the repository boundaries are cleaned up:

- [`docs/MATHHUB_PRODUCT.md`](docs/MATHHUB_PRODUCT.md)

MathHub's Claim / Proof / ProofDependency model must not be mistaken for Testamur's generic evidence/reliance model, and Testamur must not depend on a hidden MathHub/Witness runtime to function.

## Repository-boundary status

The current transition branch establishes these boundaries:

```text
testamur/       canonical Testamur local/core package
integrations/   future public adapters/plugins boundary
apps/           future hosted/product deployment boundary marker
archive/        explicitly retired historical runtime material
```

The intended final split is:

```text
public Testamur core / CLI
public integrations / tool adapters
private hosted / account / billing / service plane
MathHub retained as its own project
```

The current package metadata remains `Proprietary` during this private transition. Selecting an open-source license is an explicit repository-owner decision to make when the public split is created, not something inferred by cleanup automation.

## Landed 0.1 baseline

Testamur 0.1 local/core convergence is landed on `main` via PR #171, including the repository-boundary work from PR #172.

Post-merge release evidence:
- `main` merge commit: `434447294478783a1fa55238d9eae3c6f1126bb3`
- `testamur-release-gate` #2127: success on that merge commit

Older worker branches are implementation history, not current semantic owners. New work should branch from `main` and clean-forward only the distinct post-0.1 deltas it still needs.
