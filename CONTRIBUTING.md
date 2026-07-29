# Contributing

Thanks for helping improve the RAES environment-pack format and tooling.

For a small fix — a typo, a broken link, a clear bug — open a pull request. For
anything that changes the pack contract, a schema, the template, or tool
behavior, open an issue first so the design can be agreed before you build it.

## Set up

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

## Run the checks

Run these from the repository root before you open a pull request. They are the
same checks CI runs:

```sh
python -m unittest discover -s tests   # unit tests
raes-pack-validate --repo .            # environment-pack content gate
raes-pack-release check --all          # pack release gate
python -m compileall src tests         # byte-compile
```

## Stay inside the boundary

This repository defines and validates the pack format; it does not host packs and
does not define RAES semantics. Keep changes within that boundary — see
[what a pack is](docs/public/concepts.md) and the
[ownership boundary](docs/public/ownership-boundary.md). Where RAES owns a concept,
consume it from RAES rather than restating it here.

## Documentation changes

Public documentation lives in `docs/public/` and is the only tree published to the
site. Maintainer records — decision records, CI, release mechanics — live
elsewhere under `docs/` and are indexed in [docs/README.md](docs/README.md).
Adding a page under `docs/public/` publishes it; a record anywhere else does not.
Follow the [style guide](docs/development/documentation-style-guide.md), and note
that the docs build is warning-strict and part of the merge gate.

## Open the pull request

- Target the `dev` branch. Changes reach `main` through a `dev` → `main`
  promotion.
- The PR title must be a [Conventional Commit](https://www.conventionalcommits.org)
  (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`, `build:`). A
  required check enforces this and bans tool-branding prefixes. Feature PRs are
  squash-merged, so the title becomes the commit — get it right.
- For a change to the contract or a schema, include the rationale, the
  compatibility impact, and how you validated it.

## Releases

Releases are managed by [release-please](https://github.com/googleapis/release-please)
(see [ADR 0008](docs/decisions/adrs/0008-adopt-release-please.md)): merge-driven,
nothing hand-run. Your **Conventional Commit PR title** decides the version:
`feat:` → minor, `fix:`/`perf:` → patch, `feat!:`/`BREAKING CHANGE:` → major
(before 1.0, a major demotes to minor); `docs`/`chore`/`refactor`/`test`/`ci`/`build`
do not release.

You never bump a version or edit `CHANGELOG.md`. As PRs land on `main`,
release-please maintains a `chore(main): release X.Y.Z` pull request; merging that
one tags and publishes.

Promote `dev` to `main` with `make devmain`, and merge that promotion with a
**merge commit** — never squash or rebase it, or release-please loses the
individual commit subjects it reads to build the changelog (see
[ADR 0019](docs/decisions/adrs/0019-preserve-history-in-dev-main-promotions.md)).
