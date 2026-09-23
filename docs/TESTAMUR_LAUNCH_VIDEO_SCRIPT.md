# Testamur launch walkthrough video script

Target length: 4–5 minutes. Audience: someone who has a project or source they care about, but does not need to know Testamur's internal object model first.

The walkthrough deliberately uses the product vocabulary already exposed by Testamur. It does not introduce a trust score or a second onboarding ontology.

## 0:00–0:25 — The question

**Screen:** Testamur landing page, then open the hosted app.

**Voice:**

> Software and research increasingly depend on things you did not write: source material, package revisions, scanners, advisories, model-visible context, and previous checks. Testamur does not ask you to trust all of that. It records enough of the chain that you can ask what changed, what was actually relied on, and what needs another check.

**On-screen callout:** `recorded ≠ verified` · `fetched ≠ relied`

## 0:25–1:05 — Start with a Project

**Screen:** Create/open the demo Project. Show repository bindings and the supply-chain surface.

**Voice:**

> A Project is the place where related evidence is reviewed together. Bind a repository or use the demo project. A binding tells the scanner where it is allowed to look; it is not itself evidence that the repository is safe or valid.

> Run the supply-chain scan. Testamur records the observed dependency material and the revision it came from. If a Project has more than one repository binding, each scan remains attributable to its binding instead of being flattened into one unexplained result.

**On-screen callout:** `binding = scanner eligibility, not verification`

## 1:05–1:45 — Source → Revision

**Screen:** Open a Source, then its revision/history surface.

**Voice:**

> Testamur separates a Source from the revisions observed for that Source. Fetching a revision records what was retrieved and when. It does not silently say that anybody relied on it.

> This distinction matters when an upstream page, package, paper, or repository moves. You can still point to the exact recorded revision that entered the chain.

**On-screen callout:** `fetched ≠ relied`

## 1:45–2:25 — Compare is a trigger, not a verdict

**Screen:** Open History / Compare for two revisions. Highlight changed material.

**Voice:**

> Compare answers a mechanical question: what changed between these recorded revisions? A difference is a reason to inspect downstream assumptions. It is not a declaration that the new revision is wrong.

> The same rule applies to staleness. Stale means a check may need to run again; it does not mean the old result became false.

**On-screen callout:** `changed ≠ invalid` · `stale ≠ false`

## 2:25–3:15 — Advisory candidate → Impact

**Screen:** Return to Project supply-chain advisories. Open one exact candidate, then Impact.

**Voice:**

> Advisory matching nominates work for review by exact recorded identity overlap. A candidate is not an affectedness verdict. Open Impact to see which recorded relations and downstream objects are relevant before deciding what evidence to collect.

> When applicability evidence is recorded, Testamur preserves the assessment head and its basis. Competing unsuperseded heads stay visible instead of being resolved by insertion order or collapsed into a generic score.

**On-screen callout:** `candidate ≠ affected` · `assessment ≠ global truth`

## 3:15–3:55 — Revalidation closes the loop

**Screen:** Open Revalidation from the selected advisory/dependency context. Keep the visible Project, dependency/component, and before → after revision pair on screen; then return to the originating Project after recording the scoped check.

**Voice:**

> Revalidation is the operational end of the loop. The selected dependency and before-to-after revision pair remain visible so you can see the prior basis for this check instead of treating it as an isolated verdict. A changed or stale dependency tells you where another check may be warranted; it does not establish invalidity, affectedness, or reliance.

> Record the scoped check and preserve its result alongside the earlier record rather than rewriting history. Then return to the Project and continue with another binding or advisory candidate. Completing this one revalidation does not verify the whole Project.

> The result is an auditable chain you can inspect later: source, revision, selected comparison, explicit impact/reliance evidence, and the scoped check that followed.

**On-screen callout:** `scoped revalidation ≠ project-wide verification`

## 3:55–4:25 — Agents and integrations

**Screen:** Integrations page. Briefly show CLI and MCP/Codex installation entry points.

**Voice:**

> The same boundaries apply when an agent is involved. Material exposed to a model is not automatically material the model relied on. Testamur's CLI and MCP surfaces let tools record and inspect the same provenance without inventing a separate agent truth model.

**On-screen callout:** `EXPOSED_TO_MODEL ≠ RELIED`

## 4:25–4:45 — Close

**Screen:** Return to the Project overview, with Help / Learn visible.

**Voice:**

> Testamur is not a universal trust score. It is a way to preserve the evidence needed to answer “why?” later. Start with the five-minute quickstart or the demo project, record one real dependency chain, and follow it when something changes.

**End card:** `Source → Revision → Compare → Impact → Revalidation`

## Recording checklist

- Use the demo/example Project so the walkthrough is reproducible without private data.
- Keep browser zoom large enough that revision IDs, state badges, and next-step links remain readable at 1080p.
- During Compare → Impact → Revalidation, keep the selected dependency/component and before → after pair visible; do not silently switch scope between stages.
- After Revalidation, return to the originating Project and show that other bindings/candidates remain reviewable.
- Do not describe a recorded item as verified unless a specific verification record supports that statement.
- Do not describe a fetched item as relied on unless a reliance relation exists.
- Do not describe a changed revision as invalid or a stale result as false.
- Do not describe advisory identity overlap as affectedness.
- Do not describe a completed scoped revalidation as project-wide verification.
- Do not describe model exposure as reliance.
- If a live hosted surface is temporarily unavailable, cut to a pre-recorded capture rather than changing the semantic explanation to fit an error state.
