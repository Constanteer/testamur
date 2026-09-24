# Testamur onboarding contract

Status: product UX contract for first-run and explanatory surfaces.

## Goal

A new user must be able to understand and complete the first Testamur loop without first learning the internal ontology.

The first-use mental model is:

```text
I use something
    ↓
Testamur remembers the exact basis
    ↓
that basis changes later
    ↓
Testamur shows what may need review
    ↓
I inspect the recorded basis, decide affectedness, and revalidate
```

Do not lead first-run UI with internal names such as `SourceRevision`, `WorkSession`, `Affectedness`, or canonical `tst:*` identifiers. Those remain available as inspectable advanced concepts.

## Required first-run surfaces

1. Dashboard onboarding checklist:
   - create a Project;
   - add a Monitor;
   - record the first observation.
2. Empty Project guidance explaining what a Monitor can target.
3. First-change contextual guidance:
   - change is an event, not a verdict;
   - history and impact are the next inspection surfaces.
4. A deterministic example Project showing:
   - old revision;
   - new revision;
   - mechanical compare;
   - downstream review candidates with their recorded basis/revision provenance;
   - explicit affectedness decision;
   - explicit revalidation.
5. A five-minute quickstart that creates real product state.
6. A persistent Help entry linking to:
   - quickstart;
   - example Project;
   - plain-language product explanation;
   - integrations.
7. Launch walkthrough scripts that preserve the same semantics as the product UI.

## Language ladder

### Layer 1 — first use

Use:

```text
Project
Monitor
something you rely on
recorded version
changed
needs review
```

### Layer 2 — product inspection

Introduce:

```text
Source
Revision
History
Compare
Reliance
Impact
Revalidation
```

### Layer 3 — advanced / canonical model

Expose when useful:

```text
WorkSession
Lineage
Affectedness
temporal clauses
canonical IDs
raw envelopes
provider/extension contracts
```

The advanced layer must remain inspectable but should not be prerequisite knowledge for the basic loop.

## Semantic firewall

Every onboarding surface must preserve:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
EXPOSED_TO_MODEL != RELIED
recorded reliance provenance != affectedness
```

No onboarding copy may introduce a generic trust/confidence score as a substitute for explicit evidence states.

Impact is a review-candidate surface, not an affectedness verdict. When Testamur has recorded a downstream basis/revision, onboarding should show that provenance before asking for an affectedness decision. If the provider did not record that provenance, the UI must say it is unavailable; it must not infer a basis from timestamps, the current revision, or list order.

## Demo Project rule

The example Project is explanatory, deterministic, and must not write user workspace state.

It exists because Testamur's value often appears only after an upstream dependency changes. New users should be able to see that later-state workflow immediately instead of waiting for a real source to move.

## Video / walkthrough rule

The checked-in launch-video scripts are the narration/shot source of truth. Browser walkthroughs should mirror the same order so recorded media, captions, docs, and the live product do not drift semantically.
