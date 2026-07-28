# Ownership Boundary

An environment pack is shaped here, filled in by whoever authors a particular
scenario, and realized at runtime by a lab platform such as APTL. Four owners
meet at that seam. Their contracts are separate, and conflating them is how a
portable format quietly acquires a runtime dependency — or a runtime quietly
acquires scenario semantics.

This page is the env-packs-side statement of the boundary APTL records for its
issue #589; the two are meant to agree and to be read together.

## Four owners

| Concern | Owner |
| --- | --- |
| Portable scenario, workflow, capture, evidence, and inventory semantics | RAES |
| Environment-pack format, templates, schemas, validation, release tooling, and adoption guidance | `RAESystem/env-packs` (this repository) |
| A particular scenario's content, experiment design, and execution choices | The downstream scenario or experiment owner |
| Admitted-plan realization, lab lifecycle, trusted source acquisition, backend observation, and local evidence persistence | APTL |

### RAES owns the semantics

RAES owns portable scenario, workflow, capture, evidence, and inventory
*meaning*: the SDL and its objectives, conditions, evidence requirements, and
participant/attacker behaviour, together with the controlled vocabularies,
semantic compilation, and planner diagnostics. This repository consumes those
from the exactly pinned `raes` package and defines zero extensions to them
([ADR 0021](decisions/adrs/0021-adopt-raes-environment-pack-identity.md)). Where
a scenario needs expressivity RAES lacks, that gap is fixed upstream in RAES,
never worked around in the pack format.

### This repository owns the format, not a scenario

`RAESystem/env-packs` owns the environment-pack format: the layout contract,
templates, schemas, validation, release tooling, and adoption guidance. That is
the whole of its scope. It does not own — and must not encode — a particular
experiment or scenario: no pack content, no experiment design, no chosen
participants, targets, or execution. This repository ships the shape a pack
takes and the gates that prove a pack fits that shape; packs themselves live in
their own catalog repositories
([ADR 0021](decisions/adrs/0021-adopt-raes-environment-pack-identity.md), which
carries forward the charter of
[ADR 0001](decisions/adrs/0001-repository-purpose-and-boundary.md)).

### The downstream owner owns the scenario

Whoever authors a particular scenario or experiment owns its content, its
experiment design, and the execution choices made with a pack: which RAES
scenario is authored, what the environment contains, which capture requirements
are declared, and what the run is meant to show. Those choices are RAES inputs
expressed within this format. They are not authority over RAES semantics, and
they are not authority over APTL implementation detail.

### APTL owns runtime realization

APTL owns admitted-plan realization, lab lifecycle, trusted source acquisition,
backend observation, and APTL-local evidence persistence. It lowers an admitted
RAES execution plan onto real infrastructure through its own deployment backend
and records what it observed there. Those are runtime facts about one lab, not
portable pack content: an APTL run record is not a RAES inventory or capture
result, and a healthy container is not proof of a scenario objective.

## A pack does not select runtime implementation

The format carries declarative RAES content. It has no mechanism — and must
never acquire one — for a pack to select:

- APTL shell commands, container names, or compose fragments;
- host paths, output paths, or backend-specific persistence paths;
- collector implementations, registration ids, or import paths;
- credentials, secret sources, environment-variable keys, or trust roots.

A pack declares RAES capture *requirements*. APTL matches them to code-owned
collectors through its own trusted registry, fail-closed; a requirement that
exceeds the declared runtime capability is a diagnostic raised before any side
effect, not a fallback and not a pack-supplied override. Keeping that direction
one-way is what lets the same pack run against more than one backend.

## Reference

- APTL's ownership record for this boundary:
  [Brad-Edwards/aptl#589](https://github.com/Brad-Edwards/aptl/issues/589) and
  the note it produced,
  [environment-pack capture ownership](https://github.com/Brad-Edwards/aptl/blob/main/docs/architecture/issue-589-environment-pack-capture-ownership-preflight.md).
- [ADR 0001 — repository purpose and boundary](decisions/adrs/0001-repository-purpose-and-boundary.md)
- [ADR 0021 — RAES environment-pack identity and boundary](decisions/adrs/0021-adopt-raes-environment-pack-identity.md)
