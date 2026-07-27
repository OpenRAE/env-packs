# ADR 0017 — Sign release tags with keyless Sigstore

- Status: Accepted
- Date: 2026-07-17
- Amends: [ADR 0008](0008-adopt-release-please.md)
- Complements: [ADR 0015](0015-attest-python-distribution-build-provenance.md)

## Context

Release Please currently creates the Git tag and GitHub Release through the
GitHub API. The resulting lightweight tag is not signed, so a consumer cannot
authenticate the source ref independently of GitHub. Issue 59 originally named
python-semantic-release, but ADR 0008 has since replaced it with Release Please;
the requirement is still to make new release tags signed and verifiable.

Tag provenance is distinct from the existing release records. The CycloneDX
SBOM inventories components, GitHub's build-provenance attestation authenticates
the wheel and sdist built by the workflow, and PyPI supplies publication
attestations. None authenticates the Git tag object that selects the source
revision.

GPG would make GitHub display a `Verified` badge, but automation would need a
long-lived private key and passphrase in repository secrets, plus key ownership,
rotation, revocation, and recovery procedures. The release workflow already has
a short-lived GitHub Actions OIDC identity for trusted publishing and artifact
attestation, so adding a second long-lived signing identity would move against
the repository's existing supply-chain model.

### Release Please constraints (why this workflow is custom)

Release Please has no native tag signing and no clean handoff for external
tagging, so a signed tag cannot be produced without taking tag creation away
from it:

