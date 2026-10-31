# Contributing

Thank you for your help with the RAES environment-pack format and tooling.

For a small fix, such as a typo, a broken link, or a clear bug, open a pull
request. For a change to the pack contract, a schema, the template, or tool
behavior, open an issue first. Agree on the design before you build it.

## Set up

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

The Go checks also need [mise](https://mise.jdx.dev). `mise install` installs
the tool versions that `mise.toml` pins and verifies them against `mise.lock`.

## Run the checks

Run these commands from the repository root before you open a pull request. CI
runs the same checks:

```sh
python -m unittest discover -s tests   # unit tests
raes-pack-validate --repo .            # environment-pack content gate
raes-pack-release check --all          # pack release gate
raes-pack-validate --packs-root packs  # hosted first-party packs
raes-pack-release check --packs-root packs
python -m compileall src tests         # byte-compile
make go-check                          # Go build, vet, and tests (ADR 0047)
make go-lint                           # Go lint, formatting, and module tidiness
```

`make go-fuzz` runs every Go fuzz target for 30 seconds each. CI runs it in
`fuzz.yml`.

## Stay inside the boundary

This repository defines and validates the pack format, and it hosts selected
first-party packs in `packs/`. It does not define RAES semantics. Keep each
change inside that boundary. See [what a pack is](docs/public/concepts.md) and
the [ownership boundary](docs/public/ownership-boundary.md). When RAES owns a
concept, use it from RAES. Do not state it again here.

## Documentation changes

The public documentation is in `docs/public/`. It is the only tree that the
site publishes. The maintainer records, such as decision records, CI, and
release mechanics, are in other directories under `docs/`.
[docs/README.md](docs/README.md) lists them. A new page in `docs/public/`
becomes public, and a record in any other place does not. Follow the
[style guide](docs/development/documentation-style-guide.md). The docs build
treats warnings as errors and is part of the merge gate.

## Open the pull request

- Target the `dev` branch. Changes reach `main` through a promotion from `dev`
  to `main`. A pull request for the Go port targets the `go-cutover` branch
  instead (ADR 0047).
- The pull request title must be a
  [Conventional Commit](https://www.conventionalcommits.org) (`feat:`, `fix:`,
  `docs:`, `chore:`, `refactor:`, `test:`, `ci:`, or `build:`). A required check
  enforces this and rejects tool-branding prefixes. Feature pull requests are
  squash-merged, so the title becomes the commit message. Write it with care.
- For a change to the contract or a schema, give the reason, the compatibility
  effect, and how you validated the change.

## Releases

[release-please](https://github.com/googleapis/release-please) manages the
releases ([ADR 0008](docs/decisions/adrs/0008-adopt-release-please.md)). A
merge starts each release, and no one runs a release script. The
**Conventional Commit title of your pull request** sets the version:

- `feat:` gives a minor release.
- `fix:` and `perf:` give a patch release.
- `feat!:` and `BREAKING CHANGE:` give a major release. Before version 1.0, a
  major release becomes a minor release.
- `docs`, `chore`, `refactor`, `test`, `ci`, and `build` do not release.

Do not change a version or edit `CHANGELOG.md`. When pull requests reach
`main`, release-please keeps a `chore(main): release X.Y.Z` pull request up to
date. A merge of that pull request tags and publishes the release.

Promote `dev` to `main` with `make devmain`. Merge that promotion with a
**merge commit**. Do not squash or rebase it, because release-please then loses
the commit subjects that it reads to build the changelog
([ADR 0019](docs/decisions/adrs/0019-preserve-history-in-dev-main-promotions.md)).
