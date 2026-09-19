# Testamur launch walkthrough

This is the canonical launch/demo script for showing Testamur without collapsing its evidence semantics into a generic trust score.

## 90-second product walkthrough

### 0:00–0:12 — The problem

**Screen:** Testamur dashboard, then a project.

**Narration:** Software, research, and agent work increasingly depend on material no one person can continuously reread. Testamur records what a project used, observes those sources over time, and makes downstream review explicit when something changes.

Do **not** say “Testamur verifies everything” or “Testamur tells you what is trustworthy.”

### 0:12–0:28 — Project and source

Open the example project and its first monitor, then the Source object. A Project groups work; a Monitor observes a target; the target is represented as a stable Source while observations produce revision evidence. `recorded != verified`.

### 0:28–0:43 — Revision and change

History → two revisions → Compare. A comparison records the mechanical delta. `changed != invalid`.

### 0:43–0:58 — Reliance and impact

Open Impact with one recorded downstream reliance. Impact starts from recorded reliance, not everything fetched or exposed to a model. `fetched != relied`; `EXPOSED_TO_MODEL != RELIED`.

### 0:58–1:12 — Revalidation

Open Revalidation. A relevant change can create a review obligation; revalidation records the review that follows. `stale != false`.

### 1:12–1:24 — Supply chain

Project → Supply chain. Show manifests, exact material and an advisory candidate. A declaration is not proof of runtime use, and an advisory identity match is not an affectedness verdict.

### 1:24–1:30 — Agents

Help → Integrations → MCP/Codex installation. Humans and agents use the same provenance model through Web, CLI and MCP; no integration upgrades recorded/fetched material into verification.

End card: **Testamur — provenance, change, reliance, review.**

## Five-minute live demo

Use the bundled/example project rather than creating synthetic ontology for the demo.

1. Open the example project; explain Project vs Monitor vs Source.
2. Open a Source and its history; state `recorded != verified`.
3. Open two revisions and Compare; point to concrete changed material; state `changed != invalid`.
4. Open Impact; show only explicit reliance edges; state `fetched != relied` and `EXPOSED_TO_MODEL != RELIED`.
5. Open Revalidation; show the review obligation/result rather than calling the dependency “bad”; state `stale != false`.
6. Project → Supply chain; show manifest hashes, dependency identity strength, and an advisory candidate if present. Exact identity overlap still requires affectedness assessment.
7. Help → Integrations; show CLI/MCP/Codex entry points and finish with Quickstart.

## Demo → real-project handoff

The demo is successful only if a first-time user can repeat the same workflow on their own target. From the demo, return to Projects and choose **New Project**. Create the container with the intended Private/Public visibility, then add a Monitor for the real target. For an existing repository, use the supported repository binding/supply-chain scan instead of manually recreating dependency facts.

After the first observation, the user's normal loop is exactly the one learned in the demo:

`Source → Revision → Compare → Impact → Revalidation`

Handoff checklist:

- create the Project with the intended visibility;
- add a Monitor for the actual target;
- run/import the existing-project supply-chain scan when applicable;
- record the first Revision, then make or observe one controlled change;
- Compare the two revisions before making an affectedness claim;
- inspect Impact from recorded lineage;
- revalidate the relevant downstream item and retain that result as evidence.

If a deployed surface cannot perform one of these steps, say that it is unavailable; never substitute a claim that a gate or verification ran.

## Recording checklist

- use a clean first-run account or local workspace;
- keep browser zoom readable and hide unrelated account data;
- verify `/quickstart`, `/demo`, `/learn`, `/docs`, and `/integrations` are reachable in the deployed environment;
- ensure the example project has enough recorded history for Compare and Impact without inventing relations;
- do not call an HTTP-reachable page “verified”;
- do not describe an advisory candidate as a confirmed vulnerability without explicit affectedness assessment;
- do not imply a fetched/model-exposed source was relied upon unless a reliance edge was recorded;
- if CI/deployment infrastructure did not execute, describe it as unexecuted rather than green.

## Short launch clips

**Change workflow:** Project → Source → Revision → Compare → Impact → Revalidation. “Testamur records what changed, then follows explicit reliance to show what deserves review. Change is evidence, not a verdict.”

**Agent provenance:** Integrations → MCP setup → recorded source/reliance view. “Agent context is not automatically evidence of reliance. Testamur keeps exposure, retrieval, and reliance distinct.”

**Software supply chain:** Supply chain → manifest → dependency → advisory candidate. “Record the exact dependency evidence you have, then assess applicability explicitly. Declaration is not runtime use; identity match is not affectedness.”

## Acceptance criteria for launch UX

A first-time user should be able to answer without internal architecture documentation: What is Testamur for? What should I do first? What differs between Project, Monitor, Source and Revision? Where do I compare observations? Why did a change create an Impact/Revalidation item? What does Testamur *not* claim from a recorded/fetched/stale item? How do I connect CLI, MCP or Codex? How do I move from Demo to my own project?

If an answer requires an unexplained internal identifier or ontology term, treat that as a product UX defect rather than a documentation-only problem.