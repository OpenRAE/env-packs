# Contributing

Thanks for helping improve the RAES environment-pack format and tooling.

For a small fix — a typo, a broken link, a clear bug — open a pull request. For
a change to the pack contract, a schema, the template, or tool behavior, open an issue first.
Agree on the design before you build it.

## Set up

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

## Run the checks

Run these from the repository root before you open a pull request. They are the
same checks CI runs:

```sh
python -m unittest discover -s tests   # unit tests
raes-pack-validate --repo .            # environment-pack content gate
raes-pack-release check --all          # pack release gate
raes-pack-validate --packs-root packs  # hosted first-party packs
raes-pack-release check --packs-root packs
python -m compileall src tests         # byte-compile
```

## Stay inside the boundary

This repository defines and validates the pack format and hosts selected
first-party packs under `packs/`; it does not define RAES semantics. Keep
changes within that boundary — see
[what a pack is](docs/public/concepts.md) and the
[ownership boundary](docs/public/ownership-boundary.md). Where RAES owns a concept,
consume it from RAES rather than restating it here.

## Documentation changes

Use the [documentation style guide](docs/development/documentation-style-guide.md) for all maintained prose.
It explains Diataxis purpose, STE, source verification, meaning preservation, and narrow exclusions for historical or exact records.
Use the existing `documentation` skill if available; the guide also gives commands that need no personal skill installation.
Run Vale and STE on explicit changed Markdown paths, including hidden directories and content assets.
Record source paths, revisions, commands, results, and corrected differences in your pull request.
Review purpose and meaning separately from checker findings.

Only `docs/public/` publishes to the site.
Developer records stay elsewhere under `docs/`; [docs/README.md](docs/README.md) indexes them.
Keep the warning-strict Sphinx build and publication check.
Keep current Python instructions until the separate Go migration and cutover land.

## Open the pull request

- Target the `dev` branch. Changes reach `main` through a `dev` → `main`
  promotion.
- The PR title must be a [Conventional Commit](https://www.conventionalcommits.org)
  (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`, `build:`). A
  required check enforces this and bans tool-branding prefixes. Feature PRs are
  squash-merged, so the title becomes the commit — get it right.
- A PR into `dev` merges through the `dev` merge queue. The queue merges the PR
  when `verify` passes on the merge group (see
  [ADR 0047](docs/decisions/adrs/0047-merge-dev-pull-requests-through-a-merge-queue.md)).
- For a change to the contract or a schema, include the rationale, the
  compatibility impact, and how you validated it.

## Releases

[release-please](https://github.com/googleapis/release-please)
manages releases (see [ADR 0008](docs/decisions/adrs/0008-adopt-release-please.md)).
Releases follow merges; do not run them by hand. Your **Conventional Commit PR title** decides the version:
`feat:` → minor, `fix:`/`perf:` → patch, `feat!:`/`BREAKING CHANGE:` → major;
`docs`/`chore`/`refactor`/`test`/`ci`/`build` do not release.

You never bump a version or edit `CHANGELOG.md`. As PRs land on `main`,
release-please maintains a `chore(main): release X.Y.Z` pull request; merging that
one tags and publishes.

Promote `dev` to `main` with `make devmain`, and merge that promotion with a
**merge commit** — never squash or rebase it.
Otherwise, release-please loses the individual commit subjects that determine the changelog (see
[ADR 0019](docs/decisions/adrs/0019-preserve-history-in-dev-main-promotions.md)).
