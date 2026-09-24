# Deterministic evidence-flow demo

This fixture is the small, offline launch/demo input for the Source → Revision → Compare → Impact → Revalidation journey. It is intentionally plain text so screenshots, onboarding, CLI/MCP examples, and hosted acceptance checks can all use the same deterministic change without network access.

## Fixture

`baseline/policy.txt` is the first Source revision. `current/policy.txt` changes exactly one meaningful statement: the refund window moves from 30 days to 14 days. The USD 500 manual-review rule stays unchanged.

`downstream/refund-playbook.txt` is a downstream artifact whose recorded basis explicitly names the baseline policy and quotes the 30-day statement. That recorded provenance makes it a useful Impact review candidate after the policy changes.

## Five-minute journey

1. Create/select one disposable demo Project.
2. Record `baseline/policy.txt` as the canonical Source's first revision.
3. Record `current/policy.txt` as a second immutable revision of the same Source.
4. Open Compare and verify that the meaningful diff is `30 days` → `14 days`.
5. Open Impact and inspect `downstream/refund-playbook.txt` as a review candidate. Show its recorded basis/revision provenance before interpreting the change.
6. Decide explicitly whether the playbook is affected. The fixture is constructed so a reviewer can conclude that its 30-day guidance needs review, but Testamur must not manufacture that conclusion from the diff alone.
7. Revalidate explicitly after reviewing/updating the downstream artifact.

The fixture is disposable and requires no fetch, package registry, advisory service, or other external network dependency.

## Acceptance boundaries

The demo must preserve the product ontology rather than teaching shortcuts:

- recorded != verified
- fetched != relied
- changed != invalid
- stale != false
- EXPOSED_TO_MODEL != RELIED
- recorded reliance provenance != affectedness

A revision difference is evidence of change, not an invalidity verdict. A downstream artifact with recorded basis is a review candidate, not automatically affected. If a provider cannot supply basis/revision provenance, the UI should say it is unavailable rather than infer it from timestamps, current revision, or list order.

This fixture does not define a trust score and must not be used to introduce one.
