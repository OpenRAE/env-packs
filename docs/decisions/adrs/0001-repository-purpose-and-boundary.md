# ADR 0001 — Repository purpose and boundary

- Status: Accepted
- Date: 2026-07-05

## Context

The ACES ecosystem needs one canonical, shared home for the scenario-pack
**definition** (what a pack is, its layout, its schemas) and the
**authoring/validation tooling** that enforces it. Historically this material
lived inside a content repository alongside the actual
packs, so every consumer that wanted the contract or the tools had to vendor or
copy them, and the definition drifted per catalog.

## Decision

This repository is the single source of truth for the scenario-pack definition
and tooling. It:

- **owns** the pack definition (`docs/scenario-packs.md`), the layout contract
  (`scenarios/README.md` content), the schemas (provenance, pack-compatibility),
  the template pack, the shared oracle model, and the authoring/validation
  tools;
- **does not host actual scenario packs** — those live in their own catalog
  repositories and consume this contract;
- **does not define SDL semantics** — the Scenario Definition Language is owned
  by ACES core (`Brad-Edwards/aces`); a pack references and carries SDL, it does
  not redefine it.

## Consequences

- Catalog repositories depend on this repository as a versioned artifact rather
  than duplicating its content (see ADR 0002).
- Changes to the definition/tooling happen here and are released; consumers pin a
  version and upgrade deliberately.
- Anything that is not the definition or its tooling — packs, private runtime,
  delivery, or product integrations — is out of scope for this repository.
