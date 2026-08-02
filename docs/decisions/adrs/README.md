# Architecture Decision Records

Records of the significant, hard-to-reverse decisions for this repository. Each
ADR states the context, the decision, and its consequences. ADRs are immutable
once accepted; a later ADR supersedes an earlier one rather than editing it.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-repository-purpose-and-boundary.md) | Repository purpose and boundary | Purpose/boundary superseded by 0009 and 0036 |
| [0002](0002-distribute-as-installable-package.md) | Distribute as an installable Python package bundling schemas and template | Accepted |
| [0003](0003-build-and-release-model.md) | Build and release model | Accepted |
| [0004](0004-sbom-and-supply-chain.md) | SBOM and supply-chain provenance | Accepted |
| [0005](0005-automatic-release-on-merge-to-main.md) | Automatic release on merge to main (amends 0003) | Superseded by 0006 |
| [0006](0006-conventional-commit-releases.md) | Conventional-commit-driven automatic releases (reusable blueprint) | Versioning superseded by 0007 |
| [0007](0007-changelog-driven-versioning.md) | Changelog-driven versioning (reusable blueprint) | Superseded by 0008 |
| [0008](0008-adopt-release-please.md) | Adopt release-please (reusable blueprint) | Accepted |
| [0009](0009-scenario-packs-subordinate-to-aces.md) | Scenario packs are strictly subordinate to ACES (zero extensions) | No-hosting clause superseded by 0036; semantic boundary accepted |
| [0010](0010-consume-aces-reusable-asset-trust-policy.md) | Consume ACES reusable-asset trust policy for pack provenance | Accepted |
| [0011](0011-require-pinned-aces-sdl-validation.md) | Require pinned ACES SDL validation for scenario packs | Accepted |
| [0012](0012-pack-content-identity-and-trust-boundary.md) | Pack content identity consumes RAES associated-artifact manifests | Accepted |
| [0013](0013-separate-consumer-static-validation-from-author-ci.md) | Separate consumer static validation from author CI | Accepted |
| [0014](0014-consume-aces-concept-authority.md) | Keep governed concept references in ACES concept-authority | Accepted |
| [0015](0015-attest-python-distribution-build-provenance.md) | Attest Python distribution build provenance | Accepted |
| [0016](0016-automate-dependency-updates.md) | Automate dependency updates and ship RAES bumps as releases | Auto-merge superseded by 0020 |
| [0017](0017-sign-release-tags-with-keyless-sigstore.md) | Sign release tags with keyless Sigstore | Accepted |
| [0018](0018-openssf-scorecard-posture.md) | OpenSSF Scorecard posture | Accepted |
| [0019](0019-preserve-history-in-dev-main-promotions.md) | Preserve history in dev-to-main promotions | Accepted |
| [0020](0020-no-auto-merge.md) | No auto-merge; a human merges every pull request | Accepted |
| [0021](0021-adopt-raes-environment-pack-identity.md) | Adopt the RAES environment-pack identity as a hard cut | Upstream pin/spellings superseded by 0022 |
| [0022](0022-adopt-raes-2-upstream-contract.md) | Adopt the RAES 2 upstream contract | Accepted |
| [0023](0023-recover-interrupted-signed-releases.md) | Recover interrupted signed releases | Accepted |
| [0024](0024-pin-gitsign-pre-regression-release.md) | Pin the pre-regression gitsign release | Accepted |
| [0025](0025-recover-historical-tags-with-verified-handoff.md) | Recover historical tags with a verified object handoff | Accepted |
| [0026](0026-separate-historical-source-from-release-tooling.md) | Separate historical source from release tooling | Accepted |
| [0027](0027-publish-only-the-active-pypi-distribution.md) | Publish only the active PyPI distribution | Accepted |
| [0028](0028-project-raes-artifact-satisfaction-into-publication.md) | Project RAES artifact satisfaction into pack publication | Accepted |
| [0029](0029-parallel-pr-feedback-with-a-complete-merge-gate.md) | Parallel PR feedback with a complete merge gate | Accepted |
| [0030](0030-separate-public-and-developer-documentation.md) | Separate public and developer documentation | Accepted |
| [0031](0031-compose-beginner-safe-pack-checks-from-existing-authorities.md) | Compose beginner-safe pack checks from existing authorities | Accepted |
| [0032](0032-derive-catalog-projection-from-existing-authorities.md) | Derive one catalog projection from existing authorities | Accepted |
| [0033](0033-resolve-pack-artifacts-through-one-bounded-open.md) | Resolve pack artifacts through one bounded open | Accepted |
| [0034](0034-compose-progressive-scaffolding-from-pack-and-raes-authorities.md) | Compose progressive scaffolding from pack and RAES authorities | Accepted |
| [0035](0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md) | Compose catalog kits through RAES and transactional pack projections | Content location superseded by 0036 |
| [0036](0036-publish-first-party-content-with-env-packs.md) | Publish first-party content with env-packs | Accepted |

```{toctree}
:hidden:
:maxdepth: 1
:glob:

0*
```
