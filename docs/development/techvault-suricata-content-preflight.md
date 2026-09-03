# TechVault Suricata content-contract preflight

TechVault declares a 16-rule scenario-local Suricata source, a built-in source,
and a generated MISP source, but its current inline `local.rules` contains only
comments and its inline configuration selects only that empty file. A clean
realization therefore cannot satisfy the authored detection-engine inventory.
Copying replacement files from a LilRAE checkout after realization makes the
runtime depend on an undeclared authority and does not repair the portable
contract.

Repository history resolves the intended local-content question. Commit
`fd3f5faf662b22bdd63cf89d5c454f2e768beb42`, the parent of the full-TechVault
migration commit, contains a 16-active-rule local corpus and configuration under
`packs/techvault/build/aptl-runtime/config/suricata/`. Their count, variables,
services, addresses, and detection themes agree with the current SDL. The rule
Git blob is
`a7d8f8e6b3af1be5aed2b4091eb1dfe6307b95e1`; the accompanying configuration
blob is `b2630f613994434c66c9464f04bcc8848b9b4e1b`. That evidence selects the
16-rule corpus as the authored baseline and selects the configuration's
variable and rule-file relationships as the behavior to preserve. It does not
make every historical runtime setting authoritative: packet acquisition and
interface realization remain the separate #284 concern.

This note records the authority decision and the cross-cutting constraints on
the repair. It is not an implementation plan.

## Required contract

Keep the three Suricata sources and their lifecycles distinct:

| Source | Authority and lifecycle | Required relationship |
| --- | --- | --- |
| `suricata-builtin` | Exact Suricata image artifact; immutable for a realization | The engine file reference and effective configuration select `/var/lib/suricata/rules/suricata.rules`, and realization reports whether it loaded. The exact selected image must be shown to contain it; an image-name assumption is not provenance. |
| `techvault-local` | TechVault pack; immutable exact pack content | The associated-artifact inventory carries the active 16-rule corpus, exact-copy content placement installs it read-only at `/etc/suricata/rules/local.rules`, the engine file reference selects that path, and the declared and realized counts agree. |
| `misp-iocs` | Runtime output of the declared `misp-ioc-to-suricata` forwarding agent; mutable | The configuration and engine file reference select `/var/lib/suricata/rules/misp/misp-iocs.rules`; the forwarding output resolves to the same narrowly shared volume, and reload targets `/var/run/suricata/suricata-command.socket`, the engine's declared control channel. A zero-indicator generated file is valid and must not be confused with an empty authored local corpus. |

The local rules reference `HOME_NET`, `HTTP_SERVERS`, `HTTP_PORTS`,
`INTERNAL_NET`, and `DMZ_NET`. The effective Suricata configuration must define
all five consistently with the current TechVault networks and web application;
the historical values establish the intended subnets and web service. Standard
variables needed by the selected built-in corpus must also remain available.
Suricata's native configuration parser is the authority for engine syntax and
variable expansion. Do not reproduce its grammar as an environment-pack
schema.

The engine's `configuration_file_refs` must identify
`/etc/suricata/suricata.yaml`; each rule source's `file_refs` must identify the
corresponding selected path above. These references are the portable join to
content realization, not descriptive duplicates that may drift independently.

The Wazuh `suricata_rules.xml` content is a different layer: it interprets EVE
events after Suricata produces them. It is not a Suricata sensor rule source and
must not be counted, placed, or validated as one.

The runtime join is one chain, not independent declarations:

`associated artifact -> RAES content source -> content placement -> engine
file_refs/rule-files -> loaded engine state -> EVE output -> Wazuh sidecar and
rules -> observation/evidence`.

Every reference in that chain must identify the same path, source, lifecycle,
and producer. The current `suricata_config_seed` retained volume and comments
about undeclared MISP/socket volumes are remnants of the downstream fixup, not
a second portable authority. Static authored bytes are desired state and must
be reconciled on every clean realization; retained runtime state must never be
allowed to mask missing or changed pack inputs.

## Canonical contracts to reuse

Pinned `raes==3.3.0` already owns the portable semantic surfaces:

