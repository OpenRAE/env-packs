# What this is and is not

Read this before you build on the format, so its edges are clear up front.

## What this project does

- Defines the environment-pack layout, schemas, and template.
- Ships tools to scaffold a pack, validate one, and prepare a release.
- Validates a pack's start state through a pinned RAES release.

## What it does not do

- **It does not host packs.** Packs live in catalog repositories that consume
  this format. This repository holds the format and the tools, and no packs.
- **It does not run a scenario.** Building and running a live environment belongs
  to RAES and the runtime. A valid pack is checked content, not a running range.
- **It does not define scenario meaning.** The SDL and its semantics are
  [RAES](https://github.com/OpenRAE/rae)'s. This project consumes them and adds
  nothing. If a scenario needs something the language lacks, that gap is fixed in
  RAES, not worked around here.

## Maturity

- **One maintainer.** This is a single-maintainer project. There is no support
  SLA and no separate review or enforcement team. See
  [SUPPORT](https://github.com/OpenRAE/env-packs/blob/main/SUPPORT.md).
- **RAES is pinned exactly.** The project depends on one exact `raes` version.
  While the upstream RAES schemas are still draft, that pin moves deliberately,
  behind compatibility checks — so a pack's validation result is stable for a
  given release.
- **The contract still evolves.** The pack format is versioned. Breaking changes
  are possible and are recorded in the
  [decision records](https://github.com/OpenRAE/env-packs/blob/main/docs/decisions/adrs/README.md).

## Next

- [What an environment pack is](concepts.md)
- [The pack reference](environment-packs.md)
