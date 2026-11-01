# Agent instructions

This repository is the canonical home of the RAES environment-pack definition,
the schemas, and the template. It also holds the authoring and validation
tools, the first-party infrastructure kits, and the major example packs. The
published kits are in `kits/`, and the example packs are in `packs/`.

## Repository boundaries

This repository is **subordinate to RAES core** (`raes` / `OpenRAE/rae`). Its
purpose is to make the authoring and shipping of RAES scenarios easier. It
defines **zero extensions** to RAES semantics (see
[ADR 0021](docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md)).

- RAES core owns all scenario semantics: the SDL and its objectives,
  conditions, evidence, and participant and attacker behavior. When RAES owns
  a concept, use it from RAES. Do not define it again here, and do not extend
  it.
- This repository owns only the environment-pack layout and the authoring,
  validation, and release tools.
- This repository publishes the first-party reusable kit releases and the
  major example packs.
- Runtime backends use hosted packs. They do not own the portable scenario.
- Third-party environment packs can be in their own repositories and use this
  package.
- Do not put downstream catalog names, paths, branch rules, labels, product
  assumptions, or private deployment words into the canonical docs.

## Verification

Before you declare repository work complete, run these commands in a virtual
environment with `pip install -e .`:

```sh
python -m unittest discover -s tests
raes-pack-validate --repo .
raes-pack-release check --all
raes-pack-validate --packs-root packs
raes-pack-release check --packs-root packs
python3 -m compileall src tests
make conformance
make go-check
make go-lint
make go-audit
make go-arch
make go-mutation
make go-regression
make prose
```

## Commits and releases

- A PR title MUST be a Conventional Commit (`feat:`, `fix:`, `docs:`,
  `chore:`, `refactor:`, `test:`, `ci:`, or `build:`). A required CI check
  enforces it.
- The type is the release decision. `feat:` gives a minor release, and `fix:`
  or `perf:` gives a patch release. `feat!:` or `BREAKING CHANGE:` gives a
  major release, which is a minor release before 1.0. The types docs, chore,
  test, ci, refactor, and build do not release.
- **Never edit the version or `CHANGELOG.md` by hand.** The version is in
  `pyproject.toml` (`[project].version`). **release-please** owns both. It
  keeps a `chore(main): release X.Y.Z` PR, and a merge of that PR publishes
  the release.
- **Never edit a pack version by hand.** Each pack in `packs/` has the package
  version. The release workflow writes it and refreshes the pack digests
  (ADR 0045).
- Squash-merge feature PRs. See
  `docs/decisions/adrs/0008-adopt-release-please.md`.
- Open the `dev` → `main` promotion PR with `make devmain`. Merge it with a
  **merge commit**. Never squash it, and never rebase it. Otherwise
  release-please loses the separate Conventional Commit subjects that it reads
  to decide the version and to build the changelog. See
  [ADR 0019](docs/decisions/adrs/0019-preserve-history-in-dev-main-promotions.md).
