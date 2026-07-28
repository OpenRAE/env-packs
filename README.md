# RAES Environment Packs

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/RAESystem/env-packs/badge)](https://scorecard.dev/viewer/?uri=github.com/RAESystem/env-packs)
[![Documentation](https://app.readthedocs.org/projects/env-packs/badge/?version=latest)](https://env-packs.readthedocs.io/en/latest/)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13833/badge)](https://www.bestpractices.dev/projects/13833)

The canonical, shared home for the **RAES environment-pack definition** and the
**authoring / validation tooling** that goes with it, published as an installable
Python package so catalogs (and others) consume one version-matched artifact
instead of vendoring the contract.

This repository does **not** host environment packs. Packs live in their own catalog
repositories and consume this contract.

## Install

```sh
pip install raes-env-packs
```

This provides the console tools plus the version-matched schemas and template:

- `raes-pack-validate` — validate pack content against the contract.
- `raes-pack-release` — boundary-split build, lint, release, and profile-smoke gate.
- `raes-new-pack` — scaffold a new pack from the bundled template.
- `raes-pack-issue-skeleton` — generate a pack work-issue skeleton.

Validate one pack by pointing the tools at its directory:

```sh
raes-pack-validate --pack ./environments/example-pack
raes-pack-release check --pack ./environments/example-pack
```

As a convenience, a directory containing only pack directories can be checked
in one command. Every direct child directory is treated as a pack candidate:

```sh
raes-pack-validate --packs-root ./environments
raes-pack-release check --packs-root ./environments
```

Consumers can validate one immutably staged pack in-process, without Git,
subprocesses, or pack-local code:

```python
from raes_env_packs import validate_pack

result = validate_pack(pack_root)
if not result.ok:
    reject(result.errors)
```

This checks the static ingest contract: pack identity, required provenance and
safety/review policy, an optional referenced compatibility manifest, and direct
SDL documents through RAES. Diagnostics contain bounded error codes and relative
locations, never source bodies or absolute paths. See
[Single-Pack Consumer Validation](docs/environment-packs.md#single-pack-consumer-validation).

## What's here

- **Definition**
  - [`docs/environment-packs.md`](docs/environment-packs.md) — what an environment pack is.
  - [Migration from the retired package identity](docs/raes-migration.md).
  - Layout contract + schemas + template ship as package data under
    [`src/raes_env_packs/resources/`](src/raes_env_packs/resources/)
    (`contract/pack-layout.md`, `schemas/`, `template/`).
  - [Architecture Decision Records](docs/decisions/adrs/) — purpose, packaging,
    build/release, SBOM.
- **Tools** — the package modules under
  [`src/raes_env_packs/`](src/raes_env_packs/), exposed as the console
  entry points above.

## Boundary

This repository is **subordinate to RAES core** (`raes`): it exists to make
authoring and shipping RAES scenarios easier, and defines **no extensions** to
RAES semantics
([ADR 0021](docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md)).

- **RAES core** owns the Scenario Definition Language (SDL) and all scenario
  semantics. Where RAES owns a concept, packs consume it from RAES.
- **This repository** owns how an environment pack is structured, authored,
  validated, and released — the layout and the tools that enforce it.
- **Downstream catalogs** hold the actual packs and any private runtime,
  delivery, or product integrations.

## Development

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

python -m unittest discover -s tests
```

Releases are managed by **release-please** — merge-driven, nothing hand-run
(see [ADR 0008](docs/decisions/adrs/0008-adopt-release-please.md)). The version
lives in `pyproject.toml` (`[project].version`) and is bumped by release-please;
`__version__` derives from it. The **Conventional Commit PR title** decides the
bump:

| PR title | Bump |
| --- | --- |
| `feat!:` / `BREAKING CHANGE:` | major (pre-1.0: minor) |
| `feat:` | minor |
| `fix:` / `perf:` | patch |
| `docs:` `chore:` `refactor:` `test:` `ci:` `build:` | no release |

You never edit `CHANGELOG.md` — release-please owns it. As feature PRs land on
`main` (via `dev`), release-please keeps a `chore(main): release X.Y.Z` PR up to
date with the version bump + changelog. **Merge that PR to release:** it tags
`vX.Y.Z`, builds the sdist + wheel, generates a CycloneDX SBOM, publishes to PyPI
via OIDC, and cuts the GitHub Release. (The release PR is opened by the CI token,
so its checks don't auto-run — admin-merge it.) A CI check enforces conventional
PR titles and bans agent-branding prefixes.

Licensed under the MIT License (see [`LICENSE`](LICENSE)).
