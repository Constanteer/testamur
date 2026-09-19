# Testamur launch walkthrough

This is the canonical launch/demo script for showing Testamur without collapsing its evidence semantics into a generic trust score.

## 90-second product walkthrough

### 0:00–0:12 — The problem

**Screen:** Testamur dashboard, then a project.

**Narration:**

> Software, research, and agent work increasingly depend on material no one person can continuously reread. Testamur records what a project used, observes those sources over time, and makes downstream review explicit when something changes.

Do **not** say “Testamur verifies everything” or “Testamur tells you what is trustworthy.”

### 0:12–0:28 — Project and source

**Screen:** Open the example project and its first monitor. Open the Source object.

**Narration:**

> A Project groups work. A Monitor observes a target. The target is represented as a stable Source, while each observation produces revision evidence. Recording a source is not the same as verifying its claims.

On-screen semantic boundary:

`recorded != verified`

### 0:28–0:43 — Revision and change

**Screen:** History → two revisions → Compare.

**Narration:**

> When the observed material changes, Testamur keeps both revisions and a comparison. “Changed” is deliberately descriptive: it does not mean the previous work is invalid.

On-screen semantic boundary:

`changed != invalid`

### 0:43–0:58 — Reliance and impact

**Screen:** Impact view with one recorded downstream reliance.

**Narration:**

> Impact starts from recorded reliance, not from everything the system happened to fetch or expose to a model. That distinction prevents a large context window from becoming a fabricated dependency graph.

On-screen boundaries:

`fetched != relied`

`EXPOSED_TO_MODEL != RELIED`

### 0:58–1:12 — Revalidation

**Screen:** Revalidation queue / review action.

**Narration:**

> A relevant change can create a review obligation. Revalidation records the human or machine review that follows. A stale result means its freshness requirement was missed; it does not mean the underlying claim became false.

On-screen boundary:

`stale != false`

### 1:12–1:24 — Supply chain

**Screen:** Project → Supply chain; show manifests, exact material, advisory candidate.

**Narration:**

> For software projects, Testamur can record manifest and lockfile evidence. A declaration is not proof of runtime use, and an advisory identity match is not an affectedness verdict. Applicability remains an explicit assessment.

On-screen boundaries:

`manifest declaration != runtime use`

`advisory identity match != affectedness verdict`

### 1:24–1:30 — Agents

**Screen:** Help → Integrations → MCP/Codex installation.

**Narration:**

> Humans and agents can use the same provenance model through the CLI and MCP integration. The point is not blind trust in machine output; it is preserving the right to ask why.

End card: **Testamur — provenance, change, reliance, review.**

## Five-minute live demo

Use the bundled/example project rather than creating synthetic ontology for the demo.

1. **Open the example project.** Explain Project vs Monitor vs Source in one sentence each.
2. **Open a Source.** Show its stable identity and recorded history. State `recorded != verified`.
3. **Open two revisions and Compare.** Point to the concrete changed material. State `changed != invalid`.
4. **Open Impact.** Show only explicit reliance edges. State `fetched != relied` and `EXPOSED_TO_MODEL != RELIED`.
5. **Open Revalidation.** Show the review obligation/result rather than calling the dependency “bad.” State `stale != false`.
6. **Return to the Project → Supply chain.** Show manifest hashes, dependency identity strength, and an advisory candidate if the fixture contains one. Explain that exact identity overlap still requires affectedness assessment.
7. **Open Help → Integrations.** Show the CLI/MCP/Codex entry points and finish with the quickstart link.

## Recording checklist

Before recording a launch video:

- use a clean first-run account or local workspace;
- keep browser zoom at a readable level and hide unrelated tabs/account data;
- verify `/quickstart`, `/demo`, `/learn`, `/docs`, and `/integrations` are reachable in the deployed environment;
- ensure the example project has enough recorded history to demonstrate Compare and Impact without inventing relations;
- do not call an HTTP-reachable page “verified”;
- do not describe an advisory candidate as a confirmed vulnerability unless an explicit affectedness assessment supports that statement;
- do not imply a fetched or model-exposed source was relied upon unless a reliance edge was actually recorded;
- if CI/deployment infrastructure did not execute, describe it as unexecuted rather than green.

## Short launch clips

### 20 seconds — change workflow

Project → Source → Revision → Compare → Impact → Revalidation.

Narration: “Testamur records what changed, then follows explicit reliance to show what deserves review. Change is evidence, not a verdict.”

### 20 seconds — agent provenance

Integrations → MCP setup → recorded source/reliance view.

Narration: “Agent context is not automatically evidence of reliance. Testamur keeps exposure, retrieval, and reliance distinct so an agent can leave a reviewable trail instead of a generic trust score.”

### 20 seconds — software supply chain

Supply chain → manifest → dependency → advisory candidate.

Narration: “Record the exact dependency evidence you have. Match advisories against exact identities where possible, then assess applicability explicitly. Declaration is not runtime use; identity match is not affectedness.”

## Acceptance criteria for launch UX

A first-time user should be able to answer, without reading internal architecture documentation:

- What is Testamur for?
- What should I do first?
- What is the difference between a Project, Monitor, Source, and Revision?
- Where do I compare two observations?
- Why did a change create an Impact/Revalidation item?
- What does Testamur *not* claim from a recorded/fetched/stale item?
- How do I connect the CLI, MCP, or Codex?

If any answer requires knowledge of an internal identifier or ontology term that is not explained in context, treat that as a product UX defect rather than a documentation-only problem.
