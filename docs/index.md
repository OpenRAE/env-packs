# ACES Scenario Packs — Definition & Tooling

The canonical, shared home for the ACES scenario-pack **definition**, schemas,
template, and authoring tools, published as the installable `aces-scenario-packs`
package. It is subordinate to ACES core (`aces-sdl`), exists to make authoring
and shipping ACES scenarios easier, and defines no extensions to ACES semantics
([ADR 0009](decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)). Actual
scenario packs live in their own catalog repositories and consume this contract;
this repo does not host packs.

## Definition

- [Scenario packs — what a pack is](scenario-packs.md)
- [Golden readiness](golden-readiness.md)
- [Migration scrub policy](scrub-policy.md)
- Layout contract, schemas, and template ship as package data under
  `src/aces_scenario_packs/resources/`
  (`contract/pack-layout.md`, `schemas/`, `template/`).
- [Architecture Decision Records](decisions/adrs/README.md)

## Tools

- [Create a new pack (`aces-new-pack`)](new-pack-script.md)
- [Pack issue skeleton generator (`aces-pack-issue-skeleton`)](pack-issue-skeleton-script.md)
- `aces-pack-validate` / `aces-pack-release` — content-validation and release gates.

```{toctree}
:hidden:
:maxdepth: 2
:caption: Definition

scenario-packs
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
