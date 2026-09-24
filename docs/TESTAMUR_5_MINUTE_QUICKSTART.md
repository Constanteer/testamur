# Testamur: five-minute quickstart

This guide is the shortest path from “what is Testamur?” to a useful local result without teaching a second ontology.

Testamur records evidence about what was observed, what changed, what a user or tool explicitly relied on, and what should be reconsidered after change. It does **not** collapse those facts into a generic trust score.

## Minute 0 — install and orient

```bash
python -m pip install -e .
testamur --help
```

Keep these distinctions in view:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
EXPOSED_TO_MODEL != RELIED
```

A Source identifies something you can observe over time. A Revision is one recorded state of it. Verification is evidence produced by a particular check. Reliance is an explicit statement that work depended on evidence. Impact explains what may need attention after change; it is not a verdict that downstream work is wrong. Revalidation records the new check/reconsideration.

## Minute 1 — use a real project

From a repository you already care about, create/import a Project and bind the repository as scanner input:

```bash
testamur project import . --name demo-project
testamur project bind-repo demo-project .
testamur-project-repo show demo-project
```

A Project is a product container. Binding a repository records where scanner input comes from; it does not mean every file is relied upon. `testamur-project-repo show` reports the binding lifecycle state; disabling a binding only removes scanner eligibility and does not erase its recorded identity/history.

## Minute 2 — record the first baseline

```bash
testamur project scan demo-project
testamur project supply-chain demo-project
```

Treat this first successful scan as the **baseline observation**. It records manifest evidence such as lockfiles and declared dependency revisions. Recording a package/version does not verify the package and does not assert that it is safe.

In the Web product, the equivalent first-run path is **Create project → Add first monitor → Record first baseline**. The baseline is useful because later observations have something explicit to compare against; it is not a green verdict or a trust score.

Run the scan again without changing manifests: Testamur appends a new immutable **scan observation event** because a new observation happened, while unchanged manifest/dependency state records remain content-deduplicated. A second observation is not evidence that the dependency state changed; Compare decides whether a mechanical difference exists.

## Minute 3 — compare a later observation

After changing a dependency or manifest, scan again and compare the immutable scan revisions:

```bash
testamur project scan demo-project
testamur project supply-chain-history demo-project
testamur project supply-chain-diff demo-project
```

The diff can say “dependency added”, “dependency removed”, “version changed”, or “manifest bytes changed”. It must not silently turn “changed” into “invalid”, “vulnerable”, or “broken”.

## Minute 4 — follow Source → Revision → Compare → Impact → Revalidation

When a change matters, ask the next explicit question rather than reading a status color as a verdict:

1. **Source** — what object or upstream input are we talking about?
2. **Revision** — which recorded state changed?
3. **Compare** — what changed mechanically between revisions?
4. **Impact** — which recorded reliance or downstream work is potentially affected, and why?
5. **Revalidation** — what check or reconsideration would justify continuing to rely on it?

For supply-chain advisories, an exact package/revision overlap is a **review candidate**, not an affectedness verdict. Review the candidate against the project evidence, then record the assessment evidence and reload the canonical projection. `recorded != verified`, and `changed != invalid` still apply.

This sequence is the Web product’s intended mental model too. “Impact” means attention is justified by recorded evidence; it does not mean the downstream result is false.

## Minute 5 — connect Codex/MCP without granting hidden reliance

Testamur’s MCP/agent surface exposes the same project evidence model. For an existing project, the useful read path includes:

```text
testamur.project_repository_binding
testamur.set_project_repository_binding_enabled
testamur.project_repository_unbind
testamur.project_supply_chain
testamur.project_scan
testamur.project_supply_chain_diff
testamur.project_advisory_revalidation
testamur.record_project_advisory_assessment
```

Before scanning, `testamur.project_repository_binding` exposes the durable binding and its scanner-eligibility state; enable/disable or unbind changes scanner eligibility without rewriting binding history. For an advisory candidate, use `testamur.project_advisory_revalidation` to read the canonical review projection. After doing the actual review, `testamur.record_project_advisory_assessment` records evidence, basis, analyzer provenance, and optional supersession. The caller must not manufacture a canonical `verdict`, `state`, or `trust_score`; reload the project projection after the write to see the canonical result.

Exposure is not durable reliance. `EXPOSED_TO_MODEL != RELIED` remains a core semantic boundary; durable reliance requires an explicit reconciliation record in canonical Testamur state.

## What to open next

- `README.md` — product and CLI orientation.
- `docs/TESTAMUR_LAUNCH_WALKTHROUGH.md` — launch/demo walkthrough and narration.
- `docs/TESTAMUR_PRODUCT_API.md` — canonical product/service boundary and stable envelopes.
- `docs/TESTAMUR_SOURCE_GATEWAY_IMPLEMENTATION.md` — exact-revision retrieval and local gateway behavior.
- `docs/TESTAMUR_LINEAGE_AFFECTEDNESS_SPEC.md` — why lineage/overlap is evidence for impact analysis rather than an automatic verdict.

If the UI or an integration appears to contradict the distinctions at the top of this guide, treat that as a product bug rather than inventing a new status interpretation.
