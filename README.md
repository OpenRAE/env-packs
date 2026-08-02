# RAES Environment Packs

[![PyPI](https://img.shields.io/pypi/v/raes-env-packs)](https://pypi.org/project/raes-env-packs/)
[![Python](https://img.shields.io/pypi/pyversions/raes-env-packs)](https://pypi.org/project/raes-env-packs/)
[![Documentation](https://app.readthedocs.org/projects/env-packs/badge/?version=latest)](https://env-packs.readthedocs.io/en/latest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/OpenRAE/env-packs/badge)](https://scorecard.dev/viewer/?uri=github.com/OpenRAE/env-packs)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13833/badge)](https://www.bestpractices.dev/projects/13833)

RAES environment packs give a scenario a standard shape. This package defines that
shape and gives you the tools to build, check, and ship a pack.

A pack holds the declarative content for one reference environment: the scenario
start state, its assets, and a record of where the content came from. Authors
build packs; consumers validate a pack before they trust it. The format and the
tools ship together, so you validate a pack against the same version you built it
against.

This repository defines and validates the format and hosts selected first-party
packs under [`packs/`](packs/). External catalogs can consume the same package
and continue to host their own packs.

## What a pack looks like

```
example-pack/
├── pack.yaml                  # identity: name, title, version, status
├── sdl/example.sdl.yaml       # the scenario start state (RAES SDL)
└── docs/
    └── provenance-ledger.yaml # where the content came from
```

The start state is small to begin with:

```yaml
name: example-pack
nodes:
  target:
    type: vm
```

## Install

```sh
pip install raes-env-packs
```

That installs the command-line tools and the importable library:

- `raes-pack-new` — scaffold a new pack with a progressive wizard.
- `raes-pack-validate` — the author-CI check for a catalog checkout.
- `raes-pack-release` — build, lint, and release-gate a pack.
- `raes-pack-kit` — discover, inspect, preview, add, update, replace, and remove
  reusable infrastructure kits.
- `raes-pack-issue-skeleton` — generate a pack's starter GitHub issues.

## Validate your first pack

Scaffold a valid minimal pack in your catalog repository and check it. The
wizard generates only the files the pack needs, formats the scenario identity
through RAES, and validates the result before it lands:

```sh
raes-pack-new example-pack --route minimal --yes
python -c "from raes_env_packs import validate_pack; print(validate_pack('environments/example-pack').ok)"
```

```
True
```

`validate_pack` is the check a consumer runs before trusting a pack: it reads the
staged files, returns a result, prints nothing, and never runs the pack's code.
The [quickstart](https://env-packs.readthedocs.io/en/latest/quickstart.html) walks
through it step by step.

## Choose your route

- **Author a pack** — start with the [quickstart](https://env-packs.readthedocs.io/en/latest/quickstart.html)
  and the [pack reference](https://env-packs.readthedocs.io/en/latest/environment-packs.html),
  then compose common infrastructure from [kits](https://env-packs.readthedocs.io/en/latest/kits.html).
- **Consume a pack** — see [validating a pack](https://env-packs.readthedocs.io/en/latest/validating.html).
- **Contribute** — read [CONTRIBUTING.md](CONTRIBUTING.md).

Full documentation is on [Read the Docs](https://env-packs.readthedocs.io/en/latest/).

## What this is and is not

This project defines the pack format, hosts selected first-party packs, and
provides the tools that check them. It does **not** run a scenario or define
scenario meaning — the RAES scenario
language and its semantics belong to [RAES](https://github.com/OpenRAE/rae), and
this project consumes them from an exactly pinned `raes` release. It is a
single-maintainer project with no support SLA. See the
[limitations](https://env-packs.readthedocs.io/en/latest/limitations.html) for the
full picture.

## Contributing

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python -m unittest discover -s tests
```

[CONTRIBUTING.md](CONTRIBUTING.md) has the full setup, test, and submission path.
Maintainer records — decision records, CI, and release mechanics — are indexed in
[docs/README.md](docs/README.md).

## Releases

Releases are managed by [release-please](https://github.com/googleapis/release-please):
merge-driven, nothing hand-run. Your **Conventional Commit PR title** is the
release decision — `feat:` is a minor bump, `fix:` a patch, `docs:`/`chore:` no
release. You never edit the version or `CHANGELOG.md`; release-please owns both.
See [CONTRIBUTING.md](CONTRIBUTING.md#releases) for the details.

## License

MIT — see [LICENSE](LICENSE).
