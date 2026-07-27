# Scenario Packs

A scenario pack is declarative content plus the tooling, docs, and evidence for
a known-good reference implementation. It is not the range engine, scoreboard,
portal, class-management UI, or telemetry product.

This repository is the authoritative home for that format, and is subordinate to
ACES core (`aces-sdl`): it exists to make authoring and shipping ACES scenarios
easier and defines no extensions to ACES semantics
([ADR 0009](decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)). It ships
the layout contract, template, and tooling as package data, so an author
validates against the same version they build against. Packs live in their own
catalog repositories and consume this package; this repo does not host packs.

## Required Shape

Every new pack starts under `scenarios/<name>/` in a catalog repo and follows
the layout contract bundled in the package (`contract/pack-layout.md`):

- `pack.yaml` for identity, provenance, status, and optional-layer inventory.
- `docs/provenance-ledger.yaml` (required) — the machine-readable source,
  licensing, content-safety, publication-review, and customer-overlay contract,
  referenced from `pack.yaml` via `provenance_ledger:`.
- `pack.compatibility.yaml` when a pack needs a validated product/commercial
  compatibility projection over runtime profiles, delivery bundles, platform
  features, artifact boundaries, operator surfaces, and validation gates.
- `sdl/` for the scenario start state and structured scenario definition.
- `assets/` for custom files, planted content, host assets, and briefing assets.
- `flags/`, `challenges/`, and `ctfd/` as an all-or-nothing flag layer.
- `build/`, `tests/`, and `docs/walkthroughs/` as the reference triangle.
- `profiles/` for delivery and audience bundles when the scenario has them.
- `docs/golden-readiness-checklist.md` for milestone planning and final review.

## SDL Validation (through ACES)

`sdl/` holds the scenario start state as one or more `<name>.sdl.yaml` documents
authored in [ACES SDL][aces-sdl]. `aces-pack-validate` parses **every** direct
`sdl/*.sdl.yaml` through ACES (`aces_sdl.parse_sdl_file`, with full semantic
validation) and fails on a pack that ships no start-state document or any
document ACES rejects. SDL is validated *through ACES* — no SDL schema is
restated here, and the local JSON-Schema subset validator never touches SDL.

`aces-sdl` is therefore a hard, exactly-pinned runtime dependency
(the exact version lives once in [`pyproject.toml`](../pyproject.toml)) rather
than an optional one: the gate is fail-closed, so an
optional coupling that skipped SDL when ACES was absent would leave every pack's
most important content unchecked. The exact pin is deliberate while ACES SDL
contracts are `stability: draft`; advancing it requires compatibility tests. This
raises the package's Python floor to match ACES (`>=3.11`). See
[ADR 0011](decisions/adrs/0011-require-pinned-aces-sdl-validation.md).

The validator also enforces the one canonical pack→SDL link: each
`flags/placement.yaml` `host` must resolve to a real `Scenario.nodes` id in at
least one validated SDL document in the pack (the union across a pack's full and
reduced start-state variants). Only `flags[].host` is checked; no SDL reference
is inferred from prose, filenames, or arbitrary keys.

## Single-Pack Consumer Validation

`aces-pack-validate` is the author-CI surface for a catalog checkout. A consumer
ingesting one pack uses the public library boundary instead:

```python
from aces_scenario_packs import PackValidationLimits, validate_pack

result = validate_pack(
    staged_pack,
    limits=PackValidationLimits(max_metadata_bytes=512 * 1024),
)
```

`ValidationResult.ok` is true when `errors` is empty. Each error is a bounded,
body-free code with at most a canonical pack-relative filename and field path.
The function is silent and does not read environment configuration, invoke Git
or subprocesses, execute pack code, log, write caches, or mutate process globals.

The consumer contract checks:

- `pack.yaml` and its `name`, `title`, and `version` identity fields, including
  agreement between the pack name and staging-directory name;
- the required referenced provenance ledger against the packaged schema,
  matching pack name, all-true content-safety attestations, and required review
  gates;
- the referenced compatibility manifest, when present, against the packaged
  schema; and
