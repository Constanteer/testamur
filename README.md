# Testamur

Testamur is a local-first provenance and revalidation layer for technical work that depends on changing sources.

It records the exact revisions a workflow saw or depended on, preserves explicit reliance decisions, and helps you find what may need review when documentation, repositories, APIs, packages, papers, or other upstream sources change.

**New here? Start with the [five-minute quickstart](docs/TESTAMUR_5_MINUTE_QUICKSTART.md).** It uses an existing repository to show the Source → Revision → Compare → Impact → Revalidation mental model without requiring familiarity with Testamur's internal object names.

Testamur deliberately keeps these distinctions intact:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
EXPOSED_TO_MODEL != RELIED
lineage != affectedness verdict
```

## Start here

- **Web / hosted workspace:** https://testamur.org
- **Manifesto:** https://manifesto.testamur.org
- **Integrations:** https://testamur.org/integrations
- **Five-minute quickstart:** [docs/TESTAMUR_5_MINUTE_QUICKSTART.md](docs/TESTAMUR_5_MINUTE_QUICKSTART.md)

The hosted workspace is optional. The core runtime, CLI, Source Gateway and local Web interface can all be used locally.


## What it provides

- **Source provenance** — Sources, Snapshots and exact SourceRevisions.
- **Work sessions** — bounded, inspectable activity records that can be reconciled into explicit reliance.
- **Explicit reliance** — reconciliation, Policy, Assessment and durable Reliance records.
- **Change monitoring** — Watches, Evaluations and Alerts for upstream sources.
- **Impact analysis** — lineage and affectedness evidence for targeted revalidation.
- **Source Gateway** — exact-revision source access for local tools and integrations.
- **Local interfaces** — CLI plus a local Web workspace over the same canonical state.

## Install from source

Testamur requires Python 3.11 or newer.

```bash
git clone https://github.com/Constanteer/testamur.git
cd testamur

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Check the installation:

```bash
testamur --help
testamur status
```

Start the local Web interface:

```bash
testamur-web
```

## Core model

The normal flow is:

```text
SourceRevision
  -> WorkSession
  -> explicit reconciliation
  -> Policy / Assessment
  -> Reliance
  -> Watch / change
  -> lineage / affectedness
  -> revalidation
```

A source being fetched or exposed is not automatically evidence of reliance. Likewise, an upstream change creates a reason to inspect downstream work; it does not automatically make that work invalid.

## Software supply-chain import

For a first run against an existing repository, use the project workflow described in the five-minute quickstart:

```bash
testamur project import . --name demo-project
testamur project bind-repo demo-project .
testamur-project-repo show demo-project
testamur project scan demo-project
testamur project supply-chain demo-project
```

The initial importer recognizes pinned Python requirements, `uv.lock`, `poetry.lock`, npm `package-lock.json` / `npm-shrinkwrap.json`, `Cargo.lock`, and `go.sum`. It records exact manifest digests, canonical package/component identities, dependency observations and durable project scan relations.

A declared package version is preserved as declaration evidence; Testamur does not automatically treat a name/version match as an exact content match or vulnerability/affectedness verdict.

## Source Gateway

Testamur includes a local Source Gateway for exact-revision source access.

CLI entrypoint:

```bash
testamur-gateway
```

stdio MCP entrypoint:

```text
testamur-gateway-mcp
```

The MCP process is intended to be started by an MCP host rather than used as an interactive CLI.

Host-specific integrations and their documentation live in the separate `Constanteer/testamur-plugins` repository. The core repository keeps only host-neutral product, data-model, CLI, API, provenance, impact and revalidation documentation.

### Marketplace availability

The canonical distribution surface for Testamur integrations is currently the public source repository and its GitHub Releases.

The Codex integration is usable from `Constanteer/testamur-plugins`, but it is **not currently listed in host-operated plugin marketplaces**. The maintainer is under 18 and cannot yet complete some third-party publisher/account eligibility steps required for those listings. This affects marketplace discovery and one-click distribution only; it does not change the plugin, MCP, or local Testamur runtime.

Until those listings are available, use the documented GitHub/source installation path and pin a release tag or exact commit when reproducibility matters.

## Local state

Testamur is local-first. State location can be controlled with:

- `TESTAMUR_HOME` — Testamur state root.
- `TESTAMUR_DB` — explicit database path override.

Hosted account, billing and multi-tenant service infrastructure is intentionally outside this repository.

## Documentation

Start with:

- [Five-minute quickstart](docs/TESTAMUR_5_MINUTE_QUICKSTART.md)
- [Launch walkthrough](docs/TESTAMUR_LAUNCH_WALKTHROUGH.md)
- [Architecture](ARCHITECTURE.md)
- [Quick launch](QUICK_LAUNCH.md)
- [Product API](docs/TESTAMUR_PRODUCT_API.md)
- [Temporal model](docs/TESTAMUR_TEMPORAL_MODEL.md)
- [Lineage engine](docs/TESTAMUR_LINEAGE_ENGINE.md)
- [Environment model](docs/TESTAMUR_ENVIRONMENT.md)

## Development

Install pytest in your development environment, then run the repository gates:

```bash
python -m pip install -U pytest
bash scripts/testamur_local_gate.sh smoke
bash scripts/testamur_local_gate.sh release
```

The release gate validates the exact Testamur package surface and runs the current Testamur regression suite.

## Release

The current public release line is **v1.1.0**. The original `v1.0.0` tag remains immutable as the initial release baseline.

## Maintainer and development note

Testamur is currently maintained by a full-time student. Development happens around school, exams, and other academic commitments; during high-pressure school periods, issue and pull-request response times may be slower than for a full-time project.

AI tools have been used extensively during development for implementation, refactoring, testing, documentation, and review. Product direction, architecture, release decisions, and final responsibility remain with the maintainer. AI-generated output is not treated as verification: important behavior is expected to be backed by tests, inspectable code, reproducible builds, or the relevant external verifier.

## License

Testamur is licensed under the [Apache License 2.0](LICENSE).

## Status

Testamur is under active development. Public interfaces may still evolve, but the semantic boundary is intentional: provenance, verification, exposure, reliance, change and affectedness remain separate concepts.
