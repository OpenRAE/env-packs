# ADR 0024 — Pin the pre-regression gitsign release

- Status: Accepted
- Date: 2026-07-28
- Amends: [ADR 0017](0017-sign-release-tags-with-keyless-sigstore.md)
- Amends: [ADR 0023](0023-recover-interrupted-signed-releases.md)

## Context

The first `2.0.2` publication attempt and the authenticated recovery run both
failed before pushing a tag. gitsign 0.16.1 created the keyless CMS signature,
but `gitsign verify-tag` could not match the embedded Rekor transparency-log
record. Five bounded retries returned the same digest mismatch, demonstrating
that this was not normal transparency-log propagation delay.

gitsign 0.16.0 introduced a raw-object verification change. Its upstream pull
request records that the end-to-end Sigstore checks were unavailable when it
merged because of a GitHub Actions outage. Version 0.15.1 predates that change,
contains `verify-tag`, and remains above this repository's 0.15.0 security floor
for CVE-2026-44310.

## Decision

The release workflow temporarily pins gitsign 0.15.1. It downloads the official
Linux release asset over HTTPS and verifies the artifact against its published
SHA-256 digest before executing it. The exact version and digest are canonical
workflow environment values guarded by repository tests.

All existing release controls remain in force: the tag is annotated and signed
at the gate-selected commit, the exact GitHub workflow identity and OIDC issuer
must verify, Rekor verification remains mandatory, and failure still occurs
before the tag is pushed or any artifact is published. Existing remote tags
must dereference to the selected commit and pass the same identity-bound
verification before reuse.

The pin may advance only after a newer upstream release passes an end-to-end
annotated-tag signing and identity-bound verification run. A retry delay alone
is not evidence that the regression is fixed.

## Consequences

- The interrupted `2.0.2` release can be retried without weakening signer
  identity, bypassing Rekor, or accepting an unverified tag.
- The signer binary is reproducible at the artifact level and cannot silently
  change under the same workflow revision.
- The workflow temporarily forgoes raw-object hardening introduced after
  0.15.1. This is bounded by exact target-commit checks, immutable tag handling,
  and the requirement for a valid signature from the repository's workflow
  identity.
- Dependabot cannot advance this direct binary pin automatically; an upgrade
  requires updating the version, digest, decision rationale, and end-to-end
  evidence together.