- every direct `sdl/*.sdl.yaml` document through the pinned ACES parser.

The boundary inventory and reads are descriptor-anchored and no-follow.
Non-canonical paths, escaping pointers, symlinks, hardlinks, special files,
duplicate YAML keys, invalid UTF-8, and resource-limit violations fail closed.
Callers must acquire and immutably stage the directory before validation, then
promote those same bytes.

ACES 0.20 does not expose a resolver-policy seam for file-backed SDL parsing.
The consumer API therefore parses supplied SDL content without a file context;
an SDL document containing imports fails with `sdl.imports-denied` instead of
performing network I/O or writing `sdl/.aces/module-cache`. The author CLI keeps
file-backed parsing under its separately controlled environment. Catalog
discovery, pack validators/tests, leak scanning, flag-placement joins, release
readiness, and content-manifest verification are outside this consumer API.

See [ADR 0013](decisions/adrs/0013-separate-consumer-static-validation-from-author-ci.md).

## Status Meanings

- `draft`: design/source only; the full live scenario is not stood up.
- `built`: it stands up somewhere, but the declared ACES participant behavior
  has not been proven end to end from the participant surface.
- `golden`: the declared live reference build exists, enters participant start
  state, and has participant-equivalent full-path proof.

Do not mark a pack `golden` because management-plane checks pass. Operator
channels are useful for provisioning and diagnostics, but they do not prove the
participant experience.

## Reference Triangle

The reference triangle is one coherent proof surface:

- `build/` stands up the golden range.
- `tests/` exercises every required ACES participant behavior and objective
  against that live range.
- `docs/walkthroughs/` is the human-readable, command-by-command version of the
  same behavior.

The three must agree on the declared ACES behavior, objectives, and observable
outcomes. A mismatch between them is a defect.

## Compatibility Manifest

`pack.yaml` is the catalog entrypoint. When it contains
`compatibility_manifest: pack.compatibility.yaml`, the referenced file is
validated against the bundled `pack-compatibility.schema.yaml` by
`aces-pack-validate`.

The compatibility manifest separates:

- runtime/provider profiles (`local_minimal`, `aws_minimal`, `aws_full`);
- delivery/audience bundles (`guided`, `unguided`, `purple-team`,
  `agent-benchmark`, `demo`);
- participant/public, operator-only, oracle-only, private, and commercial
  artifact boundaries;
- assets, operator surfaces, and validation gates.

It carries **zero extensions to ACES semantics**: scoring, validation-oracle,
telemetry, and lifecycle (reset/rebuild/teardown) are ACES/runtime concerns and
are deliberately not manifest layers
([ADR 0009](decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)).

The manifest indexes existing pack-local files. It is not a runtime engine,
dependency lockfile, provider adapter, scoreboard, telemetry product, or proof
store.

## Provenance Ledger

Every pack ships `docs/provenance-ledger.yaml`, referenced from `pack.yaml`
(`provenance_ledger:`) and validated against the bundled
`provenance.schema.yaml` by `aces-pack-validate`. It is the canonical,
machine-readable record of:

- **`sources[]`** — upstream corpora, frameworks, tooling, datasets, research,
  original design, and generated material, each with a stable id, license,
  usage, and attribution requirement, plus what was used and deliberately
  excluded.
- **`artifacts[]`** — pack-relative roots classified for distribution as `open`,
  `redistributable`, `internal-only`, `commercial-only`, `generated`, or
  `customer-specific`. This open-vs-ACES-only axis is distinct from the
  compatibility manifest's runtime-visibility export values.
- **`content_safety{}`** — mandatory attestations (no real malware, third-party
  targets, credentials, or sensitive data; offensive-tooling boundary), all of
  which CI requires to be true.
- **`review{}`** — a publication-review checklist modelled as data, covering
  licensing, attribution, sensitive-data, and offensive-tooling gates.

Customer overlays are declared as path-contained `overlays[]` slots; their
content is `customer-specific` and may be removed without contaminating the base
pack. `docs/lineage.md` stays human prose and cites the ledger.

