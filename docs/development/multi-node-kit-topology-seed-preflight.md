# Kit topology and seed-content guardrails (#416)

This is a content correction within existing RAES and kit contracts. No new
schema, service, resolver, or ADR is needed.
[ADR 0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md)
governs composition and safe materialization;
[ADR 0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
places first-party releases here while RAES owns semantics.

## Acceptance scope and release boundary

Before this change, the checkout had 46 kit families and 90 releases. The
newest Wazuh, TheHive, Shuffle, and observability/evidence-store modules each
contain several compute nodes but no `infrastructure` or `relationships`. All
46 newest modules have a `seed_inventory` dataset without `text` or `source`,
covering 179 named items.
The seed gap therefore extends beyond the four topology examples.

The issue says **each seed dataset**. Unless the issue owner narrows that
criterion, apply it across current kit families, including single-node kits;
apply topology coverage to every current multi-node kit. Do not quietly define
the examples as an exhaustive seed-content scope. Historical releases remain
available and byte-identical: corrections belong in independently versioned
successors, following the SMTP/IMAP `1.2.0` precedent. Select a free successor
version per family rather than assuming every family is at `1.1.0`.

Preserve each predecessor's unrelated contracts, especially the open Linux
compute-substrate posture from #413, Windows substrate requirements, runtime
parameter fixes from #414, exported identities, and asset visibility. Package
version and `CHANGELOG.md` remain release-please-owned. Packs and walkthroughs
pinned to older releases do not migrate automatically.

## Semantic authority and topology

The exact `raes==7.0.0` pin in `pyproject.toml` is the authority. Put authored
nodes, topology, relationships, content, parameters, and exports in
`module.sdl.yaml`. Keep `kit.yaml` a closed pack-domain carrier. Reuse public
RAES parsing, descriptor, composition, and lock APIs already used by
`src/raes_env_packs/kits.py`; add no local SDL model or composer.
Existing examples in `packs/techvault/sdl/techvault.sdl.yaml`, its participant-
study variant, and `packs/ai-escape-lab/sdl/ai-escape-lab.sdl.yaml` already use
switches and infrastructure links. Reuse that RAES shape, not their scenario-
specific addresses or runtime configuration. TechVault also demonstrates
infrastructure dependency ordering for Wazuh, TheHive and Shuffle.

Use RAES switch nodes and `infrastructure.<node>.links` for network membership.
A shared module-local switch is sufficient for these small stacks when it
matches their intended topology; do not make it a universal one-switch rule.
Link targets need infrastructure entries too, including the switch itself.
Export infrastructure keys consistently with their exported nodes. A synthetic
public-parser probe against the pinned package confirmed that private
infrastructure keys with public node keys fail after namespacing; a switch node
without its infrastructure entry also fails. Standalone parsing misses this
composition boundary.

Relationships are separate from network membership. Use existing RAES kinds
for justified directed service dependencies; distinguish those from
infrastructure ordering dependencies and kit/package prerequisites. Do not
write the same dependency in several carriers merely to satisfy tests. A
Grafana/Tempo pair or matching service ports does not itself prove a required
application binding, data flow, or readiness dependency. Establish the authored
relationship's basis; use an existing typed RAES runtime binding when the claim
requires one. Do not invent a kit-level relation.

Leave concrete addressing, host publication, and backend launch configuration
out of this correction. Omitting switch properties avoids reserving CIDRs and
gateways; it does **not** prove network isolation or access control. Links and
`depends_on` relationships are not firewall policies, authenticated connections,
startup/readiness guarantees, telemetry flows, or runtime observations.

## Seed carrier and serialization boundary

RAES `ContentItem` is closed and has only `name`, `display_name`, `tags`, and
`description`. Adding `value` is invalid. Reuse dataset-level `Content.text`
and `format`, or its existing `Content.source` contract. For small fixed seeds,
inline JSON with `format: application/json` carries values beside the item
inventory and is covered by the module's artifact binding. Retain the items:
the pinned ordinary dataset validator requires items or a source; inline text
alone does not satisfy it.

For an item-keyed JSON payload, require exact item-name coverage, unique keys,
finite JSON values, and meaningful concrete values of the appropriate domain
type. Labels, empty placeholders, or the word "configured" do not supply state.
Preserve useful booleans and zero values rather than checking generic
truthiness. This is a first-party content-test convention, not a new portable
seed schema or backend ingestion protocol. Existing typed RAES application,
datastore, mail, and other runtime declarations remain authoritative for
service configuration; seeds must agree with them and must not become a second
configuration authority. Where an existing RAES domain-content contract already
describes the data, reuse its payload format rather than this inventory
convention. Opaque JSON strings are not RAES symbol references: do not hide node
links, service bindings or namespace-dependent endpoints inside them and expect
the composer to rewrite or validate them.

Check that fixed payloads remain true under parameter variation. A fixture
must not repeat a configurable organization, domain, database or retention value
as a constant and then disagree with the composed declaration. Keep independent
sample records fixed; carry configurable service facts in the existing typed
RAES fields. `Content.service_materialization` is an existing RAES surface for
applicable service content, not permission to invent a generic inventory
installer. Supplying values alone proves neither delivery nor installed state.

**Do not interpolate unrestricted parameters into serialized JSON.** A
synthetic namespaced-composition probe confirmed that RAES accepts a dataset
whose text becomes invalid JSON when a string parameter contains a quote.
RAES substitutes text without JSON escaping, and parsing SDL does not validate
embedded JSON. Backslashes and control characters need the same attention.
Two passing composition fixtures are insufficient proof of safety. Prefer fixed
synthetic records and existing typed fields for variable configuration. If a
dataset requires arbitrary parameter-derived serialization, require a suitable
public RAES contract; do not add a local template engine, secretly restrict
previously accepted parameters, or pass pre-escaped scalar parameters.

A content reference must use RAES `Source` and resolve to immutable, byte-bound
content through the ordinary pack resolver (`digest.resolve_pack_artifact`).
A kit-relative path, checkout filename, mutable URL, or guessed materialized
artifact id is insufficient. Asset ids are namespaced during materialization,
so reference candidates need proof through composition and materialization,
not just file existence. Inline fixed content avoids new acquisition or
resolver behavior.

`assets/seed.yaml` is operator-facing supporting material, not another semantic
authority. Keep identifiers and sensitivity claims accurate; avoid duplicate
payloads. Its copied `configuration` values are not a runtime parameter
renderer: do not present defaults as effective values of a varied composition.
Keep module, README, integration notes, and exports consistent.

Materialized assets stay within the existing `assets/briefing/`,
`assets/content/`, `assets/kits/`, and `docs/kits/` allowlist. A kit cannot install
validators, tests, hooks or workflows. Keep admission and preview non-executing;
trusted author CI remains the separate authority for running pack-local checks.

## Cross-cutting layers to reuse

Paths below are relative to `src/raes_env_packs/` unless specified otherwise.

| Layer and canonical incumbent | Required treatment |
| --- | --- |
| Source admission and filesystem: `_authoring_safety.admit_members`, `_pack_fs`, `KitLimits`, `load_kit_release`, kit `_strict_yaml` / `_strict_json_object` | Preserve bounded regular-file reads, no-follow traversal, link/special-file rejection, canonical contained paths, collision checks, strict duplicate-free YAML/JSON, and size/depth/member limits. Operator secret files and `raes-trust.yaml` remain inadmissible before reads. No remote import or acquisition is needed. |
| Shape and semantics: `resources/schemas/kit.schema.yaml`, `validate_kit_document`, `_load_release_scenario`, public RAES parsers | Preserve closed manifests, release/module version agreement, infrastructure-only admission, RAES references, namespaces and parameter constraints. Content tests check first-party completeness without adding another semantic validator. |
| Secrets, parameters and OS exposure: manifest/parameter secret checks, `_normalize_parameters`, `kit_cli._parameters` | Seeds must be synthetic, non-secret publication content. No customer data, credentials, tokens, private endpoints, environment coordinates, or host settings. Existing checks do not scan every arbitrary content string: review payloads explicitly. Keep bounded public scalar inputs on stdin (`--parameters -`), not JSON in argv. Add no environment bindings, shell interpolation, process commands, host mounts, listeners, or ports. |
| Host authorization and output admission: `authoring.AuthoringSession.call`, `_bounded`, `_save`, `_authoring_tools.TOOLS`, `mcp_server.create_server` | Preserve closed bounded requests, admitted source handles, host-controlled roots, preparation/apply grants and exact proposal review. The complete review, including seed bytes, must pass the existing output size, shape and secret checks before its proposal becomes actionable. Local CLI use adds no authentication service; catalog revisions and kit files grant no host permissions. No new adapter or grant is required. |
| Discovery and mutation: `KitSource`, `build_kit_catalog`, `inspect_kit`, `propose_*`, `apply_proposal` | Derive exports from admitted RAES models and retain the same preview/apply proposal. No family-specific DTO, controller, service, catalog, or workflow. Inspection's `topology` lists exported symbols; it is not an independently authored graph. |
| Integrity and persistence: RAES associated-artifact models, `canonical_sdl_digest`, `associated_artifact_set_digest`, `load_kit_release`; `digest`, `_transactions` during materialization | Bind every successor file, checksum, size, manifest version, semantic parent and set digest through existing authorities. Preserve ownership-ledger joins, the RAES lock, full-successor validation, same-filesystem Linux `renameat2` exchange and recovery preservation. The ledger is provenance/ownership, not topology, service state, another lock or a database. Unsupported OS transaction guarantees fail closed. |
| Errors and observability: `KitError` / `KitRecoveryError`, `Diagnostic` / `ValidationResult`, `authoring._safe_diagnostics`, CLI outcomes `0`/`1`/`2`/`3` | Retain bounded value-free diagnostics, silent libraries and host-owned redacted audit events. Keep seed text, parameter values, raw SDL and parser exception prose out of errors and `proposal_document`. The author-authorized `review_document` / `_proposal_review.changes` intentionally retains exact before/after content; do not redact or truncate the change being approved. No new exception hierarchy or logger. |
| Visibility, supply chain and release: existing asset visibility, component inventory, `validation`, `content_ci`, `release`, `.github/workflows/ci.yml` | Operator assets stay operator assets; inline module content is published content, not secret storage. Keep software scope unresolved/external unless actually immutably pinned or shipped. Add no dependency, product licensing claim, publication service, or CI permission. Standalone kit validation and ordinary-pack gates serve different purposes. |

## Evidence and extension seams

Build on `tests/test_published_kits.py` for admission, exact artifact coverage,
discovery, default/variation cases and namespaced composition. Assertions must
inspect composed payloads too, distinguishing JSON validity from meaningful
item coverage and correct domain data. For parameter-sensitive serialized
content, exercise quotes, backslashes, newlines, Unicode and additional
namespaces; SDL parsing alone is not the success criterion. Prove topology
endpoints resolve after import and separate imports do not accidentally share
an internal network.

Topology assertions must check the intended membership and reachability of
every participating node, plus each justified relationship's type, endpoints
and direction. Nonempty mappings alone miss disconnected nodes and reversed
dependencies. Check infrastructure ordering separately, and allow intentional
network separation rather than requiring every node to share one switch.

Use the semantic-version selection precedent in
`tests/test_kit_compute_substrate.py` for current-release checks; historical
releases remain under existing admission/composition tests. New completeness
checks cover every current seed dataset and multi-node topology, not a fixed
four-family eligibility list. Family-specific facts may be a small test-data
table; topology coverage must allow future kits with several internal networks.
Retain newest-kit compile/planning checks for added switch or realization demands.

Ordinary `raes-pack-validate` / `raes-pack-release check` invocations do not
validate the standalone kit collection. Reuse `tests/test_kit_materialization.py`
and existing integration harnesses for pack-local identity, visibility, lock
and lifecycle checks. Discovery counts must account for successor releases. The
46 successors raise the release count from 90 to 136. The integration
walkthrough's earlier count of 89 was already stale. Neither literal is
authority for how many corrections are needed. Repository completion still
requires all six checks in `AGENTS.md`.

The extension seam remains the RAES module: typed parameters vary configuration,
explicit exports expose intentional composition surfaces, and larger seeds can
use resolver-visible immutable sources. Additional nodes, networks and dataset
items need no kit-schema revision. Backend realization, runtime data delivery
and readback, secret brokering, service-specific bootstrap, readiness/evidence
models, inter-kit wiring, automatic pack upgrades, and deployment qualification
are outside #416. Do not import downstream catalog or private deployment
vocabulary into the portable contract.