- It has no signing option of any kind (open, unaddressed feature request
  [release-please-action#1171](https://github.com/googleapis/release-please-action/issues/1171)),
  and it creates the tag through the GitHub REST API — so a local signer such as
  `gitsign` (which hooks `git tag -s`) cannot intercept it. A signed tag
  therefore requires creating the tag locally, outside Release Please.
- `skip-github-release: true` is the only lever that stops Release Please from
  creating the unsigned tag; it suppresses both the tag and the GitHub Release
  (there is no tag-only mode —
  [release-please-action#1034](https://github.com/googleapis/release-please-action/issues/1034)),
  and it leaves the release-PR outputs (`release_created`, `tag_name`) unset, so
  the downstream job cannot rely on them.
- Under `skip-github-release`, Release Please does not complete its own
  `autorelease: pending` → `autorelease: tagged` label transition, and it aborts
  a later run with "untagged, merged release PRs outstanding"
  ([release-please#1561](https://github.com/googleapis/release-please/issues/1561),
  still current — closed only by a documentation change). There is no documented
  handoff for external tagging.

The design below therefore takes over only tag creation — Release Please keeps
owning the version, changelog, and release PR — authorizes on the merged PR's
`autorelease: pending` label instead of the unset outputs, and completes Release
Please's own label transition so its state machine stays consistent. This is
unsupported territory in Release Please; the end-to-end path is validated on the
first real release.

## Decision

Use **keyless Sigstore signing with gitsign** for release tags.

Release Please remains the only version, changelog, and release-PR authority.
It runs in PR-only mode (`skip-github-release: true`, declared once in the
schema-backed `release-please-config.json`) so it never creates the unsigned tag
or GitHub Release. The canonical
`.github/workflows/release-please.yml` owns the remaining release boundary; no
parallel release workflow or second version calculation is introduced.

Publication authorization is bound to an *authenticated* Release Please signal,
not to a raw version change. Only Release Please applies the `autorelease: pending`
label to its own release PRs, so the workflow resolves the pull request whose
merge produced the push and treats that label's presence as the release
authorization. A collaborator who can merge ordinary PRs but not the admin-gated
release act cannot forge the label, so a feature PR that merely edits
`[project].version` cannot trigger a signed tag or a PyPI publish. Because
`skip-github-release` leaves Release Please's own state machine expecting the
release to be tagged, the workflow — after creating the signed tag — flips the
merged PR from `autorelease: pending` to `autorelease: tagged`, or Release Please
aborts its next run with "untagged, merged release PRs outstanding"
([release-please#1561](https://github.com/googleapis/release-please/issues/1561)).

With authorization established, the version/manifest parsing below is a
consistency check, never the authorization by itself. Before treating the push as
releasable, the workflow must also validate all of the following:

- the previous and current revisions are the exact revisions from the trusted
  `push` event, and the current revision is `github.sha` on `main`;
- `[project].version` in `pyproject.toml` is a strict stable SemVer and changed
  across that push;
- `.release-please-manifest.json` has exactly the root package entry (`.`) and
  its version equals `[project].version`; and
- the expected tag is exactly `v<version>`, preserving Release Please's existing
  tag contract.

TOML and JSON are parsed with their real parsers, never sourced or scraped with
shell text matching. Event revisions and derived values cross into shell only
through environment bindings after shape validation; no value is evaluated as
shell code. Release runs are serialized with `cancel-in-progress: false`, so two
workflow runs cannot race to create or publish the same tag.

The release job creates one signed, annotated tag at the exact current commit
with gitsign's GitHub Actions token provider. It immediately verifies both the
signature and the signer policy before any GitHub Release creation, PyPI
publication, or artifact upload. The accepted identity is:

```text
certificate identity: https://github.com/RAESystem/env-packs/.github/workflows/release-please.yml@refs/heads/main
OIDC issuer:          https://token.actions.githubusercontent.com
```

The identity is bound to the repository's path at signing time. A repository
transfer therefore changes it: the OIDC token's workflow ref is issued for the
repository's current location, and GitHub's redirect for a moved repository does
not extend to certificate-identity matching. When this repository moved to
`RAESystem/env-packs`, a stale value would have failed `gitsign verify-tag`
closed and blocked every subsequent release (#142).

Tags signed before that move remain valid under the previous identity:

```text
certificate identity: https://github.com/Brad-Edwards/aces-scenario-packs/.github/workflows/release-please.yml@refs/heads/main
```

Both are legitimate for their own release ranges, and neither is a fallback for
the other -- verification asserts one exact identity, so the verifier picks the
one matching the tag rather than trying both until one passes. Any future
transfer must update the workflow, this ADR, `SECURITY.md`, and
`tests/test_release_workflow_tag_signing.py` together.

An existing tag during a rerun is acceptable only when it dereferences to the
same release commit and passes that exact identity-and-issuer policy. Any other
existing tag fails closed. The workflow never deletes, force-updates, or
temporarily replaces a release tag. Previously published unsigned tags are
historical and are not rewritten; enforcement starts with the first release
after this decision.

The GitHub Release must consume the pre-existing remote tag (`gh release create
--verify-tag`) rather than implicitly creating one. Release notes continue to
come from the matching Release Please-owned `CHANGELOG.md` section; the workflow
must not regenerate a competing changelog or recompute the version from commits.
Notes are passed to `gh` through a file or standard input, never interpolated
into a command line.

Use least-privilege job boundaries:

- the Release Please PR job has `contents: write` and `pull-requests: write`, but
  no OIDC or attestation permission;
- the read-only detection job has `contents: read` and `pull-requests: read` to
  inspect the merged PR's labels and the version transition; and
- the protected `pypi` release job has the `contents: write`, `id-token: write`,
  and `attestations: write` permissions needed to sign, attest, publish, and
  attach the release artifacts, plus `pull-requests: write` solely to relabel the
  release PR `autorelease: tagged`.

No signing key, certificate, passphrase, or new long-lived token is stored.
Git checkout must not persist credentials; GitHub authentication is exposed to
the minimum push/release commands through the existing masked `GH_TOKEN`
environment binding, never embedded in a remote URL or process argument. The
OIDC token is obtained by gitsign's native `github-actions` provider and is never
captured, printed, or passed through workflow outputs.

The gitsign installer/action is SHA-pinned like all third-party actions, and the
gitsign release is explicitly pinned to a reviewed, non-vulnerable version. In
particular, versions before 0.15.0 are forbidden because of
[CVE-2026-44310](https://github.com/advisories/GHSA-7c37-gx6w-8vc5); the workflow
also enforces that floor at runtime and fails closed below it. Verification uses
`gitsign verify-tag` (the tag-scoped command; `gitsign verify` targets a commit)
with both expected policy arguments; `git verify-tag` alone is insufficient
because it does not enforce the expected certificate identity.

The repository's existing `unittest` + PyYAML workflow-contract tests guard the
static invariants: PR-only Release Please mode, pinned signer installation,
least-privilege permissions, version/manifest validation, exact tag target,
sign-before-publish ordering, identity-bound verification, and refusal to delete
or force-update tags. This is a workflow contract, not a package schema or a new
runtime validation framework. Final acceptance still requires one real release
whose tag passes the documented command.

## Verification contract

Consumers fetch the tag and verify the Sigstore signature against the exact
workflow identity, not merely against any certificate accepted by Sigstore.
Install a supported gitsign version (0.15.0 or newer) using the
[upstream instructions](https://github.com/sigstore/gitsign#installation), then
run:

```sh
git fetch --tags origin
gitsign verify-tag \
  --certificate-identity=https://github.com/RAESystem/env-packs/.github/workflows/release-please.yml@refs/heads/main \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  vX.Y.Z
```

For a tag cut before the repository moved, substitute the previous identity
recorded above.

A successful result must report a valid Git signature, Rekor entry, and
certificate claims. The release workflow performs the same policy check before
publication.

## Consequences

- New release tags authenticate the exact workflow, repository, branch, and
  target commit without a stored signing key.
- Signing and verification depend on GitHub OIDC and the public Sigstore Fulcio
  and Rekor services; an outage blocks a release rather than producing an
  unsigned one.
- The public transparency record includes public repository/workflow/ref
  identity. This repository is public, so that disclosure adds no private
  metadata.
- GitHub does not currently render gitsign signatures with its `Verified` badge.
  The documented identity-bound gitsign check, not the web badge, is the
  acceptance signal.
- Tag signing, build provenance, PyPI publication attestations, the SBOM, and
  scenario-pack provenance remain separate concepts with separate verification
  commands and trust boundaries.
