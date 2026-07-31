# Ownership boundary

A pack is shaped here, filled in by whoever authors a scenario, and realized at
runtime by a lab platform such as APTL. Four owners meet at that seam. Keeping
their jobs separate is what lets one pack run on more than one backend — and what
stops a portable format from quietly acquiring a runtime dependency.

This is the env-packs side of a boundary APTL records for its issue #589. The two
are meant to agree and be read together.

## Four owners

| Concern | Owner |
| --- | --- |
| Portable scenario, workflow, capture, evidence, and inventory semantics | RAES |
| Environment-pack format, templates, schemas, validation, release tooling, and adoption guidance | `OpenRAE/env-packs` (this repository) |
| A particular scenario's content, experiment design, and execution choices | The downstream scenario or experiment owner |
| Admitted-plan realization, lab lifecycle, trusted source acquisition, backend observation, and local evidence persistence | APTL |

### RAES owns the meaning

RAES owns portable scenario, workflow, capture, evidence, and inventory meaning:
the SDL and its objectives, conditions, evidence requirements, and
participant/attacker behavior, along with the controlled vocabularies and
diagnostics. This repository consumes those from the exactly pinned `raes`
package and defines zero extensions to them. Where a scenario needs expressivity
RAES lacks, that gap is fixed upstream in RAES, never worked around in the pack
format.

### This repository owns the format, not a scenario

`OpenRAE/env-packs` owns the environment-pack format: the layout contract,
templates, schemas, validation, release tooling, and adoption guidance. That is
its whole scope. It does not own — and must not encode — a particular experiment
or scenario: no pack content, no experiment design, no chosen participants,
targets, or execution. It ships the shape a pack takes and the gates that prove a
pack fits that shape. Packs live in their own catalog repositories.

### The downstream owner owns the scenario

Whoever authors a particular scenario owns its content, its experiment design,
and the execution choices made with a pack: which RAES scenario is authored, what
the environment contains, which capture requirements are declared, and what the
run is meant to show. Those are RAES inputs expressed within this format. They are
not authority over RAES semantics, and not authority over runtime detail.

### APTL owns runtime realization

APTL owns admitted-plan realization, lab lifecycle, trusted source acquisition,
backend observation, and APTL-local evidence persistence. It lowers an admitted
RAES execution plan onto real infrastructure and records what it observed. Those
are runtime facts about one lab, not portable pack content: a run record is not a
RAES inventory result, and a healthy container is not proof of a scenario
objective.

## A pack does not select runtime implementation

The format carries declarative RAES content. It has no mechanism — and must never
acquire one — for a pack to select:

- APTL shell commands, container names, or compose fragments;
- host paths, output paths, or backend-specific persistence paths;
- collector implementations, registration ids, or import paths;
- credentials, secret sources, environment-variable keys, or trust roots.

A pack declares RAES capture *requirements*. The runtime matches them to
code-owned collectors through its own trusted registry, fail-closed. A
requirement that exceeds the declared runtime capability is a diagnostic raised
before any side effect — not a fallback, and not a pack-supplied override.

## Reference

- APTL's ownership record for this boundary:
  [Brad-Edwards/aptl#589](https://github.com/Brad-Edwards/aptl/issues/589) and the
  note it produced,
  [environment-pack capture ownership](https://github.com/Brad-Edwards/aptl/blob/main/docs/architecture/issue-589-environment-pack-capture-ownership-preflight.md).
- The decision records for this repository's purpose and boundary live in the
  [developer decision log](https://github.com/OpenRAE/env-packs/blob/main/docs/decisions/adrs/README.md).
