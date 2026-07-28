# ADR 0026 — Separate historical source from release tooling

- Status: Accepted
- Date: 2026-07-28
- Amends: [ADR 0023](0023-recover-interrupted-signed-releases.md)
- Amends: [ADR 0025](0025-recover-historical-tags-with-verified-handoff.md)

## Context

Recovery successfully published and reverified the signed `v2.0.2` tag, then
failed before building because the signed release commit predates the
repository's `requirements/` lock files. The current workflow correctly
requires hash-locked build and SBOM tooling, but checking out the historical
source also removed those later release controls from the working tree.

Building a different source commit would violate the signed tag. Falling back
to unconstrained package installation would weaken the current supply-chain
policy. Using the current RAES runtime lock would also produce an inaccurate
SBOM for the final historical distribution, whose declared runtime dependency
is the retired ACES SDL distribution.

## Decision

The release source and the release tooling are treated as separate identities:

- The package source remains checked out at the exact gate-selected commit
  dereferenced by the verified signed tag.
- Normal release targets materialize their build, runtime, and SBOM locks from
  that same target commit.
- The sole pre-lock exception is bound to both `v2.0.2` and commit
  `45f39a930625c9de4c44017e8966d00b82f65052`. It materializes a dedicated
  combined lock from the current workflow commit.
- The recovery lock contains the historical package runtime closure, the
  historical SBOM generator version, and the current hash-locked build
  toolchain. Every distribution is exactly pinned and hash-verified.
- A missing-lock target other than that exact tag-and-commit pair fails closed.

The materialized locks are release inputs only. They are not included in the
wheel or sdist, whose Hatch include lists remain governed by the signed source
commit.

## Consequences

- Recovery builds the exact signed historical source while retaining the
  repository's current hash-verification requirement.
- The generated SBOM reflects the historical distribution's dependency closure
  instead of the renamed RAES package's current closure.
- Retired dependency names exist in two narrowly allowlisted recovery-lock
  files. They do not re-enter current project metadata, imports, or runtime
  behavior.
- Future pre-lock recoveries require a new explicit tag-and-commit decision;
  the workflow cannot silently reuse this exception.
