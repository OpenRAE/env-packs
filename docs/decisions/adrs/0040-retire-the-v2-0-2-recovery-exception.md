# ADR 0040 — Retire the v2.0.2 recovery exception

- Status: Accepted
- Date: 2026-10-25
- Supersedes: [ADR 0026](0026-separate-historical-source-from-release-tooling.md)
  (the `v2.0.2` pre-lock exception)
- Supersedes: [ADR 0027](0027-publish-only-the-active-pypi-distribution.md)
  (the `v2.0.2` PyPI skip)

## Context

ADR 0026 and ADR 0027 added release-workflow exceptions for one target: the
signed `v2.0.2` tag at commit `45f39a930625c9de4c44017e8966d00b82f65052`.
The workflow built that target from `requirements/recovery-v2.0.2.txt` and
skipped PyPI for it.

The `v2.0.2` GitHub Release exists with its wheel, sdist, and SBOM. The
maintainer said: "I don't plan to publish 2.0.2."

## Decision

- The release workflow removes the `v2.0.2` exceptions.
- The repository deletes `requirements/recovery-v2.0.2.in` and
  `requirements/recovery-v2.0.2.txt`.
- Every release target consumes its own committed build, runtime, and SBOM
  locks. A target without them fails closed.
- PyPI publication allows only `raes-env-packs`. Every other distribution name
  fails closed.

## Consequences

- The release workflow can no longer build or publish the `v2.0.2` target.
- The existing `v2.0.2` GitHub Release does not change.
- The other decisions in ADR 0026 and ADR 0027 stay in effect.
