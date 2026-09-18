# Testamur Watch / Alert Kernel

> **Status:** implemented local operational kernel for the early Watch → Alert product slice.

Implementation:

```text
testamur/watch_store.py
```

## 1. Operations, not truth

Watch is an operational object over an existing durable Source.

It answers questions such as:

```text
has this Source changed since the previous evaluated Snapshot?
is the latest evaluated observation unavailable?
did observation recover after an unavailable/not-assessable state?
```

It does not answer:

```text
is the Source true?
is the Source trustworthy?
did a changed Source make a downstream Record false?
```

The core rule is:

```text
operational transition != epistemic truth transition
```

## 2. Durable objects

```text
tst:watch:*            persistent Watch identity
tst:watch-revision:*   immutable configuration revision
tst:watch-eval:*       immutable evaluation of a Snapshot
tst:alert:*            immutable operational alert event
```

A Watch points to one existing Source identity.

Watch configuration changes append a new WatchRevision instead of rewriting the old configuration.

## 3. Initial alert vocabulary

The initial alertable events are deliberately small:

```text
changed
unavailable
recovered
```

`unchanged`, `initial` and `not_assessable` remain evaluation states but do not generate alerts by default.

## 4. Snapshot transition semantics

Given the previous evaluated Source Snapshot and a new Snapshot:

```text
no previous + available
  → initial

available + same Revision
  → unchanged

available + different Revision
  → changed

available/recovered + unavailable status
  → unavailable

unavailable/not_assessable + available
  → recovered

metadata-only / uncapturable state
  → not_assessable
```

`changed` is exact Revision identity change. It does not imply semantic meaning changed.

Repeated unavailable observations do not repeatedly emit the same unavailable transition alert unless a later recovery/new transition occurs.

## 5. Evaluation identity and replay

Evaluation is bound to:

```text
Watch
WatchRevision
Source
Snapshot
previous evaluated Snapshot
operational state
recording time
```

Re-evaluating the same Snapshot for the same Watch reuses the already persisted evaluation/alert instead of duplicating an operational event.

Historical replay under a different policy/time perspective is intentionally not hidden inside this default operational loop. That belongs to an explicit future replay/temporal query mode.

## 6. Alerts

Alert is an immutable append-only event produced only when:

```text
an operational transition has an event type
AND
that event type is enabled by the active WatchRevision
```

Alert storage does not currently encode mutable inbox acknowledgement/read state. Those are user/workspace presentation concerns and should not mutate the historical alert event itself.

## 7. Configuration revisions

Watch configuration includes an `alert_on` event set and optional label.

Appending a configuration revision requires the caller's expected parent revision. A stale caller fails rather than silently overwriting a newer configuration head.

Changing alert configuration does not retroactively rewrite or manufacture historical alerts for old Snapshot evaluations.

## 8. Append-only rule

Watch, WatchRevision, Evaluation and Alert tables reject UPDATE/DELETE.

If future operations need lifecycle state such as disable/pause/acknowledge, prefer explicit append-only operational events or separately scoped mutable user-state projections instead of rewriting historical evaluation facts.
