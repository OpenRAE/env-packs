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

- [Owlbear protected-target design](development/owlbear-protected-target-design.md)
  — source-backed input requirements, typed runtime variation, and trust boundaries.

- [Owlbear protected-target preflight](development/owlbear-protected-target-preflight.md)
  — reusable target, runtime/artifact boundaries, composition, and security
  guardrails for issue #540.
- [TechVault case management removal preflight](development/techvault-case-management-removal-preflight.md)
  — complete service retirement, archive preservation, and catalog/distribution
  guardrails for issue #536.
- [TechVault case management removal design](development/techvault-case-management-removal-design.md)
  — removed declarations, archive rebuild, data flow, and security controls for
  issue #536.
- [Dependent-declaration variation preflight](development/dependent-declaration-variation-preflight.md)
  — released RAES dependency, validation, and publication guardrails for issue #526.
- [RAES 10 dependency design](development/raes-10-dependency-design.md)
  — dependency floor, exception contract, data flow, and security controls for issue #526.
- [Experiment artifact set design](development/experiment-artifact-set-design.md)
  — components, failure codes, security controls, and data flow for issue #504.
- [Experiment artifact set preflight](development/experiment-artifact-set-preflight.md)
  — RAES experiment validation, family treatments, safe references, release and
  installed-artifact guardrails for issue #504.
- [AI Escape Lab preflight](development/ai-escape-lab-preflight.md) — portable
  campaign, GCP reference deployment, seat containment, model access, and proof
  guardrails for issue #422.
- [Continuous integration](development/ci.md) — the PR check surface, the
  `verify` merge gate, and how to reproduce each check locally.
- [Pack-aware MCP authoring preflight](development/pack-authoring-mcp-preflight.md)
  — shared contracts, proposal approval, static safety, and RAES delegation
  guardrails for issue #192.
- [Advanced kit evaluation preflight](development/advanced-kit-evaluation-preflight.md)
  — evidence requirements, carrier boundaries, and existing validation/security
  guardrails for issue #224.
- [Advanced reusable-content evaluation](development/advanced-kit-evaluation.md)
  — candidate ranking, source evidence, carrier decisions and admission lessons.
- [Defensive-tooling composition preflight](development/defensive-tooling-composition-preflight.md)
  — pack-root relationship, lifecycle ordering, and static-evidence guardrails
  for issue #378.
- [Multi-node kit topology and seed preflight](development/multi-node-kit-topology-seed-preflight.md)
  — RAES topology, seed-value, immutable-release, and validation guardrails for
  issue #416.
- [Bundled kit distribution](development/bundled-kit-distribution.md) — installed
  source selection, data flows, and integrity checks.
- [Released kit artifact preflight](development/released-kit-artifact-preflight.md)
  — package resources, per-kit identity, installed-consumer evidence, and release
  guardrails for issue #415.
- [Two-audience delivery-bundle preflight](development/two-audience-bundles-preflight.md)
  — bundle/release view separation, exposure checks, and existing-contract
  guardrails for issue #379.
- [TechVault Kali capture and shell-access preflight](development/techvault-kali-capture-shell-preflight.md)
  — SDL authoring, runtime realization, evidence, and capability-handling
  guardrails for issue #282.
- [TechVault MISP runtime-contract preflight](development/techvault-misp-runtime-contract-preflight.md)
  — MISP, MariaDB, Redis, trust, readiness, and backend-realization ownership
  for issue #280.
- [TechVault integration endpoint reconciliation](development/techvault-integration-endpoint-preflight.md)
  — retired proxy classification, HTTPS outcomes, and remaining live evidence
  for issue #294.
- [TechVault Shuffle runtime-contract preflight](development/techvault-shuffle-runtime-contract-preflight.md)
  — application/datastore, trust, secret, readiness, and realization guardrails
  for issue #281.
- [TechVault Shuffle Orborus offline-runtime preflight](development/techvault-shuffle-orborus-offline-runtime-preflight.md)
  — portable Orborus control/authority declarations and LilRAE realization
  ownership for issue #285.
- [TechVault Orborus self-identity binding preflight](development/techvault-orborus-self-identity-preflight.md)
  — why native holder identities stay outside portable pack content for issue
  #331.
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
