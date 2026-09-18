# Testamur Product API boundary

## Purpose

The product layer composes canonical Testamur kernels. It does **not** own a second database or truth model. `testamur.product_service.TestamurProductService` is the local composition root for the open-source core; Hosted may wrap the same contracts with remote storage, auth and scheduling.

## Stable envelopes

Product object reads return `testamur.product.object.v1`; errors use the shared `testamur.error.v1` envelope. History and comparison use `testamur.product.history.v1` and `testamur.product.compare.v1`.

The surface preserves these boundaries:

- recorded is not verified;
- a mechanical content change is not invalidity or falsehood;
- history ordering is local recorded history, not an ambiguous `as_of` query;
- a missing extension capability is explicit and is never reconstructed by guessing from legacy Witness state.

## Local/core product slice

The first composition surface is:

`Source -> Revision/Snapshot -> History -> Mechanical Compare -> Record -> Relation -> Watch -> Alert`.

The service reads those objects directly from `TestamurSourceStore`, `TestamurRecordStore` and `TestamurWatchStore`. It therefore preserves the same durable IDs and append-only rows used by the kernels.

## W2-W5 integration boundary

W1 owns composition, while W2-W5 own their semantic engines. `testamur.product_extensions.ProductExtensions` is the narrow dependency-injection boundary for canonical extension readers, temporal projection and reliance/lineage impact. It contains no Witness fallback.

The converged extension readers cover canonical `work_session`, `reliance`, `policy`, `assessment`, `lineage`, `affectedness`, `advisory` and related families through Testamur-owned hooks. Historical worker branches are implementation history, not future semantic owners. The product layer must not reinterpret those payloads or assign stronger epistemic status.

Temporal integration must preserve `KNOWN_AT != AVAILABLE_BY != EFFECTIVE_AT`. Impact integration must preserve `stale != false`, `changed != invalid`, and lineage propagation as attention rather than vulnerability verdict.

### Temporal object-read contract

`TestamurProductService.temporal(ref, query)` is an object-scoped temporal read, not a global temporal search followed by a Python-side filter. Its resolution order is normative:

1. select the requested `object_ref=ref` and ordinary state assertions (first-class temporal audit events are excluded from this state view);
2. resolve network/node perspective inside that non-temporal object scope;
3. if more than one perspective remains and the caller did not select one explicitly, fail closed;
4. only after perspective resolution, apply `KNOWN_AT`, `AVAILABLE_BY`, and/or `EFFECTIVE_AT` cuts.

A time cut must never silently choose a perspective. Conversely, a different object that exists only under another perspective must not make the current object's read ambiguous. Explicit `perspective` selection is therefore semantic input, not merely an optimization hint.

Malformed temporal clauses, invalid limits, and unresolved multi-perspective reads return the shared `testamur.error.v1` envelope with code `invalid_temporal_query`; they must not leak a raw temporal-engine exception across the product boundary.

The `testamur.product.temporal.v1` success envelope exposes semantic flags confirming that the read is object-scoped, perspective-fail-closed, and excludes temporal audit-event rows from ordinary state results.

### Temporal event-read contract

Retrospective discoveries, late observations, historical-availability discoveries, and retrospective corrections are first-class W2 events and have a separate product read surface:

```text
TestamurProductService.temporal_events(ref, query)
-> testamur.product.temporal-events.v1
```

This surface is subject-scoped by `ref`. Optional `event_kinds` are part of the non-temporal scope, so filtering to one event family may legitimately remove a perspective ambiguity. `recorded_by` and `event_time_by` are temporal cuts and therefore must **not** choose a perspective. Perspective resolution happens after subject/kind scope and before either time cut.

`recorded_by` means when the selected Testamur perspective durably recorded the event. `event_time_by` filters the represented-world occurrence time when that time is exact/queryable. They are not interchangeable: discovering in 2028 that something happened in 2023 must remain recorded in 2028.

Ordinary `temporal()` state reads never mix these event rows into object-state results. Event query failures use `testamur.error.v1` with code `invalid_temporal_event_query`. Capability discovery reports `temporal` and `temporal_events` independently so alternate/Hosted compositions may expose one without pretending the other exists.

## Open-source boundary

The open-source Testamur CLI/core should include local evidence capture, Source/Record/Relation/Watch kernels, history/compare, trace/impact, verification, portable contracts/protocols, and safe agent/plugin protocol pieces. A fresh local install must require the Python package `testamur`, not `witness`.

## Closed-source Hosted boundary

Hosted may add accounts, workspaces, authentication, billing, quotas, private-source handling, hosted storage/index/search, scheduled revalidation/watch execution, alert delivery, organizations, managed runners/connectors, web UI, operations/admin infrastructure, and commercial analytics/abuse controls.

Hosted must consume canonical Testamur IDs, envelopes and semantic engines. It may change persistence and delivery mechanics, but must not create a second meaning for verification, reliance, policy, temporal reconstruction, lineage, or affectedness.

## Release gate

Before release, the converged W1-W5 implementation must pass the exact-head repository-local release gate, including the complete current `tests/test_testamur_*.py` suite and structural namespace audit. Production/runtime Testamur must import no Python module under `witness`. Historical `wtn:*` identifiers may remain readable where durable compatibility requires them; identifier compatibility does not require the Witness Python package.
