# Security

Please report security issues through GitHub's private vulnerability reporting
for this repository, or contact the maintainers directly. Don't open a public
issue for a suspected vulnerability.

Scenario packs can contain synthetic credentials, flags, service defaults, and
participant-facing artifacts. Those are training content, not production secrets.
Never commit real credentials, customer data, private keys, or operator tokens
to this repository — keep local development secrets in `.env`, which is
gitignored.

## Verifying release tag signatures

Release tags (`vX.Y.Z`) are signed with keyless [Sigstore](https://www.sigstore.dev/)
via [gitsign](https://github.com/sigstore/gitsign) — the release workflow's
short-lived GitHub Actions OIDC identity, no stored signing key (ADR 0017).
Because the signature is Sigstore keyless rather than GPG, GitHub does not render
its `Verified` badge; the identity-bound `gitsign verify-tag` check below — not
the web UI — is the authentication signal.

Install gitsign **0.15.0 or newer** (earlier versions are affected by
[CVE-2026-44310](https://github.com/advisories/GHSA-7c37-gx6w-8vc5), a
verification bypass) per the
[upstream instructions](https://github.com/sigstore/gitsign#installation), then:

```sh
git fetch --tags origin
gitsign verify-tag \
  --certificate-identity=https://github.com/RAESystem/env-packs/.github/workflows/release-please.yml@refs/heads/main \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  vX.Y.Z
```

**Tags signed before the repository moved to `RAESystem/env-packs`** carry the
signer identity of its previous path. The signing certificate records the
repository the workflow ran in at the time, and that is not rewritten by a
transfer, so verifying an older tag needs the older identity:

```sh
--certificate-identity=https://github.com/Brad-Edwards/aces-scenario-packs/.github/workflows/release-please.yml@refs/heads/main
```

Both identities are legitimate for their respective release ranges. Neither is a
fallback for the other: verification must assert one exact identity, so pick the
one matching the tag's date rather than trying both to see which passes.

A pass reports a valid Git signature, a Rekor transparency-log entry, and the
expected certificate identity. Verify against the exact identity above, not
merely any certificate Sigstore accepts; `git verify-tag` alone does not enforce
the signer identity. The release workflow runs the same check before publishing.

Tag provenance is one of several independent supply-chain records: build
artifacts (wheel/sdist) additionally carry SLSA build-provenance attestations
verifiable with `gh attestation verify` (ADR 0015), a CycloneDX SBOM (ADR 0004),
and PyPI publication attestations. None substitutes for another.
