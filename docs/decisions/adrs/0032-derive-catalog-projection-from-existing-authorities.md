# ADR 0032 — Derive one catalog projection from existing authorities

- Status: Accepted
- Date: 2026-07-30
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0010](0010-consume-aces-reusable-asset-trust-policy.md),
  [ADR 0012](0012-pack-content-identity-and-trust-boundary.md),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md),
  [ADR 0028](0028-project-raes-artifact-satisfaction-into-publication.md), and
  [ADR 0031](0031-compose-beginner-safe-pack-checks-from-existing-authorities.md)
- Coordination: OpenRAE/env-packs issue 188 and OpenRAE/hub issue 4

## Context

A static catalog needs a comparable machine record and a human card for every
environment pack. The record must combine descriptive pack facts, RAES scenario
facts, compatibility and release facts, provenance and safety, trust evidence,
rehearsal recency, and non-authoritative media. It must also aggregate records
from more than one repository without depending on a live service.

Those facts already have different authorities. Treating the card as an
independently authored manifest would duplicate them and allow it to contradict
the pack, RAES SDL, provenance ledger, compatibility manifest, publication
profile, or associated-artifact identity. Treating all requested fields as one
new pack schema would be worse: participant behavior, fidelity, and trust are
RAES-owned, while runtime compatibility, redistribution rights, publication
clearance, and observed rehearsal success are different kinds of claim.

The current code also has a security boundary that a catalog path must not
bypass. `validate_pack()` uses strict bounded YAML, packaged schemas, the pinned
RAES parser, and `_pack_fs.py`'s descriptor-anchored no-follow inventory. Some
additional relational checks still live only in trusted author CI, and
`release.py` reloads source contracts for its trusted author workflow. Reopening
an untrusted mutable tree after validation, importing author-CI helpers, or
running pack-local checks would make catalog generation unsafe and would create
another validation authority.

Finally, “stale” is relative to a policy and a point in time. Reading the wall
clock, Git timestamps, filesystem mtimes, repository order, or ambient
environment would make identical inputs produce different indexes.

## Decision

### The catalog is one derived read model

The catalog contract is a versioned, generated, pack-domain projection. It is
not an authoring authority, runtime contract, trust decision, or scenario
semantic model.

One normalized catalog entry is the only data model for both outputs:

- stable JSON index records serialize the normalized entry; and
- the local human preview renders that same entry.

The human card has no fields, defaults, filtering decisions, or state inference
of its own. A multi-entry catalog document is the static-host-friendly machine
carrier. A one-pack invocation produces the same carrier with one entry, so a
second standalone card schema and a second fact set are unnecessary.

The packaged JSON Schema follows the existing RAES schema conventions and is
closed and versioned with a string such as `environment-pack-catalog/v1`.
Generated JSON is validated against it before publication. The schema, semantic
relational checks, serializer, preview, examples, and compatibility tests are
one contract and move together.

No independently maintained `card.yaml`, `catalog.yaml`, index row, search
document, or Hub-specific metadata file is introduced. New authored input is
allowed only for a discovery fact that has no current authority. Such input
extends the existing descriptive `pack.yaml` metadata or the relevant
compatibility runtime row; it does not restate identity, SDL, provenance,
publication, or trust facts.

### Each field retains its authority

The projection composes these authorities without merging their meanings:

| Catalog concern | Authority and projection rule |
| --- | --- |
| Pack id, title, version, maturity, purpose, authors and pack-level limitations | `pack.yaml`, whose descriptive pack-domain metadata is validated by the shared static authority. |
| Intended audiences | Existing delivery-bundle declarations, with any general audience description kept as descriptive pack metadata. A consumer-specific Hub taxonomy is not copied into the pack contract. |
| Participant activity | Parsed RAES agents, action contracts, behavior specifications, objectives and other public RAES fields. The projection may summarize governed fields but must not infer activity from filenames, walkthrough prose, CTF categories, or local replacement enums. |
| Difficulty and participant/setup time | Explicit pack-domain estimates. Challenge-level difficulty is not averaged into pack difficulty, and RAES simulation clocks or objective windows are not participant-duration estimates. |
| Runtime, adapter, launch, resource and cost expectations | The compatibility manifest and, where applicable, the validated publication profile or trusted RAES backend profile. Estimates are scoped to a named profile and carry their basis; node counts and current cloud prices are not inferred. Provider and adapter ids remain references, not a new closed product vocabulary. |
| Fidelity | RAES action-contract and realization claims. The catalog does not mint an overall fidelity score or reinterpret RAES values. |
| License, redistribution and publication clearance | `pack.yaml` for the pack license and the provenance ledger for source licenses, distribution classes, safety attestations and review gates. Source licenses are not collapsed into a synthesized pack license. |
| Release identity and availability | The validated publication profile and RAES associated-artifact identities. Mutable availability remains outside immutable release identity. The catalog defines no new digest. |
| Integrity, authenticity and trust | Public models and validators from the exactly pinned RAES reusable-asset trust contracts. A content digest, provenance approval, golden status, or successful rehearsal is never upgraded into RAES trust evidence. |
| Last successful rehearsal | A structured, validated observation bound to the relevant pack release and runtime profile. A checklist, path named “rehearsal,” Git commit date, file mtime, or test command is not proof of success. Until suitable evidence exists, the projection says unknown or unverified. |
| Diagrams and media | References to validated, public-release-eligible associated artifacts. Media is presentation only and never overrides SDL, compatibility, provenance, trust, or rehearsal facts. |

