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
testamur product project import . --name demo-project
testamur product project bind-repo demo-project .
testamur product project repo demo-project
```

A Project is a product container. Binding a repository records where scanner input comes from; it does not mean every file is relied upon.

## Minute 2 — record the supply chain

```bash
testamur product project scan demo-project
testamur product project supply-chain demo-project
```

The scan records manifest evidence such as lockfiles and declared dependency revisions. Recording a package/version does not verify the package and does not assert that it is safe.

Run the scan again without changing manifests: the canonical statements are intended to remain idempotent rather than manufacturing a meaningful change.

## Minute 3 — make a mechanical comparison

After changing a dependency or manifest, scan again and compare the immutable scan revisions:

```bash
testamur product project scan demo-project
testamur product project supply-chain-history demo-project
testamur product project supply-chain-diff demo-project
```

The diff can say “dependency added”, “dependency removed”, “version changed”, or “manifest bytes changed”. It must not silently turn “changed” into “invalid”, “vulnerable”, or “broken”.

## Minute 4 — follow the evidence question

When a change matters, ask the next explicit question rather than reading a status color as a verdict:

1. **Source** — what object or upstream input are we talking about?
2. **Revision** — which recorded state changed?
3. **Compare** — what changed mechanically between revisions?
4. **Impact** — which recorded reliance or downstream work is potentially affected, and why?
5. **Revalidation** — what check or reconsideration would justify continuing to rely on it?

This sequence is the Web product’s intended mental model too. “Impact” means attention is justified by recorded evidence; it does not mean the downstream result is false.

## Minute 5 — connect an agent without granting hidden reliance

Testamur’s MCP/agent surface exposes the same project evidence model. In particular, the project supply-chain tools include:

```text
testamur.project_supply_chain
testamur.project_scan
testamur.project_supply_chain_diff
testamur.project_advisories
testamur.project_revalidate
```

A model fetching or seeing evidence is exposure, not durable reliance. Host integrations must keep `EXPOSED_TO_MODEL != RELIED`; reliance requires the explicit reconciliation path defined by the Testamur agent protocol.

## What to open next

- `README.md` — product and CLI orientation.
- `docs/TESTAMUR_LAUNCH_WALKTHROUGH.md` — launch/demo walkthrough and narration.
- `docs/TESTAMUR_AGENT_PROTOCOL.md` — host/MCP semantics and explicit reconciliation.
- `docs/TESTAMUR_EXISTING_PROJECT_SUPPLY_CHAIN_MATHHUB_AGENT_SPEC.md` — repository binding, scanner, advisory, and agent contracts.
- `docs/TESTAMUR_LINEAGE_AFFECTEDNESS_SPEC.md` — why lineage/overlap is evidence for impact analysis rather than an automatic verdict.

If the UI or an integration appears to contradict the distinctions at the top of this guide, treat that as a product bug rather than inventing a new status interpretation.
