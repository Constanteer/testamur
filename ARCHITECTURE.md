# Testamur Architecture

Testamur is a local-first provenance and revalidation system. Its job is not to produce a universal trust score; it preserves enough structure to answer narrower, inspectable questions:

- Which exact source revision was used?
- What did a work session observe?
- What did the resulting work actually rely on?
- What changed later?
- Which downstream artifacts may need review?
- What evidence supports that conclusion?

## 1. Canonical objects

### Source, Snapshot and SourceRevision

A **Source** identifies something that can be observed over time: a document, repository branch, file, API resource or other external input.

A **Snapshot** stores an observation of a Source. A **SourceRevision** gives that observation durable revision identity so downstream records can point to an exact version instead of a moving locator.

This is the foundation for reproducibility and later change comparison.

### WorkSession

A **WorkSession** records observable workflow activity. Agent integrations may record session and tool events, but Testamur does not claim access to hidden model reasoning.

Exposure remains distinct from reliance:

```text
observed / fetched / exposed
            !=
       durable reliance
```

### Policy, Assessment and Reliance

Policies express purpose-scoped requirements. Assessments evaluate available evidence against those requirements.

A **Reliance** record is created only through the explicit reconciliation path. It states that downstream work actually depends on a particular upstream revision for a particular purpose.

This is why merely fetching a page never silently becomes durable reliance.

### Watch, Evaluation and Alert

A **Watch** monitors a Source for change. Evaluations compare the latest observation with the previously known revision and Alerts surface relevant changes.

A detected change is evidence, not an automatic invalidation:

```text
changed != invalid
stale != false
```

### Lineage and affectedness

Lineage records structural downstream relationships. Affectedness adds the evidence and reasoning needed to decide whether a change may matter to a dependent artifact.

The distinction is deliberate:

```text
lineage != affectedness verdict
```

## 2. Product flow

The canonical flow is:

```text
Source
  -> Snapshot / SourceRevision
  -> WorkSession
  -> explicit reconciliation
  -> Policy / Assessment
  -> Reliance
  -> Watch / Evaluation / Alert
  -> lineage / affectedness
  -> revalidation
```

Every user-facing surface should project this same model rather than inventing a second semantic layer.

## 3. Interfaces

### CLI

`testamur` is the primary local command-line entrypoint.

### Local Web

`testamur-web` exposes a local workspace over the same canonical stores and product-service boundary. The Web UI is a projection, not a second evidence engine.

### Source Gateway

`testamur-gateway` and `testamur-gateway-mcp` expose exact-revision source access. Gateway access records what was fetched; durable reliance still requires explicit reconciliation.

### Integrations

Host-specific hooks, MCP wrappers and monitor providers live in `Constanteer/testamur-plugins`. Integrations remain thin adapters and do not own Testamur's semantic model.

## 4. Storage and identity

Testamur keeps durable object identity separate from presentation. Historical storage or wire identifiers may remain readable for compatibility, but new production code is owned by the `testamur` namespace.

Local state is controlled through `TESTAMUR_HOME` and `TESTAMUR_DB`. Raw retained source bytes, metadata and derived records are managed by Testamur-owned stores.

## 5. Temporal semantics

Testamur distinguishes multiple notions of time, including when information was recorded, when it was available and when it was effective. These are not collapsed into one generic timestamp.

See [the temporal model](docs/TESTAMUR_TEMPORAL_MODEL.md) for the detailed contract.

## 6. Release boundary

This repository ships the canonical `testamur*` Python package and Testamur-owned local entrypoints. Hosted authentication, billing, tenant isolation, managed scheduling and production deployment infrastructure are separate service-plane concerns.

The release gate enforces the package boundary and rejects reverse dependencies on retired runtime namespaces.

For executable checks, see [Quick launch](QUICK_LAUNCH.md).
