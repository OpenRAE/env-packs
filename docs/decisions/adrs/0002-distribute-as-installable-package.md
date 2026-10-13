# ADR 0002 — Distribute as an installable Python package bundling schemas and template

- Status: Accepted
- Date: 2026-07-05

## Context

Per ADR 0001, catalog repositories and other consumers must
consume the scenario-pack definition and tooling cleanly. The tools were written
for a monorepo layout: they resolve the schemas, the `_template`, the `_oracle`
model, and the contract version relative to their own location on disk
(`scenarios/…` under the repository root). That only works when the tools run
from inside a checkout that also contains the schemas and packs — it is not
consumable by an external project.

## Decision

Publish a single installable Python package, **`aces-scenario-packs`**, that
bundles both the tools and the canonical data:

- **Package layout** is `src/`-based: `src/aces_scenario_packs/` holds the tool
  modules; the schemas, the template pack, the shared oracle model, and the
  contract version are shipped as **package data** under the package.
- **Canonical resources** (schemas, template, oracle model, contract version)
  are loaded from the installed package via `importlib.resources`, never from the
  consumer's working tree.
- **The catalog under validation** (the consumer's `scenarios/<pack>/` tree) is
  supplied at runtime via an explicit root argument (default: the current
  directory). Canonical-resource resolution and catalog resolution are separate
  concerns.
- The package exposes **console entry points** (see ADR 0003) so a consumer runs
  `aces-pack-validate`, `aces-pack-release`, `aces-new-pack`, and
  `aces-pack-issue-skeleton` after `pip install`.

A single package (rather than split tool/schema packages) is chosen for consumer
simplicity: one dependency provides both the validators and the schemas they
enforce, guaranteeing they are version-matched.

## Consequences

- A consumer does `pip install aces-scenario-packs` and gets the tools plus the
  version-matched schemas and template; nothing is vendored.
- The tools are refactored so canonical-resource paths come from package data and
  the pack-catalog root is a parameter. Tests exercise the package-resource model
  against synthetic temporary catalogs.
- The schema/contract **content version** (the pack contract version and digest)
  is independent of the **package version** (see ADR 0003); the package declares
  which contract version it ships.
