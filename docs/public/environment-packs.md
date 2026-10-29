# Pack reference

This page is the map of an environment pack: what each part is for, and where the
exact rules live. The normative contract — every field and its constraints —
ships inside the package as `contract/pack-layout.md`. This page explains it;
that file decides it.

For a gentler introduction, start with [what an environment pack is](concepts.md).

## The layout

A pack is a directory. It has a required core and optional layers you add when
the scenario needs them.

```
example-pack/
├── pack.yaml                      # identity and metadata
├── sdl/                           # the scenario start state (RAES SDL)
├── docs/
│   ├── provenance-ledger.yaml     # where the content came from
│   └── golden-readiness-checklist.md
├── assets/                        # custom files, planted content, briefings
├── build/  tests/  docs/walkthroughs/   # the reference triangle (optional)
├── flags/  challenges/  ctfd/     # the flag layer (optional, all-or-nothing)
├── experiments/                   # RAES experiment artifact set (optional)
└── profiles/                      # delivery bundles (optional)
```

## Identity: `pack.yaml`

`pack.yaml` names the pack and points at its other files. It carries the pack's
`name` (which must match the directory), `title`, `version`, and `status`, and it
records which optional layers ship. It is metadata, not a runtime contract.

## The scenario start state

The `sdl/` directory holds the authored environment as one or more
`<name>.sdl.yaml` documents, written in RAES SDL. This is the heart of a pack.

The validator parses **every** `sdl/*.sdl.yaml` through the installed `raes`
release, with full semantic validation. A pack that ships no start-state document,
or any document RAES rejects, fails. SDL is validated *through RAES* — this
project restates none of the SDL schema.

RAES resolves SDL modules and records them in its lockfile, `raes.lock.json`. A
pack's resolver cache lives under `sdl/.raes/module-cache/` and is excluded from
the pack's content identity.

Because SDL is the scenario specification, the smallest valid start state is
small:

```yaml
name: example-pack
nodes:
  target:
    type: compute
```

## Provenance ledger

Every pack ships `docs/provenance-ledger.yaml`, referenced from `pack.yaml`. It is
the machine-readable record of a pack's content origins:

- **`sources`** — every upstream corpus, tool, dataset, or original design the
  pack draws on, each with a license and how it was used.
- **`artifacts`** — the pack's files, classified by how they may be distributed.
- **`content_safety`** — attestations that the pack carries no real malware,
  live targets, credentials, or sensitive data. All must be true.
- **`review`** — the licensing, attribution, sensitive-data, and offensive-tooling
  review gates, modeled as data.

RAES owns pack *trust* — integrity and authenticity — under its
`reusable-asset-trust-policy`. Governed vocabularies, such as attack tactics and
the controlled concept families, stay in the RAES `concept-authority`. The ledger
records only the content-origin facts RAES does not define, and names those RAES
authorities rather than restating them.

## Compatibility manifest

A pack that needs to describe how it maps onto runtime profiles, delivery
bundles, and artifact boundaries adds `pack.compatibility.yaml` and points at it
from `pack.yaml`. The validator checks it against the packaged schema. It carries
no scenario semantics — scoring, oracles, and telemetry are RAES and runtime
concerns, not pack layers.

## Content identity

A pack can opt into a content identity so a consumer can prove which exact bytes
an identity covers. The pack points at a RAES associated-artifact manifest from
`pack.yaml`; RAES owns the identity model, and this package resolves the pack's
files and hands the bytes to RAES to bind.

Set identity, scenario meaning, and trust are separate claims: proving which
bytes a pack is does not prove the scenario's semantics, nor that the pack is
authentic or safe to run. See [validating a pack](validating.md) for the API.

## Experiments

A pack can carry the RAES documents that define an experiment over its scenario
family. Put them in `experiments/`:

| File | RAES contract |
| --- | --- |
| `<name>.exp.yaml` | `experiment-authoring-input-v1` |
| `<name>.task.json` | `experiment-task-v1` |
| `<name>.capture.json` | `experiment-capture-spec-v1` |

The scenario family is an `sdl/*.sdl.yaml` document with RAES variation points.
Each experiment names it with an id-only `intended_scenario_ref`:

```yaml
intended_scenario_ref:
  ref_kind: scenario
  ref_id: example-pack   # the SDL document's name
```

The documents join through their RAES references. `task_ref` and
`capture_spec_refs` resolve by id and version, never by file name. Several
experiments can share one task or capture specification.

The validator admits every document and the family through RAES. It checks
selection policies, typed treatments such as `factorial-treatments-v1`, and
scenario bindings against the family. A typed treatment pins the family's
canonical digest, so edit the pins after you edit the family.

Participant targets, apparatus compatibility, and every requested combination
need the consumer's manifests. The RAES trial compiler checks them, so a valid
pack is not yet an admitted trial plan. See
[loading an experiment](validating.md#loading-an-experiment).

Classify `experiments/` in the compatibility manifest's artifact boundaries.
Treatment labels and prompt commitments can reveal the design to participants.
Prompt content stays outside the pack; the family SDL carries only its
commitments.

This support requires `raes>=9.2.0` on CPython 3.14 and layout contract
version 8.

## Status

`pack.yaml` records a `status`:

- **`draft`** — design and source only; the live scenario is not stood up.
- **`built`** — it stands up, but its participant behavior is not yet proven end
  to end.
- **`golden`** — the live reference build exists and has participant-equivalent
  proof.

`golden` is a participant claim, not a management-plane one. See
[golden readiness](golden-readiness.md) for the bar.

## Optional layers

- **Reference triangle** — `build/` stands the environment up, `tests/` exercises
  its required behavior, and `docs/walkthroughs/` is the human, command-by-command
  version. The three must agree; a mismatch is a defect.
- **Flag layer** — `flags/`, `challenges/`, and `ctfd/` ship together or not at
  all, for capture-the-flag content.
- **Delivery profiles** — `profiles/` selects which participant, facilitator, or
  presenter files a given audience sees. It changes exposure, not the scenario.

## Build and release

`raes-pack-release` is the repository-wide, read-only gate that lints a pack,
builds a boundary-split release tree, leak-scans the participant tier, and emits a
validated publication profile. Run `raes-pack-release check --all` in a catalog
you control.

This repository's selected first-party packs live under `packs/` and are gated
explicitly with `raes-pack-validate --packs-root packs` and
`raes-pack-release check --packs-root packs`. The explicit root prevents the
legacy external-catalog default (`environments/`) from hiding hosted packs.

To *publish* a release — content identity, a CycloneDX SBOM, and provenance a
consumer can verify before install — run `raes-pack-release build --publish` and
follow [distribute and verify](distribution.md). Publishing requires the pack to
opt into [content identity](#content-identity); the SBOM is generated from the
pack's component boundary and bound to that identity.

## Catalog projection

`raes-pack-catalog` renders a versioned, machine-readable
[catalog projection](catalog.md) of a pack — its "card" — and aggregates cards
from many repositories into one static index. It is a generated read model over
the facts above; it adds no new pack fields and no scenario semantics.

## The boundary

Owning the format is not owning a scenario authored in it, and not realizing that
scenario at runtime. The [ownership boundary](ownership-boundary.md) sets out the
four owners — RAES, this repository, the downstream scenario owner, and the
runtime — and what each may not decide for the others.

## The normative sources

This page explains the format. These decide it:

- `contract/pack-layout.md`, bundled in the package — the field-by-field layout
  contract.
- The packaged schemas under `schemas/` — provenance and compatibility.
- The installed `raes` release, at or above the package's minimum version — all
  SDL semantics.