- `RuntimeNetworkDetectionEngine` and its rule sources, network sets, output
  streams, file references, evidence references, and control channels are the
  engine inventory. Use them; do not add a TechVault-specific detection model.
- The existing `Content` source and placement contract owns exact authored
  configuration and rule bytes. Follow the source-backed Wazuh content already
  in TechVault rather than retaining inline text or creating another carrier.
- `RuntimeForwardingAgent(agent_kind=content_sync)` owns the MISP API-pull,
  IOC-to-rule transform, generated-output, and reload relationship. Do not add a
  second socket/reload schema or represent mutable MISP output as a RAES
  `GeneratedArtifact`, whose supported kinds do not include rule corpora.
- Existing RAES propositions, assertions, evidence requirements, observation
  boundaries, realization observations, and runtime snapshots own detection
  intent and satisfaction evidence. This repository must not define an oracle,
  scoring model, telemetry meaning, or evidence DTO.

Within this repository, all authored bytes pass through the shared
`validate_pack()`/author-CI authority and pinned `raes.parse_sdl_file` parser.
Exact content identity passes through `derive_pack_content_manifest()`,
`validate_pack_content_manifest()`, and `resolve_pack_artifact()` with the
existing exact-copy profile. These provide bounded descriptor-anchored reads,
canonical-path enforcement, symlink/hardlink/special-file rejection, inventory
and digest checks, and immutable bytes. Do not hand-edit checksums, add a second
resolver, or fall back to a host checkout or network location.

`tests/test_techvault_pack.py` and the TechVault validation entry point are the
canonical pack-contract surfaces. Pack-specific tests should join the existing
RAES declarations and exact content placements and exercise malformed variants
for active-rule count, undefined variables, selected-but-missing files,
source/placement identity mismatch, generated-source/reload mismatch, and zero
effective rules. Missing artifacts and provenance mismatches already belong to
the manifest/resolver tests; reuse those failures rather than inventing a
Suricata exception hierarchy. A bounded lexical guard may distinguish comments
and blank lines from at least one active local rule, but it must not claim to
parse Suricata syntax; exact validity, variable resolution, selected files, and
effective loaded-rule counts require the native engine check.

Static inspection cannot prove that the selected engine accepts and loads the
configuration. Runtime verification must additionally use Suricata's native
configuration test, start from a clean admitted pack with no old volumes or
checkout-sourced files, and observe the effective loaded sources and active
local rule identifiers. The clean-run proof must fail if any post-deployment
replacement or undeclared source is required.

## Security, realization, and observation gates

Any intended design crosses all of these layers:

| Layer | Required guardrail |
| --- | --- |
| RAES shape and semantic validation | Parse through pinned RAES and preserve closed shapes, unique ids, absolute file-reference rules, service/source references, and explicit content classifications. RAES currently does not prove every content-placement-to-engine-path or forwarding-to-control-channel join; add narrow TechVault contract assertions without creating a parallel production schema. |
| Pack validation and author CI | Reuse the static validator, anti-extension boundary, participant-facing content leak scan, and deterministic bounded diagnostics. Unexpected defects still raise; invalid authored input remains a `ValidationResult` diagnostic. |
| Artifact identity and filesystem policy | Put static configuration and local rules in associated artifacts and resolve them only through the canonical manifest/resolver path and exact-copy profile. Preserve size budgets and no-follow, containment, canonical-name, file-type, and digest checks. Evidence identifies artifact, pack-set, and realized-byte digests without including file bodies or host paths. |
| Secret handling | Rule/config assets contain no credentials. `MISP_API_KEY` remains a value-less `operator_secret`, resolved at the runtime secret boundary; it must not enter pack bytes, argv, logs, engine diagnostics, or evidence. Do not dump the complete environment to prove the sync agent ran. |
| Control-channel authorization | `auth_required: false` is acceptable only for the private Unix socket shared narrowly by the Suricata process and its declared sync agent. Both ends, the path, capability, ownership, permissions, and mount must agree. Never publish the socket to a participant or host-facing interface. |
| OS/container exposure | Keep the fixed configuration path in the existing process invocation and keep rule/config bodies out of argv and shell interpolation. Static content is read-only; only the generated MISP directory, command socket, and logs receive narrowly scoped writes. Account for UID/GID, modes, mount collisions, traversal, `/proc`, and symlink substitution. Do not expand the existing network capabilities to repair content placement. |
| Persistence | Reconcile static pack-owned content from immutable inputs for each realization. Treat generated MISP rules and logs as runtime state with their declared ownership and lifecycle. A retained seeding volume or prior container state cannot be accepted as content provenance or readiness. |
| Readiness and evidence | A running process, open socket, existing `eve.json`, successful reload response, or nonzero aggregate rule count is insufficient alone. Record admitted content identities and realized readback digests, native configuration success, selected source files, active local SIDs/count, reload result for mutable content, and bounded engine readiness. Preserve author declaration, backend realization, and observation as separate records. |
| Errors and logging | Keep static failures in `ValidationResult`/`PackDigestError`. Runtime adapters should emit stable redacted failure codes and correlation ids with bounded engine output. Never expose rule bodies, environment dumps, secrets, absolute host paths, or raw exception text in portable evidence or participant-facing envelopes. |

