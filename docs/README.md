# Developer documentation

Maintainer records for this repository. These live in the repository and render
on GitHub, but they are **not** part of the published documentation site — only
`docs/public/` is (see
[ADR 0030](decisions/adrs/0030-separate-public-and-developer-documentation.md)).
User-facing documentation is under [`public/`](public/index.md).

## Decisions

- [Architecture Decision Records](decisions/adrs/README.md) — the significant,
  hard-to-reverse decisions, newest last. Accepted ADRs are immutable; a later
  ADR supersedes an earlier one.

## Repository mechanics

- [Continuous integration](development/ci.md) — the PR check surface, the
  `verify` merge gate, and how to reproduce each check locally.
- [TechVault Kali capture and shell-access preflight](development/techvault-kali-capture-shell-preflight.md)
  — SDL authoring, runtime realization, evidence, and capability-handling
  guardrails for issue #282.
- [TechVault Shuffle runtime-contract preflight](development/techvault-shuffle-runtime-contract-preflight.md)
  — application/datastore, trust, secret, readiness, and realization guardrails
  for issue #281.
- [TechVault Shuffle Orborus offline-runtime preflight](development/techvault-shuffle-orborus-offline-runtime-preflight.md)
  — Docker control-authority, offline child-image, readiness, and realization
  guardrails for issue #285.
- [Migration scrub policy](development/scrub-policy.md) — how to adapt material
  from another source into this repository without leaking private vocabulary.
- [Documentation style guide](development/documentation-style-guide.md) — how the
  public docs are written, so a change reads like the rest.

## Manual integration walkthroughs

- [Infrastructure kits](development/kits-integration-runbook.md) — compose a
  realistic five-kit pack, then update, replace, remove, and revalidate it.
- [Progressive wizard](development/wizard-integration-runbook.md) — exercise
  starter routes and machine-readable replay through the shipped commands.

## Contributing

Setup, tests, and the submission path are in
[`CONTRIBUTING.md`](../CONTRIBUTING.md). The release model — release-please owns
the version and `CHANGELOG.md` — is summarized there and decided in
[ADR 0008](decisions/adrs/0008-adopt-release-please.md).
