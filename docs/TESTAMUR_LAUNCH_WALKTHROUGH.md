# Testamur launch walkthrough

Status: canonical narration, shot, caption, and browser-walkthrough source of truth.

This walkthrough is deliberately product-first. It demonstrates the same first-use loop as `TESTAMUR_ONBOARDING.md` and must not introduce a second ontology or a generic trust score.

## 90-second launch cut

| Time | Product surface | Shot / action | Narration | On-screen semantic guardrail |
| --- | --- | --- | --- | --- |
| 0:00–0:08 | Dashboard | Open a new workspace. Show the three-step first-run checklist. | “Testamur records the exact basis behind work, then tells you when that basis changes and what may need review.” | `recorded ≠ verified` |
| 0:08–0:20 | New Project | Create `Release evidence`. | “A Project is the place where you organize what you are watching and the work that depends on it.” | Do not ask for a Source during Project creation. |
| 0:20–0:32 | Add Monitor | Add a repository, package, document, API, or other supported target. For a repository, keep its repository binding visible. | “A Monitor watches a specific source. Repository scans stay attached to the repository binding that produced them. Fetching records an observation; fetching alone does not mean you relied on it.” | `fetched ≠ relied` |
| 0:32–0:42 | First observation | Record the first revision and open its detail. | “This is the recorded version and its evidence. Recording is not a claim that the source is true or verified.” | `recorded ≠ verified` |
| 0:42–0:52 | Demo Project | Switch to the deterministic read-only example and reveal a newer revision. | “Later, the source changes. Change is an event, not a verdict.” | `changed ≠ invalid` |
| 0:52–1:02 | Compare | Open old ↔ new mechanical comparison inside one source or repository binding. | “Compare shows what mechanically changed between two observations of the same tracked basis.” | Do not compare unrelated repository bindings or infer validity from the diff. |
| 1:02–1:13 | Impact | Open one downstream review candidate, inspect its recorded basis/revision, then return to the selected change. | “Impact follows recorded reliance. The basis explains why this work was connected; the selected change is a separate question you still review.” | `EXPOSED_TO_MODEL ≠ RELIED`; provenance ≠ affectedness verdict. |
| 1:13–1:22 | Revalidation | Open one affected item, inspect evidence, then record an explicit revalidation. If the Project has multiple repository bindings, show the Project-wide advisory review as a review queue, not a verdict. | “Project review can gather candidates across repositories, but each candidate keeps its repository and evidence context. You still decide what is actually affected.” | `stale ≠ false`; candidate ≠ affectedness verdict. |
| 1:22–1:30 | Help / integrations | Open Help, then show Quickstart, Learn, Docs, Codex/MCP/plugin install entry points. | “Start with the five-minute quickstart, explore the example, or connect Testamur to the tools where work already happens.” | Canonical semantics remain inspectable from Docs. |

## Five-minute live walkthrough

### 0. Orient — Dashboard

Start on the hosted Dashboard with an empty account. Keep the first-run checklist visible.

Say: “The loop is simple: create a place for the work, monitor something it depends on, record what you saw, and come back when that basis changes.”

Do not begin with canonical identifiers, lineage internals, or verification language.

### 1. Create a Project

Create `Release evidence`. A Project is a product container; it is not itself the monitored Source. If the UI offers an optional first Monitor, explain that the target belongs to the Monitor.

Success condition: the user can tell where another Monitor would be added without learning the canonical object graph.

### 2. Add a Monitor and record an observation

Add a supported target and record the first observation. Open the resulting Revision.

For repository targets, point out the repository binding once in plain language: it is the stable association that keeps scans and comparisons from different repositories from being mixed together. Do not make the binding identifier part of the first-run vocabulary unless troubleshooting requires it.

Point out separately:

- what was fetched;
- what exact revision was recorded;
- what evidence/metadata was retained;
- which repository binding produced a repository scan, when applicable;
- whether any work has actually recorded reliance on it.

Never collapse these into “trusted”, “verified”, or a numeric confidence score.

A second repository scan is a new immutable observation. Do not narrate a new scan as proof that dependency state changed; Compare establishes the mechanical delta between observations of the same binding.

### 3. Jump to the deterministic example

Use the read-only demo so the audience does not need to wait for a real upstream change. The demo must not mutate the user workspace.

Show revision A, then revision B. State: “Testamur knows that B differs from A. It does not know merely from that fact that A became invalid.”

### 4. Compare

Open Compare from the Revision/history context. Show the mechanical delta before any Impact claim.

