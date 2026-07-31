# Environment pack convention

**Environment-pack contract version:** `5`

This document is the authoritative layout convention every RAES environment pack
follows. It ships inside the `raes-env-packs` package alongside the schemas,
template, and tools that enforce it, so an author always validates against the
same contract version they build against.

Environment packs themselves live in their own catalog repositories: this package
**defines and validates** the format, it does not host packs. Everything below
describes the `environments/<name>/` layout an author creates in a catalog repo, and
`raes-pack-validate` / `raes-pack-release` check that layout against this
contract.

> First-pass rule of thumb: **put in what a scenario has, skip what it
> doesn't.** A pack is a declarative bundle plus one known-good reference — it
> is not an engine. When it ships a golden reference build, that build is a
> participant-equivalent runtime proof, not a scoreboard or productized range
> experience.

## What an environment pack is

An environment pack is **declarative content + the tooling that built and tested a
reference implementation + documentation.** A pack ships *source material and a
reference*; it does not ship an engine.

A consumer takes what it needs and **decomposes the pack into its own content
system** the way it builds ranges. The pack's job is to give a range builder
everything required to build and verify the scenario *their* way, with a
known-good reference to check against.

| DLC concept | Environment pack |
|---|---|
| The bundle you download | `environments/<name>/` |
| Game content (levels, assets, items) | SDL start state + bespoke assets + flags + challenges |
| "How to install / what it is" | docs: walkthroughs, concepts, lineage, diagrams, attack-path model |
| Reference build the studio ships | AWS golden build + tests + matching walkthrough |
| The engine | **Not in the pack.** The consumer's range system. |

## Layout

```
environments/<name>/
  pack.yaml       # identity + provenance metadata (name, version, authors, contents)
  pack.compatibility.yaml # optional product compatibility projection
  sdl/            # start state (+ injects/events/timeline)
  assets/         # bespoke files/content the scenario needs
  flags/          # flag values | generator | instructions, + placement.yaml
  challenges/     # CTF questions, hints, ratings — keyed by flag id
  ctfd/           # CTFd loader (reference)
  build/          # scripts to stand up the golden version in AWS
  tests/          # scripts to run all paths against the golden AWS range
  docs/
    walkthroughs/ # step-by-step, command-by-command — matches tests/
    concepts.md
    lineage.md
    attack-path.md
    provenance-ledger.yaml # REQUIRED source/licensing/safety/publication ledger
    diagrams/
  profiles/       # delivery/audience bundles (guided, unguided, purple, …)
```

A scaffold of this layout, with annotated placeholders, ships in the package
[`template/`](../template/); run `raes-new-pack <id>` to copy it into your
catalog and start a new pack.

### Pack metadata (`pack.yaml`)

