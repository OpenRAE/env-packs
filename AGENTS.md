# Agent Instructions

This repository is the canonical home for the RAES environment-pack definition,
schemas, template, and authoring/validation tooling. It does not host actual
environment packs — those live in their own catalog repositories and consume this
package.

## Repository Boundaries

This repository is **subordinate to RAES core** (`raes` /
`OpenRAE/rae`) and exists to make authoring and shipping RAES scenarios
easier. It defines **zero extensions** to RAES semantics
(see [ADR 0021](docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md)).

- RAES core owns all scenario semantics — the SDL and its objectives,
  conditions, evidence, and participant/attacker behaviour. Where RAES owns a
  concept, consume it from RAES; never redefine or extend it here.
- This repository owns only the environment-pack layout and the
  authoring/validation/release tooling.
- Actual environment packs live in their own catalog repos, not here.
- Don't import downstream catalog names, paths, branch rules, labels, product
  assumptions, or private deployment vocabulary into the canonical docs.

## Verification

Before declaring repository work complete, run (in a venv with `pip install -e .`):

```sh
python -m unittest discover -s tests
raes-pack-validate --repo .
raes-pack-release check --all
python3 -m compileall src tests
```

## Commits & releases

- PR titles MUST be Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `test:`, `ci:`, `build:`); a required CI check enforces it.
- The type is the release decision: `feat:`→minor, `fix:`/`perf:`→patch,
  `feat!:`/`BREAKING CHANGE:`→major (pre-1.0 → minor); docs/chore/test/ci/
  refactor/build don't release.
- **Never hand-edit the version or `CHANGELOG.md`** — the version lives in
  `pyproject.toml` (`[project].version`) and both are owned by **release-please**,
  which maintains a `chore(main): release X.Y.Z` PR; merging it publishes.
- Squash-merge feature PRs. See
  `docs/decisions/adrs/0008-adopt-release-please.md`.
- Open the `dev` → `main` promotion PR with `make devmain`. Merge it with a
  **merge commit** — never squash or rebase it, or release-please loses the
  individual Conventional Commit subjects it reads to decide the version and
  build the changelog. See
  [ADR 0019](docs/decisions/adrs/0019-preserve-history-in-dev-main-promotions.md).