Where the Hub contract chooses an outer source locator, pagination, hosting, or
transport shape, this package consumes that boundary rather than encoding Hub
product vocabulary into canonical pack terminology. The published catalog
record must nevertheless contain every fact Hub needs to render, inspect and
search a pack without reparsing pack YAML or RAES SDL.

### Absence, support and evidence are not one state

The projection represents state explicitly and uses field-specific state
vocabularies:

- `known` and `unknown` describe whether a discovery fact is available;
- `supported` and `unsupported` describe a declared capability for a particular
  profile; and
- `verified`, `unverified`, and `stale` describe evidence-backed observations.

`null`, an empty string, omission, `planned`, and a failed lookup are not
interchangeable substitutes for these states. `unknown` does not mean
unsupported. `unsupported` does not mean invalid. `unverified` does not mean
false. `stale` applies only to a previously verified observation under an
explicit freshness policy.

A state that carries a value and a state that forbids one are enforced
relationally by the same catalog validator; JSON Schema shape validation alone
is not treated as sufficient. Missing required discovery or trust declarations
produce stable actionable diagnostics even when the truthful projected state is
`unknown` or `unverified`.

Freshness uses an explicit caller-supplied `as_of` value and explicit rehearsal
age policy. The library never reads the current clock. Repeating a build with
the same staged bytes, source descriptors, target schema version, `as_of` value,
and freshness policy must produce byte-identical JSON.

### Projection consumes one safe validated snapshot

Catalog generation first passes every pack through the existing shared static
authority. It consumes the parsed, bounded snapshot produced by that pass:
canonical inventory, pack metadata, provenance, compatibility, publication
input when relevant, and parsed RAES scenarios. It does not validate a path and
then reopen the tree through a second loader.

The snapshot is an internal extension of `_validate_pack_core`, not another
public pack model. Relational joins needed by an untrusted catalog projection
move into the shared static authority and are removed from any author-only
duplicate. In particular, identity agreement, duplicate ids, referenced-member
containment and existence, and provenance source/artifact joins cannot remain
trusted-author-only if the projection relies on them.

The canonical incumbents remain:

- `PackValidationLimits`, `_StrictLoader`, `_check_yaml_events()`,
  `_trusted_schema()`, `_schema_violations()`, `_Errors`, `Diagnostic`, and
  `ValidationResult` for bounded static validation and diagnostics;
- `_pack_fs.open_root()`, `inventory()`, `open_member()`, and
  `read_member_bytes()` for every pack-controlled path and byte;
- `raes.parse_sdl()` / `parse_sdl_file()` and public `raes_contracts` models and
  validators for RAES-owned values;
- `validate_publication_document()` and its secret-bearing-location policy for
  publication facts;
- RAES associated-artifact validation for content and media identity; and
- the `raes-pack-check` presentation catalog, terminal escaping, JSON-only
  stdout discipline, and `0`/`1`/`2`/`3` process contract for actionable
  diagnostics.

Expected foreign-input defects join the existing bounded diagnostic surface; a
catalog-only exception hierarchy is not added. Diagnostics expose stable codes
and bounded pack-relative or field locations, never authored values, restricted
paths, file bodies, URLs with queries, credentials, raw RAES or Python exception
text, absolute paths, environment values, or command lines. Unexpected defects
remain tool failures and are not mislabeled as invalid packs.

Pack validity and catalog completeness remain separate verdicts. A truthful
`unknown` or `unverified` projection may carry a non-blocking completeness
diagnostic without making `validate_pack().ok` false. Severity is added through
the canonical diagnostic/result compatibility path anticipated by ADR 0031,
not through a catalog-only warning type or by changing the meaning of the
historical `errors` view.

The library path is silent, read-only and networkless. It does not import or
invoke author-CI execution, Git, pack-local validators or tests, cloud tooling,
backend probes, availability URLs, environment configuration, caches, or
databases. It does not read `.env` files. Repository acquisition,
authentication, authorization, immutable staging and hosting belong to the
caller or Hub.

### Aggregation is deterministic and collision-safe