**Required.** A small descriptive record at the pack root that says what the
pack is, who made it, what version it is, and which optional layers it ships.
This is *catalog/provenance* metadata, not a runtime contract — it pins nothing
about how a consumer builds or runs the pack (see
[not in scope](#explicitly-not-in-scope)). See [Placement map](#placement-map)
and [Challenges](#challenges) for the structured contracts; `pack.yaml` is just
the pack's identity. If you don't track packs against an upstream requirement id,
set `requirement: null` and cite the originating issue in the pack README or
lineage instead; never invent a requirement id.

```yaml
# pack.yaml
name: <name>                     # pack id; matches the directory name
title: "Human-readable title"
version: 0.1.0                    # pack version; bump when content changes
status: draft                    # draft | built | golden
description: "One line: what the scenario is and what the player does."
authors:
  - Name <email>                 # who authored it
license: "© 2026 Example Org. All rights reserved."
requirement: null                # optional upstream tracking id, or null
contents:                        # which optional layers ship; required ones are implicit
  flag_layer: false              # flags/ + challenges/ + ctfd/
  reference_triangle: false      # build/ + tests/ + docs/walkthroughs/
  profile_bundles: false         # profiles/ — delivery/audience bundles
# Optional; create and populate the RAES JSON before uncommenting (ADR 0012):
# associated_artifact_manifest: associated-artifacts.json
```

`status` tracks the pack's maturity: `draft` (SDL/design only), `built` (stands
up somewhere), `golden` (a participant-equivalent verified reference build +
passing tests).
`contents` declares which all-or-nothing optional groups are present, so the
pack self-describes what a consumer will find. `license` carries the pack's
terms so a consumer who takes a single pack à la carte sees them; it defaults to
the repository [`LICENSE`](../LICENSE) and need only be overridden if a pack
ships under different terms.

`pack.yaml` **must** point at `provenance_ledger: docs/provenance-ledger.yaml`
(the [provenance ledger](#provenance-ledger-docsprovenance-ledgeryaml) — the
required source/licensing/safety/publication contract), **may** point at
`compatibility_manifest: pack.compatibility.yaml`, and may opt into the RAES
content-identity boundary with
`associated_artifact_manifest: associated-artifacts.json`. The compatibility manifest is
the richer product compatibility projection validated by
[`pack-compatibility.schema.yaml`](../schemas/pack-compatibility.schema.yaml). It does not
replace SDL, topology, profile, build, or CTFd ledgers. It indexes them for
catalog and commercial-package consumers. It carries **zero extensions to RAES
semantics**: scoring, validation-oracle, telemetry, and lifecycle
(reset/rebuild/teardown) are RAES/runtime concerns and are not manifest layers
(ADR 0009).

### Compatibility manifest (`pack.compatibility.yaml`)

**Optional, but CI-enforced when referenced.** A pack uses
`pack.compatibility.yaml` when it needs a machine-checkable commercial/product
contract beyond identity metadata. The manifest must be static source metadata:
it cannot discover cloud state, call CTFd, run Terraform, emit telemetry, or
store mutable proof.

Keep the manifest to static, checkable metadata: it indexes the pack's other
ledgers for catalog and product consumers, it does not redefine or replace them.

The manifest defines:

- **Pack/source projection**: pack name, title, version, maturity status,
  requirement UID when one exists, GitHub issue provenance, and upstream
  references.
- **Runtime/provider profiles**: build/test/walkthrough references for runtime
  profiles such as `local_minimal`, `aws_minimal`, and `aws_full`. These are
  not delivery bundles.
- **Delivery/audience bundles**: guided, unguided, purple-team,
  agent-benchmark, demo, or custom content bundles. These may join to
  `profiles/bundles.yaml` when a pack ships a profile layer.
- **Platform features**: required, optional, planned, or not-shipped features
  such as real AD, Windows hosts, CTFd, C2/callback containment, cloud IAM, OT,
  IoMT, VPN/jump access, controlled egress, or SaaS facsimiles.
- **Artifact boundaries**: explicit participant/public, operator-only,
  oracle-only, commercial, private, and redistributable roots.
- **Assets and operator surfaces**: references to existing pack-local files and
  tools, not duplicated truth.
- **Validation**: commands and gates that prove the manifest, pack layout,
  visibility boundaries, profile bundles, tests, and rehearsal evidence.

Visibility is a contract, not just a directory name. Existing roots remain
valid equivalents:

| Compatibility boundary | Existing roots and equivalents |
|---|---|
| `participant_visible` / `public` | `assets/briefing/`, safe `assets/content/`, `profiles/_shared/`, `profiles/*/participant/`, or an explicit `public/` root |
| `operator_only` | `profiles/*/operator/`, `docs/` operator runbooks, `tests/`, `build/`, `ctfd/`, or an explicit `operator/` root |
| `oracle_only` / `private` | Restricted non-participant rehearsal evidence, answer material, operator diagnostics, or a legacy explicit `oracle/` root. These are release-boundary labels only, not scenario semantics. |
| `commercial` | bundled content a commercial catalog may ship to licensed operators, commonly `profiles/`, `build/`, `tests/`, `ctfd/`, docs, or an explicit commercial export root |

If a pack introduces literal `public/`, `operator/`, or `oracle/` directories,
map them in `pack.compatibility.yaml` before content relies on them. Participant-visible roots are still covered by the repo-wide
leak scan; operator/oracle/private roots may contain restricted action ordering,
answers, credentials, raw evidence, and reset internals.

Boundary declarations must prevent restricted content from entering a
participant export structurally. Every `participant_visible` path (normally
`export: public`) must be disjoint from every path selected by `operator_only`,
`oracle_only`, or an `operator`, `oracle`, or `private` export. Equal paths and
containment in either ancestor/descendant direction are invalid. Validation and
release reject the declaration before staging; the participant leak scan is a
separate defense-in-depth check for unsafe content inside an otherwise valid
participant root.

### Provenance ledger (`docs/provenance-ledger.yaml`)

**Required.** Every pack ships a machine-readable provenance ledger and
references it from `pack.yaml` (`provenance_ledger: docs/provenance-ledger.yaml`);
the `raes-pack-validate` gate enforces its
presence and validates it against
[`provenance.schema.yaml`](../schemas/provenance.schema.yaml). It is the source of truth for
**where content came from, what may be done with it, whether it is safe to ship,
and whether it has been cleared to publish.** `docs/lineage.md` stays human prose
and cites the ledger. A worked example is
[`template/docs/provenance-ledger.example.yaml`](../template/docs/provenance-ledger.example.yaml).

The provenance schema is enforced for every pack: it is the content-safety and
publication-review gate, and pack exports carry it rather than bypassing it.

#### RAES trust authority (ADR 0010)

An environment pack is a `reusable_scenario` asset in RAES's own trust vocabulary.
**RAES core is the authority for pack integrity and authenticity**, via the
reusable-asset trust policy (`reusable-asset-trust-policy/v1`, `$id`
`https://raes.dev/schemas/reusable-asset-trust-policy-v1.json`; RAES ADR-071).
That policy owns the `integrity_digest`, `authenticity_signature`,
`provenance_lock_record`, `governance_source`, and `artifact_checksum` evidence
classes and their enforcement levels. Per
[ADR 0021](../../../docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md),
this ledger **consumes** that policy as the authority and **re-defines none of
it**: a pack's cryptographic integrity/authenticity and its composed-module
(SDL) dependency provenance are established by RAES mechanisms
(scenario-snapshot digest binding, `raes.lock.json` digest pins, RegistryTrustPolicy
signatures), not here. RAES schemas are `stability: draft` today, so the ledger
references the policy now and the explicit upstream version pin (dependency +
compatibility tests) lands once RAES marks it stable.

The ledger is scoped to pack-domain facts RAES does **not** define. Every field
has one documented status:

| Ledger field | Status |
|---|---|
| `pack`, `schema_version` | Pack-domain: ledger identity and version. |
| `sources[]` (`license` / `usage` / `attribution` / `used` / `excluded`) | Pack-domain: content-origin licensing and attribution of external, non-RAES material. Distinct from the RAES `provenance_lock_record` evidence class (digest-pinning of composed RAES modules via `raes.lock.json`), which stays with RAES. |
| `artifacts[].classification` (`open` … `customer-specific`) | Pack-domain: distribution / redistribution rights — **not** an RAES trust enforcement level. |
| `content_safety{}` | Pack-domain: content-safety exclusion attestations; RAES defines no content-safety evidence class. |
| `review{}` | Pack-domain: publication-clearance gates; not RAES `governance_source`. |
| `overlays[]` | Pack-domain: customer-overlay distribution containment. |
| `integrity_digest`, `authenticity_signature`, `provenance_lock_record`, `governance_source`, `artifact_checksum` | **RAES-owned → deferred to RAES.** The ledger neither carries nor re-defines them. |

If a pack needs trust expressivity the RAES policy lacks, that gap is raised
**upstream in RAES**, never worked around with a pack-side extension.

#### Concept-authority alignment (ADR 0014)

RAES also owns the governed **concept** vocabulary — ATT&CK and ATLAS
offensive-behaviour tactics, UCO concept families, and the controlled
vocabularies — published under `contracts/concept-authority/`. Those
classifications have one semantic home: RAES SDL behaviour specifications
(`behavior_specifications.offensive_behavior_refs` /
`ai_offensive_behavior_refs`), validated by the pinned `raes.parse_sdl`. The
pack format consumes them and restates none of them. Two former local overlaps
are removed: the provenance ledger carries no `sources[].kind`, and the canonical
challenge contract carries no `challenges[].category` (see
[Challenges](#challenges)). The remaining local vocabulary — source licensing /
attribution / usage, artifact distribution classes, content-safety exclusions,
publication-review gates, overlay containment, and challenge display text — is
genuinely pack-domain packaging vocabulary, not an RAES concept surface. See
[ADR 0021](../../../docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md).

The ledger has four parts:

- **`sources[]`** — every upstream corpus, framework, tool, dataset, research
  report, original design, generated material, or customer overlay as a
  first-class row with a stable `source_id`, `license`, `usage`,
  `attribution_required` (+ `attribution` text when true), and what was `used` /
  `excluded`. Covers MITRE CTID, AEL, ATT&CK, Atomic Red Team, CALDERA,
  scenario-specific research, original design, and generated material. A row
  records only content origin, licensing, attribution, and usage; it carries no
  `kind` (or other) concept classification — governed ATT&CK/ATLAS/UCO concept
  vocabulary lives in RAES concept-authority and RAES SDL, not here (ADR 0014).
- **`artifacts[]`** — pack-relative roots classified for **distribution**:
  `open`, `redistributable`, `internal-only`, `commercial-only`, `generated`,
  or `customer-specific`. This is the "open vs RAES-only" axis and is
  **separate** from the compatibility manifest's runtime-visibility export
  values (`public`/`operator`/`oracle`/`private`/`commercial`): one says what may
  be published or sold, the other says who sees it at runtime. Artifact rows may
  cite `source_id`s.
- **`content_safety{}`** — the hard boundary, attested as data:
  `no_real_malware`, `no_real_third_party_targets`, `no_real_credentials`,
  `no_sensitive_data`, `offensive_tooling_boundary`. CI requires **all true** —
  the policy is exclusion of real sensitive content, never a weaker class.
- **`review{}`** — publication review modelled as data, not a comment: a
  per-gate checklist covering at least `licensing`, `attribution`,
  `sensitive-data`, and `offensive-tooling` (optionally `customer-overlay`), each
  `pending`/`approved`/`blocked`.

**Customer overlays.** A private customer overlay declares an `overlays[]` slot
with a path-contained `root`; its content is classified `customer-specific` and
lives only under that root. CI enforces that overlay roots never overlap base
artifact roots, so an overlay can be removed without contaminating the base
pack's source, licensing, or redistributability claims — and a base export never
includes customer-specific material.

### Validity and RAES participant behavior

The hydrated RAES SDL is the scenario specification. A pack declares the
attacker through RAES `agents` and `behavior_specifications`, binds governed
actions through `action_contracts`, and uses RAES preconditions, effects,
failure classes, observation boundaries, outcome interpretation rules,
objectives, evidence requirements, and workflows as needed. The pinned
`raes` parser is the semantic authority; this package defines no parallel
behavior, route, reachability, or validity schema.

Pack-local `docs/attack-path.md` remains required explanatory design prose. It
may describe an intended route through the environment, but it is not
machine-readable system state and does not override the hydrated SDL. Reference
tests and walkthroughs demonstrate that the live golden build realizes the
declared RAES behavior and objectives from the participant surface; static parse
success alone is not runtime proof.

Restricted non-participant material must stay separate from participant-visible
content. A participant or agent-benchmark export may expose stable RAES
objective ids and participant-safe summaries, but never restricted action
ordering, raw evidence, answers, credentials, flags, or next-step hints. The
`oracle_only` group and `oracle` export value remain compatibility labels for
that release boundary only; they do not confer semantic authority. CTFd remains
a consumer of the RAES-backed scenario and live proof, not a competing spec.

### A. Start state & content (declarative)

- **`sdl/`** — the scenario start state, plus injects / events / timeline if it
  has them. [RAES SDL][raes] is the authoring format. This is the one
  section every pack has (see [Required vs optional](#required-vs-optional)).
- **`assets/`** — the bespoke files and content the scenario needs: container
  definitions, custom binaries, documents planted on hosts, site content, decks
  and handouts. Anything custom-authored that the start state references lives
  here.

### B. Flags & challenge layer (declarative + the reference loader)

- **`flags/`** — flag **values**, or a **value generator**, or **instructions**
  to produce them, plus the **placement map** (`flags/placement.yaml`) that says
  exactly where each flag goes. See [Placement map](#placement-map).
- **`challenges/`** — the CTF question, hints, and rating (difficulty / points)
  for each flag, keyed by flag id. See [Challenges](#challenges).
- **`ctfd/`** — the reference CTFd loader.

The flag layer is a coupled group: a pack either has flags-and-challenges or it
doesn't (a pure-emulation scenario may have neither).

### C. Reference build & test tooling (the only imperative part)

- **`build/`** — scripts that stand up the **golden version in AWS**. This is
  the reference build a range builder decomposes into their own content system.
- **`tests/`** — scripts that run every path against the **live golden AWS
  range** and confirm each flag. The tests target the golden range, not an
  abstraction.

### D. Documentation & understanding

- **`docs/walkthroughs/`** — step-by-step, command-by-command walkthroughs that
  **match the test paths** (same commands, same expected output, same flag), so
  the walkthrough is the human-readable form of the reference tests.
- **`docs/concepts.md`** — the concepts the scenario involves.
- **`docs/lineage.md`** — where the content and ideas came from.
- **`docs/attack-path.md`** — the attack-path model that makes the scenario
  understandable.
- **`docs/diagrams/`** — technical diagrams.

### E. Delivery profiles (optional)

- **`profiles/`** — the same environment packaged for different **audiences**:
  guided and unguided participant runs, a purple-team facilitation set, an
  agent-benchmark contract, a demo/presenter path, and so on. A delivery
  profile is a *content bundle*, **not** a runtime topology profile — it never
  redefines how a consumer builds or sizes the range. The structured selection
  contract is `profiles/bundles.yaml` (the canonical manifest), and `pack.yaml`
  carries `contents.profile_bundles: true` plus a thin `profile_bundles:` index
  pointing at it, so a consumer can select a bundle à la carte from the
  manifest.

  Bundles factor shared participant-safe content once (e.g. `profiles/_shared/`)
  and add explicit per-bundle overlays. They keep the
  [visibility boundary](#how-a-consumer-uses-a-pack): participant-facing files
  live under `profiles/<bundle>/participant/` (and `profiles/_shared/`) and are
  leak-scanned exactly like `assets/briefing/`; operator/facilitator-only files
  live under `profiles/<bundle>/operator/` and may cite restricted execution
  evidence. A
  pack ships this layer with a static `profiles/validate_*.py` gate, the same
  way the SDL ledgers ship their validators.

  The standard RAES delivery bundles are:

  | Bundle id | Required artifacts | Optional artifacts | Exposure rule |
  |---|---|---|---|
  | `guided` | Staged objectives, progressive hints, teaching notes or facilitator pacing, and answer checks/checkpoints. | Facilitator prompts, room pacing variants, remediation notes. | Participant files may teach method but must not reveal restricted action ordering, answers, or raw evidence. Facilitator notes are operator-only. |
  | `unguided` | Terse mission brief, participant objectives, and rules of engagement. | Post-run reveal, debrief notes, rubric summary. | Participant files contain no next-step hints or staged solution order. Operator calibration stays operator-only unless expressed as participant-safe objective text. |
  | `purple-team` | Defender injects, detection goals, expected alert references, blue-team tasks, and debrief prompts. | Timeline variants, SIEM query examples, after-action worksheet. | Defender/operator material may reference expected alerts and detections, but any red-team handout remains separate and leak-scanned. |
  | `agent-benchmark` | Deterministic task envelope, participant-safe objective contract, and no-facilitator run metadata. | Allowed assumptions, timeout/resource policy, replay metadata, result schema. | The agent-facing contract is participant-safe. Joins from public objective ids to raw execution evidence or answers are operator-only. |
  | `demo` | Shortened route description, reduced-resource runtime compatibility, high-signal proof moments, and presenter script. | Fallback script, timing notes, preflight checklist, cleanup note. | A demo may constrain exposed milestones or compatible runtime profiles, but it reuses the existing RAES specification and build/test contracts and never creates a second behavior spec. |

  Profile selection changes **content exposure only**. It does not fork the
  hydrated RAES SDL, scenario topology, planted content, flags, or golden proof.
  A shortened demo can expose fewer beats, and an agent benchmark can expose a
  deterministic task envelope, but both still point back to the same base
  scenario contract.

  A pack that ships this layer authors, at minimum:

  - `pack.yaml` with `contents.profile_bundles: true` and a thin
    `profile_bundles:` index pointing at `profiles/bundles.yaml`.
  - `profiles/bundles.yaml` with one row per shipped bundle, using stable
    bundle ids, audience, compatible `runtime_profiles`, shared includes,
    participant entrypoints, operator entrypoints, and any benchmark objective
    join paths.
  - The entrypoint files named by the manifest, placed under
    `profiles/_shared/`, `profiles/<bundle>/participant/`, or
    `profiles/<bundle>/operator/` according to the exposure rule.
  - A pack-local `profiles/validate_*.py` gate and `profiles/tests` suite that
    validates the manifest, pack index, runtime-profile joins,
    participant/operator split, leak scan, and any objective/evidence joins.
  - When the pack has a compatibility projection, matching
    `pack.compatibility.yaml.delivery_bundles` rows with pack-local manifest,
    participant path, operator path, and validation references.

## The reference triangle (build → test → walkthrough)

`build/`, `tests/`, and `docs/walkthroughs/` are one coherent reference, all
pointed at the same **golden AWS range**:

1. `build/` stands the golden up in AWS.
2. `tests/` runs every path against that live golden range and confirms each
   flag.
3. `docs/walkthroughs/` is the command-by-command human version of those same
   paths.

A range builder gets a known-good build, automated verification of it, and a
matching walkthrough — so when they decompose the pack into their own range
system, they have a reference to validate against path-by-path. AWS is assumed
for both the golden build and its tests.

### Participant-equivalent golden ranges

`golden` is a stronger claim than "the operator can prove it with management
access." A golden reference build must stand up from the declared golden build
profile into the participant start state and then be completable from a
participant-accessible execution surface.

That means:

- The golden build itself creates or seeds every required host, identity,
  domain join, service, share, route, tool, artifact, credential, flag, and
  objective state. Rehearsal scripts may verify and observe; they must not be
  the only thing that makes the range playable.
- The documented happy path starts from something a participant can actually
  use: an attacker host, browser terminal, seeded foothold, VPN-accessible jump
  box, or equivalent role-appropriate surface.
- The path is proven without cloud-console actions, SSM/RunCommand shells,
  Terraform outputs, generated passwords, root shells, database consoles, or
  other management-plane shortcuts. Those are acceptable only for provisioning,
  reset, observation, teardown, and operator diagnostics.
- All credentials or derivation steps required by the attack path are present
  in-world as synthetic scenario content. If lateral movement, privilege
  escalation, collection, or exfiltration requires a secret, the participant can
  discover or derive it from the range itself.
- The proof exercises the intended privilege context. A SYSTEM/root/operator
  shell is not evidence that a user-level foothold is playable.

`golden` does **not** require a consumer-grade portal, scoreboard, scoring
engine, class-management UI, or telemetry product. Those remain runtime concerns
owned by consuming ranges. It **does** require that a human can run the
walkthrough command by command from the participant surface and complete the
scenario in the intended role.

### Golden definition of done

Every environment pack that claims `golden` must carry a concrete checklist at
`docs/golden-readiness-checklist.md`. The checklist is deliberately written with
unchecked `- [ ]` boxes so the final reviewer can copy it into an issue, PR, or
rehearsal report and mark what was actually proven in that run.

The checklist must cover, at minimum:

- [ ] The range applies from a clean checkout using committed pack content.
- [ ] No hidden repo-root `.env`, external file fetch, or undocumented manual
      setup is required, except approved cloud/operator credentials.
- [ ] The declared golden build profile creates the participant start state.
- [ ] The participant entry surface exists, is documented, and is reachable.
- [ ] The full happy path is executed manually from the participant surface,
      command by command.
- [ ] Operator channels such as SSM, Terraform, cloud consoles, generated
      passwords, root/SYSTEM shells, and database consoles are used only for
      provisioning, diagnostics, reset, observation, or teardown.
- [ ] Every required RAES objective, flag, and success condition is reached
      from the intended participant privilege context.
- [ ] Negative gates prove objectives/flags are not trivially reachable before
      the required action or privilege.
- [ ] Reset, persistence, survival, or cleanup behavior works where claimed.
- [ ] Automated rehearsal passes against the same golden build profile.
- [ ] The human walkthrough and automated rehearsal exercise the same declared
      RAES behavior and objectives.
- [ ] Durable evidence is committed as a rehearsal report.
- [ ] Teardown is run and verified; no live range resources remain.
- [ ] `pack.yaml.status: golden` is set only after the above proof exists.

### Scenario milestone structure

A new scenario milestone should be structured so the work naturally reaches the
definition of done instead of relying on reviewer memory. Unless a scenario is
explicitly smaller, create or track issues for these slices:

- [ ] Scenario contract and pack skeleton.
- [ ] Topology, assets, and reference-triangle design.
- [ ] Attacker behavior specified in RAES participant semantics.
- [ ] Flag, challenge, and reference CTFd layer, when the scenario has flags.
- [ ] Delivery profile bundles, when the scenario has multiple audiences.
- [ ] Golden build implementation in the declared live infrastructure.
- [ ] Automated live rehearsal for the golden build.
- [ ] Final manual participant walkthrough.
- [ ] Final docs, status, evidence, and teardown reconciliation.

The **final manual participant walkthrough** is its own slice. It is not
subsumed by "tests passed" or "Terraform applied." That slice stands up the
range, enters through the participant surface, works the happy path by hand,
fixes every discovered defect, re-runs the affected manual step, runs automated
rehearsal, tears down, and records exactly what was proven.

## How a consumer uses a pack

À la carte. A consumer takes what it needs — the SDL as a start-state seed, the
assets, the flags + placement, the challenge text — and **bakes it its own
way**. The `build/`, `tests/`, and `ctfd/` are *the reference* — used as-is,
adapted, or discarded. Nothing in the pack presumes how the consumer runs it.

## Required vs optional

A pack puts in what the scenario has. The sections divide into three tiers:

| Tier | Sections | Rule |
|---|---|---|
| **Required** | `pack.yaml`, `sdl/`, `docs/concepts.md`, `docs/attack-path.md` | Every pack. A pack with no identity, no start state, and no way to understand it is not a pack. |
| **Required-if-present** | the flag layer (`flags/` + `challenges/` + `ctfd/`); the reference triangle (`build/` + `tests/` + `docs/walkthroughs/`) | Each group is all-or-nothing. If a pack ships flags it ships their placement and challenge text; if it ships a golden build it ships the tests and the matching walkthrough. |
| **Optional** | `assets/`, `docs/lineage.md`, `docs/diagrams/`, `profiles/`, `pack.compatibility.yaml` | Include when the scenario has them. `profiles/` (delivery bundles) ships its own `profiles/bundles.yaml` manifest + `validate_*.py` gate when present. `pack.compatibility.yaml` is validated when `pack.yaml` references it. |

The **minimum complete pack** is therefore `pack.yaml` + `sdl/` +
`docs/concepts.md` + `docs/attack-path.md`. A pure-emulation scenario with no objectives is complete
without the flag layer; a paper design not yet built is complete without the
reference triangle.

## Placement map

`flags/placement.yaml` is the one structured contract between flags and assets:
it says where every flag value lands. It is a list of entries keyed by a stable
`flag_id` that the [challenges](#challenges) file reuses.

```yaml
# flags/placement.yaml
flags:
  - flag_id: boreas-mail-creds        # stable id; the join key across the pack
    source: value                     # value | generator | instructions
    value: "PEN{exfil_the_mailbox}"   # present when source: value
    host: boreas-mail                 # an asset / host in the SDL start state
    path: /var/mail/j.frost           # where the value lands on that host
    note: planted in the draft folder # optional human note

  - flag_id: scada-override
    source: generator                 # value produced at build time
    generator: build/gen-override.py  # script, relative to the pack root
    host: brain-controller
    path: /opt/brain/override.code

  - flag_id: gitea-deleted-schematic
    source: instructions              # no shippable value; how to produce it
    instructions: docs/walkthroughs/a7-gitea.md#restore-the-schematic
    host: boreas-intranet
    path: /data/git/acme/schematic.kicad
```

Rules:

- **One entry per flag**, keyed by `flag_id`. The id is the join key to
  `challenges/` and to the walkthroughs.
- **`source` is one of `value` / `generator` / `instructions`.** Exactly one of
  `value` / `generator` / `instructions` is populated to match.
- **`host` names an asset** that exists in the SDL start state; **`path`** is
  where the value lands on it. Together they are the "flag X goes at host/path
  Y" contract.

## Challenges

`challenges/challenges.yaml` holds the player-facing CTF text for each flag,
keyed by the same `flag_id` as the placement map. One entry per flag.

```yaml
# challenges/challenges.yaml
challenges:
  - flag_id: boreas-mail-creds        # joins to flags/placement.yaml
    title: "Mind the Mailbox"
    difficulty: easy                  # easy | medium | hard | insane
    points: 100
    question: "Frost left himself a note. What does PEN{...} say?"
    hints:                            # ordered; cost is the loader's concern
      - "Dovecot keeps drafts on disk."
      - "Look under /var/mail."
```

Keep the contract minimal and let the loader own presentation: `ctfd/` maps
these fields onto CTFd's own challenge / hint / scoring model. Challenge grouping
such as a CTFd *category* is adapter-local presentation, not part of the
canonical challenge contract: define it in the loader's own configuration. It is
never promoted to an ATT&CK/ATLAS classification or copied back into the pack
challenge shape — governed tactic/technique classification lives in RAES SDL, not
a pack field ([ADR 0021](../../../docs/decisions/adrs/0021-adopt-raes-environment-pack-identity.md)).
Long prose hints or per-flag write-ups may live in their own files under
`challenges/` and be referenced from the entry; the YAML index stays the
canonical list.

## Build, release & versioning

A pack is packaged for release by the repo-wide, **static and read-only** gate
the `raes-pack-release` gate. It derives release
views from the contracts above — it never stands up a range, calls a cloud/CTFd/
Terraform/Docker API, mutates state, or uploads. It runs in or behind the
existing environment-pack-content gate (`raes-pack-validate`); a pack is
**releasable** when it ships a `pack.compatibility.yaml` with
`artifact_boundaries`. Packs without a compatibility manifest are explicit
skips, never a silent partial release.

- **Lint (fail fast).** A pack must not advertise a delivery bundle it does not
  ship. Every `pack.compatibility.yaml.delivery_bundles[].status: supported` row
  must agree with `pack.yaml.contents.profile_bundles`, the `pack.yaml`
  `profile_bundles:` index, and `profiles/bundles.yaml` — bundle id present and
  every shared/participant/operator entrypoint and validation reference present
  on disk. `planned` / `not_shipped` rows are honest metadata and need no shipped
  content; they are never packaged as supported.
- **Build (boundary split).** Each `artifact_boundaries` group is staged into its
  own release root — `participant/`, `operator/`, `restricted/`, `commercial/` —
  so participant-visible, operator-only, and restricted non-participant material
  are physically separated. The authored `oracle_only` label maps to the
  `restricted` release view through the single `BOUNDARY_TIERS` seam and gains no
  scenario or validation-oracle meaning from that label. Participant and restricted non-participant roots must pass the
  disjointness rule above before any copy starts. Every member is read through a
  **root-anchored, no-follow descriptor**, so the safety decision and the copy are
  the same file object and a path component cannot be swapped for a symlink
  between them; `..`, absolute paths, symlinks, hardlinks, and special files all
  fail closed. Staged files are written with a fixed safe mode rather than
  inheriting the source's ownership, ACLs, extended attributes, or set-id bits.
  The operator-token leak scan is re-run over the staged participant tier so
  no restricted operator vocabulary reaches a participant artifact.
- **Profile smoke.** Delivery-bundle selection must change participant exposure:
  each supported bundle's participant view (`_shared/` includes + its
  `participant/` entrypoints) is assembled and the views are proven non-identical
  across bundles, with operator entrypoints never resolving under a participant
  root.
- **Publication profile.** `build` emits `release.yaml` as a schema-backed
  `environment-pack-publication/v1` document — a consumer contract, not an
  informational summary — and validates it before promotion. Its `release` block
  is the immutable identity: pack id/version, the RAES semantic parent, the
  validated associated-artifact set, and the participant/operator/restricted/
  commercial views. Its `summary` block carries the descriptive release facts
  (the **environment-pack contract version** above plus a `sha256` digest of this
  file, supported delivery profiles, compatible runtime profiles, and a bounded
  provenance summary — counts and review-gate statuses only, never source/review
  prose or restricted operator vocabulary). Its `distribution` block carries the
  mutable provider/location availability and channel records and is deliberately
  outside identity, so distribution can evolve without re-identifying an
  unchanged release. `pack.yaml.version` is the pack release version — CI
  numbers, timestamps, and git SHAs are build provenance, not semantic versions.

  A published release is immutable: rebuilding the same version with different
  bound identities is refused, and only an identity-equivalent rebuild is
  idempotent.

See the [publication profile](#publication-profile) section below.

Run it locally exactly as CI does:

```
raes-pack-release check --all          # lint + smoke + build-to-tempdir
raes-pack-release build --pack <pack> --out dist/
raes-pack-release metadata --pack <pack>
```

## Publication profile

The publication profile turns one validated pack release into distributable,
verifiable release views. It **consumes** the RAES artifact-requirement contract
(RAES ADR-098, `artifact-requirement-v1`) and defines no RAES semantics: author
posture, mechanism vocabulary, acquisition, timing, permitted routes, and trust
references are RAES-owned and read from the exactly pinned `raes` release. See
[ADR 0028](../../../docs/decisions/adrs/0028-project-raes-artifact-satisfaction-into-publication.md).

Publication is a **claim about release assets**, never an override of author
intent. The gate joins every claim back to the requirement RAES parsed from the
pack's `sdl/`:

- an **exact** requirement may reference only its exact immutable artifact. It is
  never relabeled a candidate or locked input, and never published under another
  digest;
- a **constrained** requirement may advertise zero or more of its *declared*
  candidates, locked inputs, or explicitly permitted materialization
  specifications. The advertised set is never exhaustive;
- an **open** requirement may reference an applicable backend capability with no
  published artifact, candidate, or recipe; and
- a requirement may be published with **nothing at all**. Absence is not an
  unsatisfied, exhaustive-alternatives, or pull-at-runtime claim.

A pack declares what a release supplies through an optional `pack.yaml` pointer:

```yaml
publication_supply: publication-supply.yaml
```

The file lists `publications`, `capability_claims`, `availability`, and
`channels`. Derivation cannot invent which permitted assets an author chose to
ship, so those rows are authored; everything else in the profile — view
structure, identity binding, and contract facts — is derived by the release tool.
Any publication or capability claim requires the pack to have opted into content
identity (`associated_artifact_manifest`), because a claim is only meaningful
against bound, verifiable bytes.

Backend-native or dynamic satisfaction is claimed by capability reference. A bare
backend-profile name is not evidence of mechanism support: a concrete, validated
RAES `ArtifactMechanismCapability` is required.

Redistribution rights, origin access, and runtime exposure remain three
independent axes. Public and authenticated/private origins use the same
availability record shape. Credentials, tokens, signed-URL values, secret-store
coordinates, entitlement, and environment-variable names are **not** publication
content and are rejected. The release tool never fetches an availability
location, resolves a channel, contacts a backend, or executes a specification.

## Pack content identity

Pack content identity consumes the RAES
`associated-artifact-manifest-v1` contract (RAES ADR-077); this repository does
not define another digest framing or checksum model. A pack opting in declares a
contained JSON pointer in `pack.yaml`:

```yaml
associated_artifact_manifest: associated-artifacts.json
```

The manifest uses `scope: scenario`, parent id equal to the pack name, logical id
`<pack-name>-associated-artifacts`, and manifest version equal to the pack
version. Its artifact ids are opaque RAES ids. Each payload locator uses
`raes-environment-pack:/<percent-encoded-root-relative-path>`, which is resolved only
inside the opened pack root and never fetched as a network URI.

The manifest carrier and exact `sdl/.raes/module-cache/` resolver cache are not
payloads. Every other regular file must be represented by at least one locator,
and every locator must resolve to an inventoried file. Scenario-pack payload
checksums use SHA-256. RAES derives the canonical set digest and validates the
concrete SDL parent, descriptor set, checksum, size, and byte reader for every
entry.

The package exposes authoring derivation and consumer validation separately:

```python
from raes_env_packs import (
    derive_pack_content_manifest,
    pack_content_digest,
    validate_pack_content_manifest,
    verify_pack_content_digest,
)

derived = derive_pack_content_manifest(pack_root)
declared = validate_pack_content_manifest(pack_root)
digest = pack_content_digest(pack_root)
verify_pack_content_digest(pack_root, expected_digest)
```

This is an **associated set identity, not scenario identity or trust**. Per
[ADR 0012](../../../docs/decisions/adrs/0012-pack-content-identity-and-trust-boundary.md)
RAES owns the model, canonicalization, byte binding, diagnostics, and reusable
asset trust mapping. This repository owns pack layout, safe pack-local
materialization, and inventory completeness. The set digest is distinct from the
SDL semantic digest, the `release.yaml` contract digest above, and SDL lock
digests; none proves authenticity by itself.

Callers must use an immutable staging area. Descriptor-anchored no-follow reads
and before/after inventory checks fail closed during the operation, but a live
directory walk is not atomic storage. Acquisition, atomic promotion, retention,
permissions, and use-time verification remain consumer responsibilities.

## Explicitly not in scope

To keep packs declarative and consumer-agnostic, a pack is **not** any of: a
runtime/engine, a "generator" abstraction, a capability-negotiation or adapter
API, a dependency **lockfile** or runtime contract a consumer must satisfy, a
scoreboard, a range portal, class-management UX, or an emitted
telemetry/observability contract. Those are runtime concerns owned by whatever
consumes the pack — not the pack. The golden reference build is the one runtime
proof the pack ships, and it must be participant-equivalent as defined above.

The descriptive `pack.yaml` and the validated compatibility projection are not
runtime engines. `pack.yaml` records what the pack *is* for the catalog and for
humans. `pack.compatibility.yaml` tells a consumer what the pack exposes and
requires, but it still does not build, resolve, score, observe, or run the pack.

[raes]: https://github.com/OpenRAE/rae
