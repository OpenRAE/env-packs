# ADR 0047 — Pin one exact RAES version

- Status: Accepted
- Date: 2026-11-02
- Supersedes: [ADR 0043](0043-require-a-minimum-raes-version.md)

## Context

[ADR 0043](0043-require-a-minimum-raes-version.md) made `pyproject.toml`
declare a minimum RAES version (`raes>=<floor>`). The maintainer decided to pin
one exact RAES version. The maintainer plans to return to a minimum version
after RAES 11 ([issue 620](https://github.com/OpenRAE/env-packs/issues/620)).

## Decision

- `pyproject.toml` declares `raes==<version>`.
- `requirements/runtime.in` copies that declaration.
  `requirements/runtime.txt` and `uv.lock` lock the same version with hashes.
- A change to the RAES version changes all four files.
- RAES stays a mandatory dependency. Validation still flows only through RAES.

## Consequences

- A consumer installs the RAES version that CI tests.
- A new RAES release needs a new release of this package before consumers can
  use it.
