# Security Policy

## Supported versions

Testamur is currently maintained on the latest public release line and on `main`.
Security fixes may be applied to the latest release and then carried forward to
`main` as appropriate.

## Reporting a vulnerability

Please do not open a public issue for an undisclosed vulnerability.

Use GitHub's private vulnerability-reporting / Security Advisory flow for this
repository when it is available. Include enough information to reproduce and
assess the issue:

- affected Testamur version or commit;
- affected component (CLI, local Web, Source Gateway/MCP, storage, monitoring, etc.);
- security impact and realistic attack preconditions;
- minimal reproduction steps or proof of concept;
- any known mitigations.

Do not include real credentials, private source content, access tokens, or user
data in a report.

If the private GitHub reporting flow is unavailable, contact the maintainers
through a private channel rather than publishing exploit details.

## Security model notes

Testamur records provenance and review evidence; it does not convert recorded
facts into trust or verification claims. Security fixes must preserve the
semantic boundaries that are part of the product contract:

- `recorded != verified`
- `fetched != relied`
- `changed != invalid`
- `stale != false`
- `EXPOSED_TO_MODEL != RELIED`

A security-related upstream change or advisory may create a review candidate,
but identity overlap alone must not silently become an affectedness verdict.

## Secrets and local data

Local Testamur state may contain source metadata, snapshots, work-session events,
or other evidence. Treat `TESTAMUR_HOME`, `TESTAMUR_DB`, hosted workspace
databases, and exported evidence as potentially sensitive. Do not commit local
state databases or credentials to the repository.