For supply-chain scans, compare observations only inside the same repository binding. If the Project contains two repositories, show them as two independent histories rather than manufacturing one cross-repository diff.

Narration contract: “Compare is evidence about difference. It is not a validity judgment.”

### 5. Impact

Open Impact and choose one downstream review candidate. Before discussing the selected change, inspect the candidate's recorded reliance basis/revision and, when the provider recorded it, the relation and recorded-at provenance. Then return to the selected change and decide whether that change warrants scoped revalidation.

The shot should make the review sequence visible rather than merely narrating it:

1. identify the downstream work;
2. inspect the recorded basis/revision that explains why the reliance edge exists;
3. distinguish that provenance from the currently selected change;
4. only then decide whether to continue into Revalidation.

If a provider does not supply basis/revision provenance, show that provenance as unavailable. Do not invent a basis, infer a timestamp, or convert missing provenance into an affected/not-affected judgment for a cleaner demo.

Distinguish explicit reliance from material that was only fetched or exposed to a model. A recorded basis explains the historical reliance edge; it does not by itself establish that the current selected change affects the downstream work.

Narration contract: “Impact follows recorded reliance. This basis explains why the work is connected. Whether this particular change matters is the review we are doing now.”

### 6. Revalidation

Open an affected item. Inspect its previous basis, the new revision, and the comparison. Record a revalidation only after that inspection.

When demonstrating a Project with multiple repository bindings, open the Project-wide advisory review. Explain that it gathers exact advisory candidates from every active binding so the review queue is complete, while preserving the binding/evidence context for each candidate. The aggregation is a convenience for review; it is not an affectedness judgment and must not collapse repository histories.

Narration contract: “Stale means the recorded basis moved and this item may need review. It does not mean the result is false. Revalidation records a new decision against an explicit basis.”

For advisory review, add: “Candidate means this advisory deserves inspection against this recorded inventory. It does not by itself mean the project is affected.”

### 7. Leave a next step

End in Help rather than a dead-end marketing CTA. Show these routes in order:

1. **Quickstart** — create real product state in about five minutes.
2. **Example Project** — replay the complete change → impact → revalidation loop safely.
3. **Learn** — plain-language mental model and worked examples.
4. **Docs** — canonical semantics, CLI, APIs, and object model.
5. **Integrations** — Codex, MCP, plugins, and installation paths.

The marketing site CTA should enter the hosted app at the same first-run path; the hosted Help surface should link back to Learn/Docs without changing terminology.

## Multi-repository launch shot

Use this optional 30–45 second insert when demonstrating supply-chain review:

1. Open one Project containing two repository bindings.
2. Show that each repository has its own scan history and latest inventory.
3. Open Compare for repository A and explicitly keep both compared observations inside repository A.
4. Return to Project review and show advisory candidates gathered from A and B.
5. Open one candidate and retain repository, package/version, advisory, and observation context on screen.
6. End before any automatic “safe/unsafe” conclusion; the next action is inspection or explicit revalidation.

This shot exists to make a subtle product boundary visible: Project-level review may aggregate candidates, while observation identity, comparison, and evidence remain binding-scoped.

## Recording checklist

Before publishing a recording or screenshots, verify all of the following:

- the Dashboard checklist order is Project → Monitor → first observation;
- the demo is visibly read-only/deterministic;
- Source and Revision appear only after the first-use mental model is established;
- repository scans visibly retain their repository binding context;
- a second scan is described as a new observation, not automatically as changed dependency state;
- supply-chain Compare never crosses repository bindings;
- Project-wide advisory review preserves per-binding candidate/evidence context;
- advisory candidate aggregation is never presented as an affectedness verdict;
- Compare precedes Impact in the changed-source story;
- Impact demonstrates an actual recorded reliance edge;
- Impact visibly inspects the recorded basis/revision before interpreting the selected change;
- missing Impact provenance is shown as unavailable rather than guessed;
- recorded reliance provenance is never presented as an affectedness verdict;
- Revalidation is an explicit user action, not an automatic verdict;
- no copy says or implies `recorded = verified`;
- no copy says or implies `fetched = relied`;
- no copy says or implies `changed = invalid`;
- no copy says or implies `stale = false`;
- no copy says or implies `EXPOSED_TO_MODEL = RELIED`;
- no generic trust/confidence score is shown;
- the final frame contains working Quickstart, Example, Learn, Docs, and Integrations entry points.

If the live UI differs from this sequence, fix the UI or update this canonical script and the onboarding contract together before recording. Do not silently narrate around product drift.
