# RAES Environment Packs

RAES environment packs give a scenario a standard shape. This package defines
that shape and gives you the tools to build, check, and ship a pack.

A pack holds the declarative content for one reference environment: the scenario
start state, its assets, and the record of where the content came from. Authors
build packs; consumers validate a pack before they trust it. Because the format
and the tools ship together in one installable package, you validate a pack
against the same version you built it against.

This repository defines and validates the format. It does not host packs —
those live in their own catalog repositories.

## Start here

New to environment packs? The [quickstart](quickstart.md) scaffolds a pack and
validates it in about five minutes.

```sh
pip install raes-env-packs
```

## Choose your route

- **Author a pack** — scaffold one with the [pack tools](new-pack-script.md) and
  plan it against the [golden-readiness checklist](golden-readiness.md).
- **Consume a pack** — [check a pack](checking.md) you received with
  `raes-pack-check`, or call the [`validate_pack` API](validating.md), before you
  trust its bytes.
- **Publish a catalog** — render a machine-readable
  [catalog projection](catalog.md) with `raes-pack-catalog` so a static catalog,
  browser, or Hub can list your packs.
- **Understand the format** — read [what a pack is](concepts.md) and the
  [pack reference](environment-packs.md).
- **Know the limits** — see [what this is and is not](limitations.md).
- **Contribute** — start from the
  [contributing guide](https://github.com/OpenRAE/env-packs/blob/main/CONTRIBUTING.md).

```{toctree}
:hidden:
:caption: Get started

quickstart
concepts
limitations
```

```{toctree}
:hidden:
:caption: Author a pack

new-pack-script
pack-issue-skeleton-script
golden-readiness
```

```{toctree}
:hidden:
:caption: Consume a pack

checking
validating
catalog
```

```{toctree}
:hidden:
:caption: Reference

environment-packs
ownership-boundary
raes-migration
```
