# Testamur launch usability acceptance pass

Status: executable product acceptance checklist for the launch path. This complements `TESTAMUR_LAUNCH_WALKTHROUGH.md`; it does not define a second ontology.

Run this pass against the hosted product before recording launch material or declaring the first-run path ready.

## First run

1. Start with an empty account. The first visible task is to create a Project, not to learn Source/Revision identifiers.
2. Create a Project and confirm the next action is obvious: add a Monitor or open the deterministic example.
3. Add a Monitor and record the first observation. The UI must distinguish the fetched material, the recorded Revision, and any later reliance.
4. Open Help from the working surface. Quickstart, Example, Learn, Docs, and Integrations must be reachable without returning to the marketing site.
5. Follow one integration entry point (Codex, MCP, or plugin) far enough to reach an install/configuration instruction rather than a dead end.

Acceptance language: `recorded != verified`; `fetched != relied`.

## Repository scan and Compare

Use one Project with two repository bindings, A and B, and at least two observations for A.

1. Project → Supply chain shows both repository locators in human-readable form.
2. The binding guidance makes it clear that A and B are separate histories; an internal binding identifier is not required vocabulary.
3. Review observation history from the Project surface. A user must be able to determine which repository produced every observation used for comparison.
4. Form a Compare pair from two observations of A. Both endpoints retain A's repository context.
5. Attempting to reason from A → B as a before/after pair must be prevented by the UI or explicitly rejected by the workflow. Never manufacture a cross-binding diff.
6. Record another scan of A. The UI may call it a new observation; it must not claim dependency state changed until a mechanical comparison establishes a delta.

Acceptance language: `changed != invalid`; new observation != changed dependency state.

## Impact and advisory review

1. From a valid same-binding Compare, continue to Impact without losing the compared revision/observation context.
2. Impact distinguishes an explicit recorded reliance edge from material merely fetched or exposed to a model.
3. Open Project-wide advisory review. Candidates from A and B may appear in one review queue.
4. Open one candidate. Repository, package/version, advisory, and observation/evidence context remain inspectable.
5. No aggregate badge, score, color, or copy converts candidate aggregation into an affectedness, safety, validity, or trust verdict.

Acceptance language: `EXPOSED_TO_MODEL != RELIED`; candidate != affectedness verdict.

## Revalidation

1. Enter Revalidation from the affected item/candidate path with the relevant comparison/evidence context still available.
2. Staleness is described as a review condition, not falsity.
3. Revalidation requires an explicit decision/action; merely opening the new revision must not silently clear the review condition.
4. After revalidation, the prior recorded basis remains inspectable so the decision is auditable.

Acceptance language: `stale != false`.

## Navigation continuity

Walk the public-to-product path once without using browser history:

`marketing site → hosted app → first-run → Project → Monitor → observation → Compare → Impact → Revalidation → Help → Learn/Docs → integration install`

Fail the pass if any transition requires guessing an undocumented URL, changes terminology for the same concept, or drops the object/repository context needed to understand the next screen.

## Failure policy

A missing or unexecuted CI gate is not a green gate. If GitHub Actions has no assigned runner, `runner_id=0`, empty steps, or another infrastructure failure, record that state and continue static/product verification. Do not describe the gate as passed.

A launch recording must not narrate around a broken transition. Fix the product path first, then update the walkthrough only when the intended product behavior itself changed.
