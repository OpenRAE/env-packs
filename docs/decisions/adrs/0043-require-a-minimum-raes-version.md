# ADR 0043 — Require a minimum RAES version

- Status: Accepted
- Date: 2026-10-29
- Supersedes: the exact-pin rule of ADR 0011 (pinned RAES SDL validation) and
  the exact-pin consequence of
  [ADR 0021](0021-adopt-raes-environment-pack-identity.md)
- Coordination: OpenRAE/env-packs issue 504

## Context

`pyproject.toml` declared one exact `raes==` version (ADR 0011). The
maintainer decided to stop pinning a specific patch level: when a version and
its successors are valid, the package allows them.

## Decision

- `pyproject.toml` declares `raes>=<floor>`. The floor is the oldest RAES
  release that supplies every RAES API this package uses.
- `requirements/runtime.in` copies that declaration.
  `requirements/runtime.txt` and `uv.lock` stay exact and hash-locked. They
  record the RAES version that CI tests.
- A change that needs a newer RAES API raises the floor.
- RAES stays a mandatory dependency. Validation still flows only through RAES.

## Consequences

- A consumer can install a newer RAES release without a new release of this
  package.
- CI tests the locked RAES version. A RAES release above the lock is not tested
  until the lock moves.
