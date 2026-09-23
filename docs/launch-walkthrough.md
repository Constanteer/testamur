# Testamur launch walkthrough

This is the canonical five-minute product walkthrough and a launch acceptance checklist. It is deliberately evidence-first: the walkthrough must not imply that recording, fetching, comparing, or displaying a source verifies it or establishes reliance.

## Audience and outcome

A first-time non-developer should finish with one Project, one Source, at least two recorded revisions, one comparison, an understandable impact view, and one explicit revalidation decision. The user should also know where Help, Docs, Learn, CLI, Codex, and MCP entry points live.

## Five-minute path

### 0:00–0:30 — Start from the product, not the ontology

Open Testamur and choose **Try the demo** (or create a Project if the demo has already been used). Explain the product in one sentence: Testamur records what evidence was observed, what changed, and what downstream claims or decisions may need another look.

Acceptance: a new user can identify the primary action without reading documentation first. Do not show a generic trust score.

### 0:30–1:15 — Project and Source

Open the demo Project. Point out its Sources and add/open one canonical Source. Show the source identity, retrieval/recording state, and latest recorded revision.

Say explicitly: **recorded does not mean verified; fetched does not mean relied upon.** A retrieval is provenance, not an endorsement.

Acceptance: the UI makes the Project → Source relationship obvious and exposes the next action without requiring CLI knowledge.

### 1:15–2:15 — Revision and Compare

Open the Source history, select two revisions, and open Compare. Identify what changed and which revision is newer.

Say explicitly: **changed does not mean invalid.** A diff is an observation. It can trigger review, but it is not itself a correctness judgment.

Acceptance: revision identity and ordering are visible; Compare can be reached from the Source flow; empty/no-change/error states give a next step rather than a dead end.

### 2:15–3:15 — Impact

Move from the comparison to Impact. Show the concrete downstream records that may be affected and why they are connected to this Source/revision.

Say explicitly: **EXPOSED_TO_MODEL is not RELIED.** Exposure alone must not be promoted to reliance, and stale does not mean false.

Acceptance: the user can answer “what should I inspect next?” without interpreting an opaque score. Impact must preserve relationship/provenance semantics rather than collapse them into confidence.

### 3:15–4:15 — Revalidation

Open the revalidation flow for one affected item. Show what evidence is being reconsidered, what changed, and what action is available. Record a decision only if the walkthrough environment is intended to persist it.

Acceptance: revalidation is visibly an explicit review/action, not an automatic consequence of change. A changed Source must not silently invalidate dependent work.

### 4:15–5:00 — Learn and integrations

Open Help / Docs / Learn and show where the same workflow is explained. Then open Integrations and point to CLI, Codex, and MCP setup plus diagnostics.

Acceptance: a user who wants to continue can find a human-readable guide; a developer can find installation/diagnostic commands; successful integration diagnostics are described only as wiring/runtime evidence, never Source verification.

## Demo data contract

The bundled demo should be deterministic and disposable. It should contain enough state to exercise Project → Source → Revision → Compare → Impact → Revalidation without network access. Demo fixtures must be clearly labeled as examples and must not be mixed with a user's real evidence records.

The demo should include: one Project; one canonical Source; two distinguishable recorded revisions; a meaningful but small diff; at least one downstream relationship suitable for Impact; and a revalidation candidate whose correct lesson is “inspect and decide,” not “the newer revision is automatically true.”

## Recording script

Use the five sections above as the launch video shot list. Keep the cursor on the product path and avoid terminal footage until the final integrations segment. Prefer showing actual states and transitions over describing architecture. If a state is unavailable in the deployed build, call that out and fix the product path rather than editing around it in the video.

## Launch acceptance failures

Treat any of these as a launch-path defect: first-run has no obvious primary action; demo creation fails or depends on external network access; Source history cannot reach Compare; Compare cannot reach an understandable Impact view; Impact implies a generic trust/confidence score; revalidation silently changes validity; Help/Docs/Learn strands the user; marketing and hosted navigation disagree about where the app lives; integration guidance claims verification from installation or transport success; or a deployed static asset can remain stale across a release.

## Semantic invariants

These statements are non-negotiable throughout onboarding, demo copy, product UI, docs, and video narration:

- recorded != verified
- fetched != relied
- changed != invalid
- stale != false
- EXPOSED_TO_MODEL != RELIED

Onboarding may explain the existing model, but must not introduce a second ontology or a generic trust score.
