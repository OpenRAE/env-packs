# Architecture Decision Records

Records of the significant, hard-to-reverse decisions for this repository. Each
ADR states the context, the decision, and its consequences. ADRs are immutable
once accepted; a later ADR supersedes an earlier one rather than editing it.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-repository-purpose-and-boundary.md) | Repository purpose and boundary | Purpose/boundary superseded by 0009 |
| [0002](0002-distribute-as-installable-package.md) | Distribute as an installable Python package bundling schemas and template | Accepted |
| [0003](0003-build-and-release-model.md) | Build and release model | Accepted |
| [0004](0004-sbom-and-supply-chain.md) | SBOM and supply-chain provenance | Accepted |
| [0005](0005-automatic-release-on-merge-to-main.md) | Automatic release on merge to main (amends 0003) | Superseded by 0006 |
| [0006](0006-conventional-commit-releases.md) | Conventional-commit-driven automatic releases (reusable blueprint) | Versioning superseded by 0007 |
| [0007](0007-changelog-driven-versioning.md) | Changelog-driven versioning (reusable blueprint) | Superseded by 0008 |
| [0008](0008-adopt-release-please.md) | Adopt release-please (reusable blueprint) | Accepted |
| [0009](0009-scenario-packs-subordinate-to-aces.md) | Scenario packs are strictly subordinate to ACES (zero extensions) | Accepted |
| [0010](0010-consume-aces-reusable-asset-trust-policy.md) | Consume ACES reusable-asset trust policy for pack provenance | Accepted |
| [0011](0011-require-pinned-aces-sdl-validation.md) | Require pinned ACES SDL validation for scenario packs | Accepted |
| [0012](0012-pack-content-identity-and-trust-boundary.md) | Pack content identity consumes ACES associated-artifact manifests | Accepted |
| [0013](0013-separate-consumer-static-validation-from-author-ci.md) | Separate consumer static validation from author CI | Accepted |
| [0014](0014-consume-aces-concept-authority.md) | Keep governed concept references in ACES concept-authority | Accepted |
| [0015](0015-attest-python-distribution-build-provenance.md) | Attest Python distribution build provenance | Accepted |
| [0016](0016-automate-dependency-updates.md) | Automate dependency updates and ship ACES bumps as releases | Accepted |
| [0017](0017-sign-release-tags-with-keyless-sigstore.md) | Sign release tags with keyless Sigstore | Accepted |
| [0018](0018-openssf-scorecard-posture.md) | OpenSSF Scorecard posture | Accepted |
| [0019](0019-preserve-history-in-dev-main-promotions.md) | Preserve history in dev-to-main promotions | Accepted |

```{toctree}
:hidden:
:maxdepth: 1
:glob:

0*
```
