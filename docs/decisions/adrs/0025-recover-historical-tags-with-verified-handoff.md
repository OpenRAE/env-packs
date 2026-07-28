# ADR 0025 — Recover historical tags with a verified object handoff

- Status: Accepted
- Date: 2026-07-28
- Amends: [ADR 0017](0017-sign-release-tags-with-keyless-sigstore.md)
- Amends: [ADR 0023](0023-recover-interrupted-signed-releases.md)
- Amends: [ADR 0024](0024-pin-gitsign-pre-regression-release.md)

## Context

The digest-pinned gitsign 0.15.1 recovery run successfully signed the historical
`v2.0.2` release commit and verified its Rekor entry, certificate claims, exact
workflow identity, and OIDC issuer. Its subsequent tag push was rejected by
GitHub because the built-in `GITHUB_TOKEN` is a GitHub App token without
workflow permission and the historical commit changes files under
`.github/workflows/`.

The job's declared `contents: write` permission cannot grant that separate
workflow permission to `GITHUB_TOKEN`. Persisting a broadly scoped personal
access token in the repository solely for this one historical release would
expand the long-lived release trust boundary.

## Decision

When, and only when, the tag step records that identity-bound gitsign
verification succeeded but the step later fails, the release workflow exports
the exact annotated-tag object as a GitHub Actions artifact. The artifact also
contains the tag object's Git object ID and the dereferenced target commit.
The upload action is commit-pinned, fails if the handoff files are absent, and
retains the artifact for one day.

An operator may download that short-lived object, reconstruct it locally, and
push it with existing workflow-scoped GitHub credentials only after all of the
following checks pass:

1. Hashing the exported object as a Git tag reproduces the exported object ID.
2. Dereferencing the tag reproduces the gate-selected historical commit.
3. The digest-pinned gitsign verifier accepts the exact workflow certificate
   identity and OIDC issuer required by ADR 0017.
4. The remote tag is still absent; the tag is never deleted, replaced, or
   force-updated.

The recovery workflow is then rerun. It consumes the remote tag only after
performing the same target and signature checks, and proceeds through the
normal build, attestation, SBOM, PyPI, GitHub Release, and release-please state
transition.

This handoff is a recovery path for a historical tag blocked by GitHub's token
policy. Normal releases continue to sign, verify, and push the current main
release tag automatically with `GITHUB_TOKEN`.

## Consequences

- The interrupted release can complete without weakening Sigstore verification
  or storing a broadly scoped personal access token as a repository secret.
- The operator pushes the exact tag object created and verified inside the
  trusted release environment, rather than recreating or resigning it locally.
- The failed workflow remains visibly failed until the verified handoff is
  completed and the recovery run succeeds.
- The one-day retention limits the lifetime of the recovery artifact and may
  require rerunning recovery if manual completion is delayed.
