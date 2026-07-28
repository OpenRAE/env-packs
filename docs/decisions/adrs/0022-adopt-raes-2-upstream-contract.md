# ADR 0022 — Adopt the RAES 2 upstream contract

- Status: Accepted
- Date: 2026-07-28
- Supersedes: the upstream dependency pin and RAES-owned identifier spellings
  selected by [ADR 0021](0021-adopt-raes-environment-pack-identity.md)

## Context

ADR 0021 completed the local environment-pack identity cut against RAES 1.1.0.
RAES 2.0.0 is now the required upstream release and changes three identifiers
owned by RAES: its schema namespace, module lockfile, and resolver cache path.
Keeping the earlier spellings while claiming RAES 2 compatibility would expose
a mixed contract to pack authors and consumers.

## Decision

The maintained distribution exactly pins `raes==2.0.0`. Current pack contracts,
schemas, templates, documentation, validation behavior, and tests consume the
RAES 2 spellings together:

- governed schema identifiers use `https://raes.dev/schemas/`;
- module dependency locks use `raes.lock.json`; and
- the SDL resolver cache is `sdl/.raes/module-cache/`.

The cache remains excluded from environment-pack content identity only at that
exact SDL-root path. A same-named directory elsewhere remains ordinary pack
content. Consumer validation continues to deny imports and therefore must not
create the resolver cache.

This repository does not define aliases for the earlier spellings or copy any
RAES-owned schema or resolver logic. Public SDL imports remain from `raes`, and
governed contract imports remain from `raes_contracts`.

## Consequences

- A pack authored for the RAES 2 resolver cannot be silently interpreted using
  the RAES 1 lockfile or cache identity.
- Pack-owned schema versions stay at their newly minted environment-pack
  versions; their canonical URI host is corrected before release.
- Advancing the exact RAES pin remains a reviewed compatibility change governed
  by ADR 0011 and ADR 0016.