Multi-repository aggregation consumes explicit source descriptors and already
staged local pack roots or validated catalog documents. A source descriptor has
a stable non-secret source id and immutable revision supplied by the caller. A
Git remote containing credentials, ambient checkout branch, current `HEAD`,
filesystem mtime, or repository basename is not an identity source.

Records have a deterministic composite key that includes the source identity,
pack identity and pack version. When RAES release or set identities exist they
are carried as evidence, not replaced by a catalog hash. Duplicate composite
keys, conflicting records for one immutable identity, unsafe source ids, and
ambiguous pack versions fail closed; input order never selects a winner.

Entries and every semantically unordered collection are sorted by documented
stable keys. JSON uses UTF-8, fixed separators/indentation, stable key ordering,
and one trailing newline. Aggregating the same inputs in another repository or
discovery order produces the same bytes.

Generated output is written only to an explicit contained destination through a
scratch artifact, validated, and atomically promoted. Output names are fixed or
derived only from validated safe slugs; untrusted source labels never become
unchecked paths. Generated files use fixed safe modes and do not inherit source
ownership, ACLs, extended attributes, set-id bits, or world-writable modes.
There is no catalog database or mutable cache.

### Static output remains safe to render and host

JSON serialization, not string interpolation, carries authored text. Human
terminal output reuses control-character escaping. HTML or Markdown previews
escape authored text and do not admit raw HTML, scriptable SVG, data URLs,
event-handler attributes, or active external embeds.

Media references must resolve through the safe pack inventory, be eligible for
the public/participant catalog boundary, satisfy provenance distribution
policy, and, when identity is claimed, be covered by the associated-artifact
manifest. The generator records a media reference and safe metadata; it does
not parse, execute, fetch, transcode, or trust the media as scenario meaning.
Hub applies its own content-serving and browser policy at the hosting boundary.

Catalog inputs and output carry no credentials, tokens, signed URLs,
secret-store coordinates, entitlement material, or environment-variable names.
Only local paths and non-secret selectors may appear in process arguments.
Outer authenticated acquisition keeps secrets out of argv and out of the
projection.

### Compatibility and extension seams are explicit

The catalog schema version is independent of the Python package version, pack
version, environment-pack layout-contract version, publication-profile version,
and RAES contract versions.

Because the schema is closed, changing field shape, requiredness, enum meaning,
state semantics, identity, or canonical ordering mints a new catalog schema
version. A package patch may fix implementation defects without changing the
same-version contract. Aggregation accepts one declared target version and
refuses a silent mixed-version merge. Supporting a later version is an explicit
projection adapter, not scattered conditionals in renderers.

The deliberate future-variation inputs are:

- target catalog schema version;
- stable source id and immutable source revision;
- explicit `as_of` and freshness thresholds; and
- Hub's chosen outer source/hosting boundary.

A new provider, adapter, runtime or media role extends validated source data and
projection mappings without adding product-specific enums to the pack. A new
RAES-owned semantic or trust field arrives through a reviewed exact-pin advance
and public upstream adapter, never through a copied schema or private RAES API.

## Consequences

- Authors maintain pack, RAES, provenance, compatibility, publication and
  evidence facts once; cards and indexes cannot drift from them.
- Hub and other clients can render, inspect and search using the published
  projection alone, while still treating referenced media as separate bytes.
- A catalog can truthfully publish incomplete packs because unknown,
  unsupported, unverified and stale are explicit, but incompleteness remains
  actionable in diagnostics.
- The trusted author CLI is not an ingest API. Catalog generation over foreign
  repositories stays inert and bounded.
- Synthetic fixture packs cover AI research, security, resilience/disaster
  recovery, product testing and simulator-backed scenarios without checking
  real packs into this repository. They vary authority combinations, not a new
  scenario-category enum.
- Compatibility tests must also cover hostile YAML, filesystem races and unsafe
  members, duplicate cross-repository identities, input-order independence,
  state/value invariants, secret-bearing locators, terminal/browser escaping,
  media-boundary eligibility, and byte-for-byte repeatability.

## Non-goals

This decision does not add a marketplace, rankings, payments, recommendations,
hosted execution, acquisition, authentication, authorization, a registry,
database, crawler, search engine, live backend discovery, cloud pricing lookup,
runtime health probe, launch or teardown, rehearsal execution, media processing,
or telemetry.

It does not host an environment pack, define a Hub product taxonomy, add a
generic adapter/plugin system, create a catalog trust score, infer pack quality
or difficulty, declare a runtime supported from a matching name, or treat
publication clearance, content identity, rehearsal success, and RAES trust as
equivalent. It does not define or extend RAES SDL, participant behavior,
fidelity, objectives, evidence, trust, realization, scoring, reward, telemetry,
or validation-oracle semantics.