The declared end-to-end behavioral proof should use the Kali-to-webapp DMZ path
and a SQL-injection request that matches local SID `1000010`. It must observe
that exact Suricata EVE alert and the corresponding existing Wazuh
web-application alert (`303020`), rather than accepting unrelated alerts or
aggregate statistics. This is the most direct existing join among the current
topology, historical authored rule, EVE forwarding path, and Wazuh rule corpus.
If the sensor cannot observe that declared path, the result is evidence for the
#284 packet-processing gap; it is not permission to copy rules after startup or
weaken the expected detection.

## Extensibility boundary

The reusable seam is a source-neutral mapping from a declared engine rule
source, through its `file_refs`, to a content placement and content identity,
with lifecycle distinguishing image-built-in, immutable pack-authored, and
mutable forwarding-agent-generated sources. Only the mutable class needs a
typed reload relationship. LilRAE should extend its existing generic content
placement/seeding adapter through this mapping, not branch on `techvault`, a
scenario name, or an APTL-era path.

A second static corpus should require another associated artifact, content
entry, placement, and engine rule source; another dynamic feed should require a
forwarding source/transform/output/reload declaration. Neither should require a
new resolver, validator family, Suricata-specific pack schema, or post-start
copy hook. Packet-acquisition/interface selection remains an independently
variable seam owned by #284 and must not be baked into the recovered content
contract.

## Non-goals and rejected shortcuts

- Do not preserve, rename, or tolerate LilRAE's checkout-local copy as a
  fallback, migration aid, readiness repair, or source of provenance.
- Do not assume all historical configuration bytes are authoritative. Recover
  the rules, variables, selection, outputs, and control relationship; keep
  capture/interface policy within #284.
- Do not treat header-only local rules as a valid authored corpus, but do not
  reject a header-only generated MISP file when its declared indicator count is
  zero.
- Do not count Wazuh correlation XML as Suricata rules, or treat EVE file
  existence, Wazuh ingestion, or an unrelated alert as proof of the intended
  sensor detection.
- Do not add pack-local RAES semantics, a duplicate Suricata grammar/parser,
  another content identity, reload, observation, error, or provenance model, or
  downstream catalog/deployment vocabulary.
- Do not expand capabilities, publish the command socket, embed operator
  secrets, place secrets in argv, or include authored content bodies in errors
  or evidence.
- Do not declare golden readiness from static tests. A clean participant-
  equivalent realization and the exact observable detection path remain
  required.

No new ADR is required. ADR 0009, ADR 0036, ADR 0012, ADR 0013, ADR 0028, ADR
0033, the public [ownership boundary](../public/ownership-boundary.md), and
[golden-readiness criteria](../public/golden-readiness.md) already decide the
authority, identity, validation, publication, and proof boundaries. The issue
requires a TechVault contract repair inside those decisions, not a new
repository-wide semantic choice.
