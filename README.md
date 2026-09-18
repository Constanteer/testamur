# Testamur

Testamur is a local-first provenance and revalidation layer for inspectable technical work.

It records the exact source revisions a workflow saw or depended on, captures observable work-session events, preserves explicit reliance decisions, and helps identify what may need review when upstream sources change.

Testamur deliberately keeps these distinctions intact:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
lineage != affectedness verdict
```

## What it provides

- **Source provenance** — Sources, Snapshots and exact SourceRevisions.
- **Work sessions** — observable session/tool activity without claiming access to hidden model reasoning.
- **Explicit reliance** — reconciliation, Policy, Assessment and durable Reliance records.
- **Change monitoring** — Watches, Evaluations and Alerts for upstream sources.
- **Impact analysis** — lineage and affectedness evidence for targeted revalidation.
- **Source Gateway** — exact-revision source access, including a local stdio MCP server.
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

A source being fetched or shown to an agent is evidence of exposure, not automatically evidence of reliance. Likewise, an upstream change creates a reason to inspect downstream work; it does not automatically make that work invalid.

## Software supply-chain import

Scan a repository's dependency manifests and lockfiles into Testamur:

```bash
testamur project import .
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

Agent/editor integrations live in the separate `Constanteer/testamur-plugins` repository.

## Local state

Testamur is local-first. State location can be controlled with:

- `TESTAMUR_HOME` — Testamur state root.
- `TESTAMUR_DB` — explicit database path override.

Hosted account, billing and multi-tenant service infrastructure is intentionally outside this repository.

## Documentation

Start with:

- [Architecture](ARCHITECTURE.md)
- [Quick launch](QUICK_LAUNCH.md)
- [Product API](docs/TESTAMUR_PRODUCT_API.md)
- [Agent workflow](docs/TESTAMUR_AGENT_WORKFLOW.md)
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

The first public release line is **v1.0.0**.

## License

Testamur is licensed under the [Apache License 2.0](LICENSE).

## Status

Testamur is under active development. Public interfaces may still evolve, but the semantic boundary is intentional: provenance, verification, exposure, reliance, change and affectedness remain separate concepts.
