# Agent Instructions

This repository is the canonical home for the RAES environment-pack definition,
schemas, template, authoring/validation tooling, first-party infrastructure kits,
and major example packs. Published kits live under `kits/`; example packs live
under `packs/`.

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
- This repository publishes first-party reusable kit releases and major example packs.
- Runtime backends consume hosted packs; they do not own the portable scenario.
- Third-party environment packs may live in their own repositories and consume
  this package.
- Do not import downstream catalog names, paths, branch rules, labels, product
  assumptions, or private deployment vocabulary into the canonical docs.

## Documentation

Use the existing `documentation` skill when your agent exposes it.
Otherwise, follow the [documentation style guide](docs/development/documentation-style-guide.md) and its tool-only commands.
Choose a Diataxis purpose, verify claims against code, and preserve technical meaning and literal commands.
Record source revisions and check results in the pull request.

Run writing checks on explicit changed Markdown paths, including hidden directories and content assets.
Preserve exact evidence, legal text, and historical records through narrow, explained exclusions.
Keep `docs/public/` as the sole published source root.
Keep Python instructions until the Go instruction migration and cutover land.

## Verification

Before declaring repository work complete, run (in a venv with `pip install -e .`):

```sh
python -m unittest discover -s tests
raes-pack-validate --repo .
raes-pack-release check --all
raes-pack-validate --packs-root packs
raes-pack-release check --packs-root packs
python3 -m compileall src tests
```

## Commits & releases

- PR titles MUST be Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `test:`, `ci:`, `build:`); a required CI check enforces it.
- The type is the release decision: `feat:`→minor, `fix:`/`perf:`→patch,
  `feat!:`/`BREAKING CHANGE:`→major; docs/chore/test/ci/refactor/build do not
  release.
- **Never hand-edit the version or `CHANGELOG.md`** — the version lives in
  `pyproject.toml` (`[project].version`) and **release-please** owns both.
  It maintains a `chore(main): release X.Y.Z` PR; merging it publishes.
- **Never hand-edit a pack version.** Every pack under `packs/` carries the
  package version. The release workflow writes it and refreshes the pack
  digests (ADR 0045).
- Squash-merge feature PRs. See
  `docs/decisions/adrs/0008-adopt-release-please.md`.
- Open the `dev` → `main` promotion PR with `make devmain`. Merge it with a
  **merge commit** — never squash or rebase it. Otherwise, release-please loses
  the individual Conventional Commit subjects that determine the version and changelog. See
  [ADR 0019](docs/decisions/adrs/0019-preserve-history-in-dev-main-promotions.md).