The provenance schema is enforced for every pack: it is the content-safety and
publication-review gate, and pack exports carry the ledger rather than bypassing
it.

**ACES is the authority for pack trust.** A scenario pack is a `reusable_scenario`
asset in the ACES reusable-asset trust policy
(`reusable-asset-trust-policy/v1`; ACES ADR-071), which owns pack integrity and
authenticity (`integrity_digest`, `authenticity_signature`,
`provenance_lock_record`, `governance_source`, `artifact_checksum`). Per
[ADR 0009](decisions/adrs/0009-scenario-packs-subordinate-to-aces.md) and
[ADR 0010](decisions/adrs/0010-consume-aces-reusable-asset-trust-policy.md), this
ledger is scoped to pack-domain facts ACES does not define — content-origin
licensing/attribution (`sources[]`), distribution class (`artifacts[]`),
content-safety attestations (`content_safety{}`), publication review (`review{}`),
and customer-overlay containment (`overlays[]`) — and re-defines none of the
ACES-owned trust concepts; those are established by ACES mechanisms
(scenario-snapshot digest, `aces.lock.json`, RegistryTrustPolicy signatures). ACES
schemas are `stability: draft`, so the ledger references the policy now and the
explicit upstream pin lands once ACES marks it stable. The bundled
[layout contract](https://github.com/RAESystem/env-packs/blob/main/src/aces_scenario_packs/resources/contract/pack-layout.md)
carries the full field-by-field mapping.

**ACES concept-authority governs concept vocabulary.** ATT&CK and ATLAS
offensive-behaviour tactics, UCO concept families, and the controlled
vocabularies are published by ACES under `contracts/concept-authority/` and are
authored and validated in ACES SDL behaviour specifications, not restated in the
pack format. The provenance ledger therefore carries no `sources[].kind`, and the
canonical challenge contract carries no `challenges[].category`; both were
free-text overlaps of governed concepts, and a challenge's presentation grouping
is an adapter-local CTFd concern. The remaining pack vocabulary (distribution
class, source licensing/usage, review gates, challenge display text, delivery
audiences, visibility) is genuinely pack-domain. This advanced the provenance
schema to `scenario-pack-provenance/v2` and the scenario-pack contract to
version 3. See
[ADR 0014](decisions/adrs/0014-consume-aces-concept-authority.md).

## Pack Content Identity

A consumer that ingests a pack by reference (path/key + version + digest) needs
to prove which concrete bytes the identity covers. ACES owns that portable model:
`associated-artifact-manifest-v1` attaches one exact payload set to a scenario
parent, `associated-artifact-set/v1` derives its set digest, and the ACES
validator binds the parent, set, checksums, sizes, and staged bytes.

A pack opting into content identity points at the ACES JSON manifest from
`pack.yaml`:

```yaml
associated_artifact_manifest: associated-artifacts.json
```

Each artifact keeps its opaque manifest-local id and uses a pack-local locator
such as `aces-scenario-pack:/docs/operator-guide.md`. The URI is not integrity
evidence; this package resolves it inside the opened pack root and supplies the
concrete bytes to ACES. The manifest carrier and
`sdl/.aces/module-cache/` are excluded, while every other regular file must be
declared. Missing, extra, unsafe, or changed members fail closed.

The public, in-process API separates authoring derivation from consumer
validation:

```python
from aces_scenario_packs import (
    derive_pack_content_manifest,
    pack_content_digest,
    validate_pack_content_manifest,
    verify_pack_content_digest,
)

derived = derive_pack_content_manifest(pack_root)  # persist during authoring/release
declared = validate_pack_content_manifest(pack_root)
digest = pack_content_digest(pack_root)            # declared ACES set digest
verify_pack_content_digest(pack_root, expected)    # full validation, then compare
```

Derivation recomputes descriptor checksums, sizes, and the set digest from a
caller-owned immutable staging area. Validation instead requires the manifest
already shipped with the pack to agree with those bytes. Both parse the SDL
parent through ACES. Neither runs git, a subprocess, pack-local code, network
resolution, or archive extraction.

**Set identity is not parent identity or trust.** Per
[ADR 0012](decisions/adrs/0012-pack-content-identity-and-trust-boundary.md), this
repository owns only pack layout, safe materialization, and exact inventory.
ACES owns canonicalization and byte-binding semantics. The resulting
`associated_artifact_set` identity is distinct from the scenario semantic
digest; neither one proves authenticity, authorization, entitlement, or safe
handling.

A directory API cannot make mutable storage atomic. Consumers must acquire and
immutably stage a pack, validate and digest that exact staging area, atomically
promote the same bytes, and reverify before use when the storage boundary does
not make that redundant.

## Validity and ACES participant behavior

The hydrated ACES SDL is the scenario specification. Declare attacker behavior
with ACES participant semantics: bind the attacker through `agents` and
`behavior_specifications`, declare governed actions through `action_contracts`,
and use ACES preconditions, effects, failure classes, observation boundaries,
outcome interpretation rules, objectives, evidence requirements, and workflows
as the scenario requires. `aces-pack-validate` parses that SDL through the
exactly pinned `aces-sdl` package; this package does not define a second behavior
shape or decide that an ACES behavior specification is complete.

The reference build, automated rehearsal, and participant walkthrough then
demonstrate that the live environment realizes the declared ACES behavior and
objectives. Explanatory `docs/attack-path.md` prose may describe the intended
route through the environment, but it is not system state or a machine-readable
contract. CTFd, operator debriefs, and agent-benchmark reports are consumers of
the same ACES-backed scenario and live evidence; none is a competing
specification.

The compatibility manifest retains `oracle_only` and the `oracle` export value
as release-boundary compatibility vocabulary. They classify restricted
non-participant material only and confer no scenario semantics. Participant
files must not expose restricted action ordering, raw evidence, answers,
credentials, flags, or next-step hints.

## Operating Profiles

ACES uses **delivery/audience bundles** for operating profiles:
`guided`, `unguided`, `purple-team`, `agent-benchmark`, and `demo`. These are
content overlays under `profiles/`; they are not runtime/provider profiles.
Selecting a bundle changes which participant, facilitator, defender, benchmark,
or presenter files are exposed. It does not change the hydrated ACES SDL,
topology, planted content, flags, reference tests, or golden proof.

The standard bundle responsibilities are:

- `guided`: staged objectives, progressive hints, teaching notes or facilitator
  pacing, and answer checks/checkpoints.
- `unguided`: terse mission brief, participant objectives, rules of engagement,
  and operator-only post-run reveal material.
- `purple-team`: defender injects, detection goals, expected alerts, blue-team
  tasks, and debrief prompts.
- `agent-benchmark`: deterministic task envelope, participant-safe objective
  contract, no-facilitator run metadata, and operator-only execution evidence.
- `demo`: shortened path, scripted reset reference, reduced-resource runtime
  compatibility, high-signal proof moments, and presenter script.

When a pack ships `profiles/`, `pack.yaml` sets `contents.profile_bundles: true`
and points at `profiles/bundles.yaml`; the pack carries the entrypoint files,
a `profiles/validate_*.py` gate, and `profiles/tests`. The compatibility
manifest mirrors the shipped bundle rows in `delivery_bundles` for catalog and
commercial consumers.

## Build, Release & Versioning

Packaging and release verification is the repo-wide, static/read-only gate
`aces-pack-release`, run in/behind the scenario-content gate. It lints
profile-support consistency (a `supported` delivery bundle must actually ship
its content, or the build fails fast), builds a boundary-split release tree
(`participant/`, `operator/`, `oracle/`, `commercial/`) with the participant
tier leak-scanned, smoke-tests that delivery-bundle selection changes
participant exposure, and emits a versioned `release.yaml` (pack version, the
scenario-pack contract version + digest from the bundled contract, supported
profiles, and a bounded provenance summary). A pack is releasable once it ships
a `pack.compatibility.yaml` with `artifact_boundaries`. Run
`aces-pack-release check --all` locally; see the bundled layout contract
(`contract/pack-layout.md`) for the full build/release section.
