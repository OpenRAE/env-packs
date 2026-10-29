# ADR 0042 — Carry RAES experiment artifact sets in packs

- Status: Accepted
- Date: 2026-10-29
- Extends: ADR 0011 (pinned RAES SDL validation),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md), and
  [ADR 0038](0038-ship-raes-concept-bindings-beside-pack-sdl.md)
- Coordination: OpenRAE/env-packs issue 504; OpenRAE/rae issues 1666 and 1696

## Context

RAES defines an experiment through three contracts:
`experiment-authoring-input-v1`, `experiment-task-v1`, and
`experiment-capture-spec-v1`. A typed factorial design
(`factorial-treatments-v1`) selects scenario-family alternatives and
participant configuration. The RAES trial compiler accepts these documents,
an admitted `ExpandedScenario` family, and apparatus context from the caller.

The pack format had no place for experiment documents. RAES 9.2.0 adds
`admit_scenario_family`, so an import-free pack SDL document can be an
experiment family.

## Decision

- An optional `experiments/` directory holds the experiment artifact set.
  Direct members are recognized by suffix: `*.exp.yaml` (authoring input),
  `*.task.json` (task), and `*.capture.json` (capture specification).
- The shared static authority validates every recognized document through the
  RAES contract models and the RAES experiment loader. A malformed document
  fails even when no experiment refers to it.
- RAES reference fields join the documents. Task and capture references
  resolve by identity and version. File names carry no identity.
- Each experiment names one pack SDL document as its family through an
  id-only `intended_scenario_ref`. The validator admits that family through
  RAES and checks selection policies, typed treatments, and scenario bindings
  with the RAES owning validators.
- Participant and apparatus targets need caller-supplied manifests. The RAES
  trial compiler checks them, and every requested combination, at compilation.
- `load_pack_experiments` returns the validated typed artifact set.
  `PackExperiment.compilation_request` joins it with caller-supplied apparatus
  context into a RAES `TrialCompilationRequest`. Input references derive from
  the pack documents.
- The layout contract version becomes 8.

## Consequences

- Consumer checks, author CI, release, and verification share one experiment
  verdict.
- Content identity, release archives, and reload carry the documents without a
  new carrier.
- A family edit makes typed treatment pins stale until the author updates them.
- Static validity is not trial admission. Compilation with trusted apparatus
  context remains a consumer step.
- This repository adds no experiment schema, selection rule, or compiler.
