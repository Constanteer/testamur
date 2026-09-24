# Testamur five-minute launch video

This is the recording-ready companion to `launch-walkthrough.md`. Record the product path as it exists; do not edit around a broken or unavailable state. If a shot cannot be completed, treat that as a launch defect.

## Recording rules

- Target 4:30–5:00. Keep terminal footage to the final integrations segment.
- Use the bundled disposable demo. Do not use personal or production evidence.
- Keep Project, Source, revision IDs, comparison direction, and downstream candidate visible when they matter.
- Never narrate a retrieval, diff, stale marker, integration check, or recorded relationship as a correctness verdict.
- Do not show or invent a generic trust/confidence score.

## Shot list and narration

### 0:00–0:25 — First run

**Screen:** Landing/first-run state. Click **Try the demo**. Wait for the demo Project to open.

**Narration:** “Testamur keeps the evidence behind a decision inspectable. This demo records a source, how it changed, and which downstream work may deserve another look.”

**Capture gate:** The primary action is visible without opening docs; demo creation needs no external network request; the resulting Project is visibly marked as example/demo data.

### 0:25–1:05 — Project → Source

**Screen:** Show the Project summary and Sources. Open the canonical demo Source. Hold briefly on source identity and latest recorded revision.

**Narration:** “This is a recorded source and its revision history. Recorded is not verified, and fetched is not relied upon. Testamur is preserving provenance here, not endorsing the source.”

**Capture gate:** Project → Source is an obvious click path; source identity and latest revision are visible; no badge or copy implies verification merely from retrieval.

### 1:05–1:55 — Revision → Compare

**Screen:** Open Source history. Select the two seeded revisions. Open Compare and point to one meaningful changed region plus the revision direction.

**Narration:** “These two observations differ. The comparison tells us what changed and in which direction; changed does not mean invalid.”

**Capture gate:** Both revision identities remain recoverable from the view; comparison direction is unambiguous; no-change and error states, if encountered, expose a next action rather than a dead end.

### 1:55–2:55 — Compare → Impact

**Screen:** Continue to Impact. Open one downstream review candidate. Show its recorded basis/revision provenance before discussing the current change. If the provider does not supply provenance, show the explicit unavailable state rather than inferring one.

**Narration:** “This downstream item was connected to recorded evidence. Its recorded basis explains why the relationship exists; it does not prove that this particular change affected or invalidated the work. Exposure to a model is also not reliance.”

**Capture gate:** The viewer can answer what to inspect next and why the candidate is present. Do not infer provenance from timestamps, current revision, list order, or object proximity. Recorded reliance provenance is not affectedness.

### 2:55–3:55 — Impact → Revalidation

**Screen:** Open the candidate’s revalidation flow. Show the evidence under review, the observed change, and the available explicit action. In the disposable demo, record the intended review decision if the fixture supports it.

**Narration:** “Revalidation is a review action, not an automatic consequence of change. Stale does not mean false. We inspect the evidence and make the decision explicitly.”

**Capture gate:** A changed Source does not silently flip validity. The UI distinguishes observation/state from the user’s explicit review decision and provides a route back to the scoped Project.

### 3:55–4:25 — Help / Docs / Learn

**Screen:** Open Help, Docs, or Learn from the product navigation and show the matching Source → Compare → Impact → Revalidation explanation.

**Narration:** “The same workflow is documented in-product, so you do not need to learn Testamur’s internal model before using it.”

**Capture gate:** Documentation is reachable from the hosted app and returns to the product without a navigation dead end.

### 4:25–5:00 — CLI / Codex / MCP

**Screen:** Open Integrations. Show the CLI install entry, Codex plugin path, MCP setup, and diagnostic commands. Terminal footage may be used here only.

**Narration:** “For automated workflows, the same evidence model is available through the CLI, Codex, and MCP. A successful diagnostic proves the integration is wired and reachable; it does not verify a Source or establish reliance.”

**Capture gate:** Installation and diagnostics match the currently shipped executable names and protocol contract. Host/runtime success is described as wiring evidence only.

## Required end-frame

Return to the demo Project or product home, not a terminal. The viewer should leave with one mental model: **record evidence → inspect change → inspect downstream relationships → explicitly revalidate**.

Do not add a trust score or compress the ending into “Testamur tells you what to trust.”

## Pre-publish acceptance

Before publishing, watch the recording once with audio muted and once without looking at the cursor. The visual path alone must preserve revision direction and review scope; the narration alone must preserve these invariants:

- recorded != verified
- fetched != relied
- changed != invalid
- stale != false
- EXPOSED_TO_MODEL != RELIED
- recorded reliance provenance != affectedness

If any invariant depends on a spoken disclaimer contradicting the visible UI, fix the UI before publishing the video.