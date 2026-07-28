# RAES Environment Packs — Definition & Tooling

The canonical, shared home for the RAES environment-pack **definition**, schemas,
template, and authoring tools, published as the installable `raes-env-packs`
package. It is subordinate to RAES core (`raes`), exists to make authoring
and shipping RAES scenarios easier, and defines no extensions to RAES semantics
([ADR 0021](decisions/adrs/0021-adopt-raes-environment-pack-identity.md)). Actual
environment packs live in their own catalog repositories and consume this contract;
this repo does not host packs.

## Definition

- [Environment packs — what a pack is](environment-packs.md)
- [Migrating from the retired package identity](raes-migration.md)
- [Ownership boundary — RAES, this repository, downstream, APTL](ownership-boundary.md)
- [Golden readiness](golden-readiness.md)
- [Migration scrub policy](scrub-policy.md)
- Layout contract, schemas, and template ship as package data under
  `src/raes_env_packs/resources/`
  (`contract/pack-layout.md`, `schemas/`, `template/`).
- [Architecture Decision Records](decisions/adrs/README.md)

## Tools

- [Create a new pack (`raes-new-pack`)](new-pack-script.md)
- [Pack issue skeleton generator (`raes-pack-issue-skeleton`)](pack-issue-skeleton-script.md)
- `raes-pack-validate` / `raes-pack-release` — content-validation and release gates.

```{toctree}
:hidden:
:maxdepth: 2
:caption: Definition

environment-packs
raes-migration
ownership-boundary
golden-readiness
scrub-policy
```

```{toctree}
:hidden:
:maxdepth: 1
:caption: Tools

new-pack-script
pack-issue-skeleton-script
```

```{toctree}
:hidden:
:maxdepth: 1
:caption: Decisions

decisions/adrs/README
```
