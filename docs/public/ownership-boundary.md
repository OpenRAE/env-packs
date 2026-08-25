# Ownership boundary

A pack is shaped here, filled in by whoever authors a scenario, and realized at
runtime by a lab platform such as LilRAE. APTL is being renamed to LilRAE: those
names identify one project across a rename, not separate products or layers.
Four owners meet at the pack/runtime seam. Keeping their jobs separate is what
lets one pack run on more than one backend — and what stops a portable format
from quietly acquiring a runtime dependency.

This is the env-packs side of a boundary the LilRAE project recorded under its
APTL-era issue #589. The two records are meant to agree and be read together.

## Four owners

| Concern | Owner |
| --- | --- |
| Portable scenario, workflow, capture, evidence, and inventory semantics | RAES |
| Environment-pack format, templates, schemas, validation, release tooling, adoption guidance, and selected first-party pack content | `OpenRAE/env-packs` (this repository) |
| A particular scenario's content and experiment design | Its declared pack owner, which may be this repository or an external catalog |
| Admitted-plan realization, lab lifecycle, trusted source acquisition, backend observation, and local evidence persistence | LilRAE (formerly APTL) |

### RAES owns the meaning

RAES owns portable scenario, workflow, capture, evidence, and inventory meaning:
the SDL and its objectives, conditions, evidence requirements, and
participant/attacker behavior, along with the controlled vocabularies and
diagnostics. This repository consumes those from the exactly pinned `raes`
package and defines zero extensions to them. Where a scenario needs expressivity
RAES lacks, that gap is fixed upstream in RAES, never worked around in the pack
format.

### This repository owns the format and selected first-party scenarios

`OpenRAE/env-packs` owns the environment-pack format: the layout contract,
templates, schemas, validation, release tooling, and adoption guidance. Under
ADR 0036 it may also own selected first-party scenario packs under `packs/`.
Those packs remain RAES inputs and receive no special semantics or runtime
privileges from being colocated with the tooling.

### The downstream owner owns the scenario

Whoever owns a particular pack owns its content and experiment design,
and the execution choices made with a pack: which RAES scenario is authored, what
the environment contains, which capture requirements are declared, and what the
run is meant to show. Those are RAES inputs expressed within this format. They are
not authority over RAES semantics, and not authority over runtime detail.

### LilRAE owns runtime realization, not pack content

LilRAE owns admitted-plan realization, lab lifecycle, trusted source acquisition,
backend observation, and LilRAE-local evidence persistence. It lowers an admitted
RAES execution plan onto real infrastructure and records what it observed. Those
are runtime facts about one lab, not portable pack content: a run record is not a
RAES inventory result, and a healthy container is not proof of a scenario
objective.

## A pack does not select runtime implementation

The format carries declarative RAES content. It has no mechanism — and must never
acquire one — for a pack to select:

- LilRAE shell commands, container names, or compose fragments;
- host paths, output paths, or backend-specific persistence paths;
- collector implementations, registration ids, or import paths;
- credentials, secret sources, environment-variable keys, or trust roots.

A pack declares RAES capture *requirements*. The runtime matches them to
code-owned collectors through its own trusted registry, fail-closed. A
requirement that exceeds the declared runtime capability is a diagnostic raised
before any side effect — not a fallback, and not a pack-supplied override.

## Reference

- The LilRAE project's APTL-era ownership record for this boundary:
  [Brad-Edwards/aptl#589](https://github.com/Brad-Edwards/aptl/issues/589) and the
  note it produced before the rename,
  [environment-pack capture ownership](https://github.com/Brad-Edwards/aptl/blob/main/docs/architecture/issue-589-environment-pack-capture-ownership-preflight.md).
- The decision records for this repository's purpose and boundary live in the
  [developer decision log](https://github.com/OpenRAE/env-packs/blob/main/docs/decisions/adrs/README.md).
