# Testamur launch walkthrough

The canonical launch/demo script lives at [`TESTAMUR_LAUNCH_WALKTHROUGH.md`](./TESTAMUR_LAUNCH_WALKTHROUGH.md).

This compatibility page intentionally does not duplicate the narration or recording checklist. Keeping one source of truth prevents launch guidance from drifting away from the current first-run product flow, five-minute quickstart, and integration surfaces.

For the executable first-use path, use [`TESTAMUR_5_MINUTE_QUICKSTART.md`](./TESTAMUR_5_MINUTE_QUICKSTART.md).

The launch contract keeps these distinctions explicit:

```text
recorded != verified
fetched != relied
changed != invalid
stale != false
EXPOSED_TO_MODEL != RELIED
```

Neither the walkthrough nor the quickstart introduces a generic trust score. If deployed UI differs from the canonical walkthrough, treat that as product drift to fix rather than narrating around it.
