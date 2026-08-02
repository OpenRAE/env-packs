# ADR 0036 — Host first-party environment packs

- Status: Accepted
- Date: 2026-08-02
- Supersedes: the no-hosted-packs boundary in
  [ADR 0001](0001-repository-purpose-and-boundary.md) and
  [ADR 0009](0009-scenario-packs-subordinate-to-aces.md)

## Context

The original repository charter separated the environment-pack package and
tooling from every actual pack. That separation made the pack contract reusable,
but it also left first-party scenarios without a natural editable authority and
encouraged a consuming backend to appear to own scenario content.

TechVault exposed the problem directly. APTL can realize the scenario, but a
backend is not the owner of a portable RAES scenario or its distributable
content. Moving the content into another catalog solely to preserve the original
charter would add indirection without creating a better owner.

The semantic boundary established by ADR 0009 remains correct: RAES owns SDL
meaning and this repository must not extend it. Hosting a scenario expressed in
RAES is distinct from inventing scenario semantics.

## Decision

This repository may host selected first-party environment packs under `packs/`
alongside the installable pack contract and tooling.

1. A hosted pack is an ordinary consumer of the published environment-pack
   contract. It has `pack.yaml`, RAES SDL, provenance, content identity, and the
   same validation/release gates expected of a pack in an external catalog.
2. RAES remains the sole semantic authority. Hosted SDL is scenario data; local
   metadata, validation, and tests may preserve and cross-check it but may not
   redefine objectives, conditions, evidence, participant behavior, or other
   RAES concepts.
3. A runtime backend consumes a hosted pack and does not acquire ownership of
   it. Backend-specific source paths, secret state, and product lifecycle remain
   outside the pack. Portable RAES runtime declarations already present in the
   SDL remain authoritative scenario input.
4. `packs/<name>` is the editable authority for a hosted pack. A backend or
   catalog may cache or distribute released bytes, but must not maintain a
   competing editable copy.
5. The required CI and local completion gates validate both the package/tooling
   suite and every direct child of `packs/` explicitly. A pack cannot be hidden
   by the legacy `environments/` default.
6. Golden-range claims remain evidence-based. A hosted pack may be `draft` or
   `built`; hosting it does not imply a golden reference build.

## Consequences

- TechVault lives at `packs/techvault` and is named `techvault`; APTL consumes it
  as a backend.
- External catalog repositories remain supported. The `environments/` catalog
  convention and the package's authoring/validation APIs do not change.
- Repository docs, contributor instructions, Ground Control guidance, and CI no
  longer state that actual packs are forbidden here.
- The subordinate-to-RAES and zero-extension decisions in ADR 0009 remain in
  force. Only its carried-forward no-hosted-packs clause is superseded.
- Golden TechVault work is tracked separately and cannot block shipping the
  non-golden pack.
