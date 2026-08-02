# ADR 0036 — Publish first-party content with env-packs

- Status: Accepted
- Date: 2026-08-02
- Supersedes: the content-location decisions in [ADR 0001](0001-repository-purpose-and-boundary.md)
  and [ADR 0035](0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md)
- Coordination: OpenRAE/env-packs issue 190

## Context

Separating the first-party infrastructure kits from their authoring contract
left a completed implementation without a published collection and made the
author experience depend on an unnecessary repository boundary. This repository
already carries the environment-pack contract, kit tooling, and major example
content. The first-party kits are part of that same author-facing product.

## Decision

This repository publishes the complete first-party infrastructure-kit collection
under `kits/` and major example packs under `packs/`. Each kit retains its own
identity and version. The kit catalog remains a deterministic projection over
ordinary releases; co-location does not add a runtime API, backend semantics, or
a second RAES authority.

Repository CI validates every checked-in kit independently, exercises meaningful
parameter variation, and composes a representative multi-kit environment. The
repository's immutable Git revision is the admitted source revision used by kit
materialization provenance.

Third-party and private catalogs remain free to publish their own packs and kits
in separate repositories using the same contracts. Co-locating the first-party
collection establishes no requirement that all ecosystem content live here.

## Consequences

- Authors obtain the tooling, the initial kit collection, and major examples
  from one repository.
- A kit implementation is not complete until its release is present and tested
  under `kits/`.
- The first-party collection cannot be stranded behind a separate unpublished
  catalog repository or PR.
- RAES continues to own scenario and module semantics; backends continue to own
  realization.
