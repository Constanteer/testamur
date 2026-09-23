# Impact review card contract

Status: launch UX contract

## Goal

The Impact surface should let a reviewer answer **why this downstream object is in the review set** without reading raw JSON or inferring affectedness from provenance.

For every projected downstream edge, the UI should expose the provenance that the provider actually returned, when available:

- downstream object identity and an `Open` action;
- relation / edge identity or kind;
- the recorded basis object or revision that justified the reliance edge;
- the time the reliance/provenance was recorded, when supplied;
- a direct action to inspect that basis/revision.

Missing provenance stays missing. The Web layer must not synthesize a basis, relation, timestamp, or affectedness verdict to make a card look complete.

## Semantic boundary

An Impact card is an **inspectable review candidate**, not a verdict.

- `recorded != verified`
- `fetched != relied`
- `EXPOSED_TO_MODEL != RELIED`
- `changed != invalid`
- `stale != false`
- edge basis explains why reliance was recorded; it does not establish that the selected change affected that reliance.

The card may summarize fields already present in the canonical `/v1/impact` response. It must not infer reliance from fetch/model exposure, infer affectedness from a mechanical diff, or introduce a generic trust score.

## Presentation

Preferred card hierarchy:

1. **Review candidate** — human-readable downstream title/kind plus stable ref.
2. **Why it appears here** — provider-supplied relation/reason only.
3. **Recorded basis** — basis/revision ref with `Inspect basis` when resolvable through the canonical object surface.
4. **Recorded at** — only when the provider supplies a timestamp.
5. **Actions** — `Open downstream` and, when possible, `Inspect basis`.

If the provider returns only a downstream ref/reason, render those facts and an explicit `Basis not supplied by this provider` note rather than fabricating provenance.

## Navigation context

Impact-card actions must preserve the selected review scope already carried by the contextual workflow (`project`/`project_id`, `dependency`/`component`, `from`, `to`) where the destination participates in the review workflow. Navigation context is presentation scope only; carrying it must not alter canonical object identity or provider semantics.

## Acceptance checks

- A reviewer can distinguish the downstream object from the basis/revision that caused it to enter the review set.
- Provider-supplied basis/revision is inspectable in one action.
- Missing basis is visibly missing, not guessed.
- The selected Compare pair remains visible after following Impact review actions.
- No card text equates an edge with affectedness, invalidity, falsity, verification, or trust.
- Raw/provider-specific payload remains available for advanced inspection without becoming the primary launch UX.

## Implementation target

The current `impactPanel(ref)` in `testamur/web/app.js` renders array results as a minimal title/reason/Open row and falls back to raw JSON for non-array payloads. The next implementation step is to normalize only **known provider-supplied provenance fields** into the card above while retaining a lossless advanced/raw path. Do not normalize unknown fields into semantic claims.