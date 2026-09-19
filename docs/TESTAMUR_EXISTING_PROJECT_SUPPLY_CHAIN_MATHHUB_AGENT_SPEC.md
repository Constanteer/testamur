# Existing-project supply chain and MathHub agent integration

Status: canonical implementation spec

## Scope

This spec defines two product surfaces that must share Testamur's existing semantics rather than create a second ontology:

1. durable supply-chain lifecycle for an already-existing Testamur Project;
2. CLI/client/MCP/plugin access to MathHub for human and AI clients.

It does not make Testamur a package vulnerability verdict engine and it does not make MathHub an AI verifier.

Canonical boundaries remain:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
EXPOSED_TO_MODEL != RELIED
lineage != affectedness verdict
```

No generic trust score is introduced.

## Existing-project repository binding

A Project MAY bind one or more repository roots. A binding is an explicit durable product object, not a guess from Project name.

Minimum binding fields:

- stable binding id;
- project id;
- repository kind: local_path or git;
- canonical locator;
- optional branch/ref;
- creation time and actor;
- enabled/disabled state.

A local path is execution configuration, not globally portable identity. A git binding SHOULD retain remote locator plus requested ref when available.

CLI target surface:

```text
testamur product project repo bind PROJECT PATH
testamur product project repo list PROJECT
testamur product project repo unbind PROJECT BINDING
testamur product project scan PROJECT [--binding BINDING]
testamur product project supply-chain PROJECT
testamur product project supply-chain-diff PROJECT [--from REV] [--to REV]
```

`project import PATH --name NAME` remains a convenient bootstrap command, but repeated operation on an existing Project must converge on the same durable Project and scan history.

## Supply-chain scan lifecycle

Each scan creates or reuses immutable evidence:

```text
Project
  -> RepositoryBinding
  -> SupplyChainScan revision
       -> Manifest revision(s)
       -> Dependency record revision(s)
```

Unchanged scans are idempotent. Changed manifests append record revisions. Historical scan revisions remain queryable.

The current Project projection MUST select the newest applicable supply-chain scan revision and MUST NOT replace history in place.

### Diff

A scan-to-scan diff is mechanical evidence, not a risk verdict. It MUST distinguish at least:

- dependency_added;
- dependency_removed;
- dependency_version_changed;
- dependency_identity_strengthened;
- dependency_identity_weakened;
- manifest_added;
- manifest_removed;
- manifest_changed.

The diff MUST preserve old and new component revision identifiers where known.

A dependency removal from the latest scan does not erase historical reliance, lineage, or prior advisory evidence.

## Scanner ecosystem

Current parsers remain valid:

- requirements*.txt;
- uv.lock;
- poetry.lock;
- package-lock.json / npm-shrinkwrap.json;
- Cargo.lock;
- go.sum.

Next compatibility targets are pnpm lockfiles, yarn lockfiles, Maven, Gradle, CycloneDX and SPDX. Unsupported or unpinned declarations remain warnings/evidence gaps rather than invented exact revisions.

## Advisory ingestion and applicability

Provider documents are immutable adverse-event inputs. Initial providers include OSV and CISA KEV.

Provider package/version overlap is candidate evidence. It is not automatically a local affectedness verdict.

Pipeline:

```text
provider revision
  -> normalized adverse-event revision
  -> exact/unresolved identity matching
  -> lineage/applicability evidence
  -> affectedness assessment
  -> Project review surface
  -> targeted revalidation
```

The system MUST preserve UNKNOWN / POTENTIALLY_AFFECTED / CONFIRMED_AFFECTED / DISPROVEN distinctions according to the affectedness engine rather than caller-supplied verdicts.

## Project refresh

`project refresh` currently refreshes monitors. The target product behavior is explicit, not ambiguous:

- `project refresh` refreshes configured monitors;
- `project scan` rescans bound repository supply chains;
- a future `project update` MAY orchestrate both, but must report each operation separately.

Background scheduling MAY invoke repository scans only for bindings that can be safely and deterministically accessed by the running host.

## Agent/MCP supply-chain tools

Host-neutral agent tools SHOULD project the same ProductService/CLI operations:

```text
testamur.project_get
testamur.project_scan
testamur.project_supply_chain
testamur.project_supply_chain_diff
testamur.project_advisories
testamur.project_revalidate
```

Agent access must not silently convert source exposure, dependency declaration, advisory overlap or change into reliance/verification/invalidity.

## MathHub boundary

MathHub remains a non-AI mathematical knowledge and proof graph. Lean/kernel checking is the verifier.

Canonical MathHub ontology remains:

```text
Claim + Proof + ProofDependency
```

AI clients are callers of the same explicit MathHub client surface used by the CLI.

## MathHub client and CLI

Introduce a reusable MathHub client over the existing HTTP API. CLI and MCP/plugin adapters MUST use this client instead of duplicating endpoint semantics.

Target CLI:

```text
mathhub search QUERY
mathhub claim CLAIM
mathhub argument CLAIM
mathhub path CLAIM --target TARGET
mathhub graph [CLAIM]
mathhub import DECLARATION
mathhub import-closure DECLARATION
mathhub claim create ...
mathhub proof add CLAIM ...
mathhub proof build PROOF
```

Read calls must remain bounded. Write calls must surface MathHub/Lean failures without converting them into AI-authored truth.

## MathHub MCP/plugin surface

Host-neutral MCP tools SHOULD include:

```text
mathhub.search_claims
mathhub.get_claim
mathhub.get_argument
mathhub.find_path
mathhub.get_graph
mathhub.import_declaration
mathhub.import_closure
mathhub.register_claim
mathhub.register_proof
mathhub.build_proof
```

The native Codex plugin may bundle these tools alongside Testamur provenance tools. Claude Code, OpenCode and other MCP hosts must be able to use the same server without requiring a host-specific ontology.

For every MathHub write response, verification/build provenance comes from MathHub/Lean. The agent is never represented as the verifier merely because it requested the operation.

## Repository boundaries

- `Constanteer/testamur`: canonical Testamur core/product semantics.
- `Constanteer/testamur-plugins`: thin host adapters and MCP/plugin packaging.
- `Constanteer/Mathub`: MathHub runtime, client, CLI, API and Web product.
- `Constanteer/testamur-host`: hosted account/tenancy/deployment bundle.

Legacy Testamur copies in MathHub should be removed once no current deployment/package path depends on them. Cleanup must follow dependency verification rather than deleting by filename pattern.

## Acceptance sequence

A release-quality existing-project flow is:

```text
bind existing repo
 -> scan
 -> inspect immutable inventory
 -> change lockfile
 -> rescan same Project
 -> view added/removed/upgraded diff
 -> ingest/update advisory evidence
 -> review affectedness candidates
 -> record assessment
 -> revalidate targeted downstream work
```

A release-quality MathHub agent flow is:

```text
AI host
 -> MathHub MCP/client
 -> search/read Claim
 -> inspect exact Proof/argument dependencies
 -> optionally import/register/build
 -> Lean verifies
 -> MathHub returns Build/provenance
```

Tests must cover idempotent rescans, changed rescans, removals, version changes, historical scan preservation, explicit Project binding, CLI/client parity, bounded MCP reads and Lean failure propagation.
