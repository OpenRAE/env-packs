# Owlbear protected-target kit preflight

Issue #540 calls for reusable Owlbear target declarations and supporting kit
material. Use the existing infrastructure-kit carrier and RAES module contract.
The protected target is static environment state; its attack, evaluation, and
experiment context belongs to a consuming pack. Existing ADRs
[0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md),
[0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md),
[0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md), and
[0041](../decisions/adrs/0041-distribute-kits-as-package-resources.md)
already cover this design. No new ADR, kit family contract, or schema is needed.
This note records guardrails, not an implementation sequence.

## Facts that must be established

The supplied issue does not identify a source revision, artifact digest,
redistribution terms, listener, API, or supported posture values. Establish those
facts from the admitted Owlbear source before fixing the release contract.
Do not copy another kit's generic HTTP routes, `stable` source, synthetic account,
or resource estimates as evidence of Owlbear's behavior. Record the source
revision, attribution, rights, required artifact inputs, and known limitations
with the release. A digest establishes content identity, not authenticity or
permission to redistribute.

The public package includes all of `kits/`. Only material cleared for public
redistribution belongs there, including configuration, datasets, and any model
or dependency artifacts. `operator` visibility does not make bundled bytes
private. External artifacts remain requirements; their acquisition is a separate
authorized operation. Do not fetch, vendor, publish, or send source or derived
material to another service just because a kit references it.

The separate `owlbear-protected-target-design.md` draft proposes
an ARM64 Linux kernel/eBPF target with kernel-module, daemon, game, and
signature inputs. It supplies a candidate source revision, not verified binary
identities. This preflight has not reviewed that upstream source or confirmed
its platform, license, interface, or build claims. Treat those claims as pending
source review, not as facts established by this note.

For that proposed scope, kernel/build compatibility and required kernel access
must be explicit admission prerequisites. An open substrate does not establish
kernel compatibility or isolate privileged kernel operations from a host.
Composition and tests must never load a module, attach eBPF, or grant privilege.
Backend admission must refuse an unsuitable environment without a permissive
fallback. Preserve ABI/build facts with admitted artifacts where available;
a source commit does not identify the resulting executable bytes.

The proposed daemon-state parameter belongs in RAES
`runtime.service_manager_units`. Its unit must have a supported binding to the
actual daemon; an unrelated unit with the desired state does not satisfy that
requirement. If a backend must supply a wrapper or native unit mapping, disclose
that preparation prerequisite. Active daemon state does not prove enforcement,
and inactive daemon state does not prove that kernel protection is absent.
Keep those claims separate from artifact presence, loading, and readiness.

## Declaration and extension boundaries

Use one independently versioned release under `kits/<id>/<version>/` with the
existing `kit.yaml`, RAES `module.sdl.yaml`, README, seed/integration assets,
composition cases, and associated-artifact manifest. Select an existing concern
for discovery. Owlbear identity belongs in its actual RAES source/product
declarations; do not invent a `protected-target` node type, concern, manifest
section, or target registry. Unlike pack versions, kit versions are independent
of the Python package version. Never rewrite an already released kit.

The module owns its nodes, resource requirements, actual service surfaces,
runtime declarations, and explicit exports. The manifest's resource estimates
are planning metadata, not a second executable sizing contract. Keep estimates
consistent with the supported configurations and state storage/accelerator or
platform limitations where applicable. A shared `deployment_profile` label
alone does not change allocated resources.

Keep the existing `deployment_profile` and `service_label` convention and expose
bounded, non-secret RAES scalar parameters for meaningful Owlbear runtime
variation, with RAES types and allowed values for supported postures.
A changed posture must change the relevant typed runtime requirement,
not just a description or seed label. Keep these three meanings separate:
Owlbear runtime configuration, RAES realization `open`/`constrained`/`exact`
authority, and RAES artifact requirement explicitness. A target called
"protected" is not a safety or effectiveness claim.

Parameterize supported public configuration at the RAES module seam. Artifact
selection uses RAES `Source.artifact_requirement`, including its existing
identity, constraints, locked-input, materialization, route, and trust-reference
contracts where applicable. Do not squeeze an arbitrary JSON configuration,
shell fragment, environment map, or artifact resolver into a string parameter.
An unsupported semantic need goes upstream to RAES. The current dependency floor
and tested lock are RAES 10.0.0 under
[ADR 0043](../decisions/adrs/0043-require-a-minimum-raes-version.md);
older preflight pins are not the current contract.

Leave compute substrate open unless the established Owlbear requirements demand
a specific substrate. An exact input artifact does not automatically require a
virtual machine, container engine, or backend profile. Export the actual target
node and useful RAES surfaces, with the collection's benign `seed_inventory`.
Connections to callers, model services, storage, and observation services belong
at the consuming pack root where those services are independent. Keep only
inseparable internal dependencies inside the kit, with explicit topology.
If the target requires retained state or generated files, use RAES
`persistent_volumes` and `generated_artifacts` with explicit lifecycle and
sensitivity. These runtime resources are separate from kit ownership records.

Pack-local seed material describes useful static state, with at least three
concrete benign objects. It must agree with typed runtime declarations without
becoming a parallel configuration language. `_stage_kit_members` copies assets
verbatim: variation does not render seed/integration files. Describe defaults as
defaults and refer to parameters where necessary. Fixed asset destinations also
mean that a second namespace does not by itself permit a second materialization
at the same paths. Preserve existing collision diagnostics; do not claim
multi-instance support from an SDL-only composition test.

## Cross-cutting layers to reuse

Paths below are relative to `src/raes_env_packs/` unless otherwise stated.

| Layer and canonical incumbent | Required treatment |
| --- | --- |
| File admission: `_pack_fs`, `_authoring_safety.admit_members`, `KitLimits` | Preserve descriptor-relative no-follow reads, canonical relative paths, collision/link/special-file rejection, inventory-change detection, and byte/member/parser limits. Operator files and `raes-trust.yaml` are refused before reads. Current kit defaults allow 8 MiB per file and 32 MiB total: large Owlbear inputs belong in admitted artifact requirements, not a raised global budget. |
| Carrier parsing: `kits.validate_kit_document`, `_strict_yaml`, `validation._StrictLoader` / `_check_yaml_events`, `resources/schemas/kit.schema.yaml` | Reuse closed fields, duplicate-key rejection, exact kit/module version agreement, unique asset ids/destinations, required test kinds, and component-scope checks. Keep SDL and artifact semantics out of pack schemas. No Owlbear-specific validator or DTO is needed. |
| SDL/runtime policy: `kits.load_kit_release`, `_verify_infrastructure_only`, RAES `parse_sdl` / `parse_sdl_file`, compiler/planner | Use public RAES contracts for service references, runtime configuration, authorization, resources, artifacts, and realization constraints. Check composed references and compiled requirements as well as parsing. Keep agents, action contracts, behavior, objectives, conditions, injects, events, scripts, stories, and workflows outside the kit; admission already rejects those sections. Do not weaken it to package an evaluation scenario. |
| Configuration, secrets, and environment shapes: kit manifest/parameter secret checks, `_normalize_parameters`, RAES runtime models | Parameters are bounded non-secret scalars; environment coordinates and secret-shaped names/values are rejected. No credentials, private keys, signed URLs, secret-store coordinates, or provider environment keys in parameters, seeds, provenance, or examples. If secret-dependent behavior is essential, declare only supported value-free RAES requirements/references. RAES runtime environment uses typed entries, not an arbitrary map; do not introduce a second env-binding shape or use raw environment declarations to bypass kit secret restrictions. Heuristic admission is not a scan of every payload string: review all released content. |
| Authentication, exposure, and host/OS boundary: RAES runtime authorization/listener declarations, `kit_cli._parameters`, `authoring.AuthoringSession`, `_authoring_tools.TOOLS`, `mcp_server` | Distinguish scenario-visible services from bind addresses, host port publication, and firewall rules. Do not grant host mounts, Docker socket access, privilege, external provider access, or disabled authentication merely for convenience. Any intentional authored posture must be supported, bounded, and explicit. Stdin carries CLI parameter documents; secret bytes never enter argv, healthchecks, shell expansion, environment dumps, logs, or evidence. Backend secret delivery, file modes, process visibility, egress admission, and runtime containment remain backend obligations. Existing host source/root grants, closed request shapes, preparation, and exact apply authorization still govern composition; a new kit grants no new access. |
| Integrity and provenance: `kits._load_release_manifest`, RAES associated-artifact models/helpers, `digest.validate_pack_content_manifest` | Bind every release file except the manifest itself to exact checksum, size, semantic parent, and set digest. Required Owlbear inputs are distinct from these shipped bytes and from a RAES module digest or lock. Preserve source/rights records without adding a provenance schema. Materialization changes locators and artifact ids; verify requirement/manifest references, satisfaction addresses, namespaces, and input identities in the resulting pack rather than assuming kit-local references survive unchanged. No second hash, lock, or trust model. |
| Composition and persistence: `KitSource`, `inspect_kit`, `propose_*`, `apply_proposal`, `_transactions`, materialization-schema validation | Inspection and preview stay networkless and non-executing. Reuse RAES structured edits/resolution, `raes.lock.json`, explicit ownership and immutable source/revision records, full-successor validation, concurrent-change checks, fixed safe modes, and atomic promotion/recovery. Assets target only the existing non-executable allowlist. No lifecycle scripts, custom writer, cache, database, automatic download, or service start. Linux transaction requirements remain; portability of declarations is not universal host support. |
| Component inventory and release: `component_boundary`, `KitSourceResolver`, `publication`, `sbom`, `release`, `verify` | Classify every shipped/pinned Owlbear component at its finest RAES artifact/source or preserved upstream SBOM identity. Mutable/runtime-selected inputs stay explicitly external or unresolved. Recovery uses the recorded immutable kit source/revision, not a matching filename or current checkout. Preserve publication/compatibility and provenance gates on the composed pack. Component inventory is an SBOM input, not a signature, dependency-closure guess, safety result, or proof of realization. |
| Errors and observability: `Diagnostic`, `ValidationResult`, `KitError` / `KitRecoveryError`, `kit_cli`, `authoring._safe_diagnostics` | Keep silent libraries, bounded value-free diagnostics, terminal-safe rendering, existing host envelopes, and CLI statuses 0/1/2/3. Host audit and backend observation retain their existing owners. Catch documented RAES domain errors at existing boundaries if adaptation is necessary; do not catch a broad built-in or base exception to hide a failure. No new exception/logger hierarchy and no raw upstream prose, payloads, prompts, credentials, or absolute host paths in errors. |
| Packaging and workflow: `pyproject.toml`, `.github/workflows/ci.yml`, `release-please.yml`, `.gc/plan-rules.md`, dependency/workflow policy tests | The existing complete-tree wheel/sdist mapping already includes a new kit. Reuse hash-locked tools, pinned actions, least-privilege tokens, fail-closed `verify`, signed releases and existing publication destinations. No new publisher or per-kit packaging list. Implementation uses `feat(kits):`; release-please owns the package version/changelog and automated pack-version synchronization. Human merge boundaries remain unchanged. |

## Evidence and limits

Reuse `tests/test_published_kits.py` for discovery, exact release validation,
substantive seeds/material, and default versus materially different domain
parameters. Its release-count assertion must account for a new release.
Composition-case YAML is data, not an executable test runner: listing
`multi-kit` or a group name does not exercise a relationship. Assert actual
Owlbear runtime changes, namespaced exports/references, and composition with an
appropriate existing kit. Do not invent a dependency solely to satisfy a test.
If multi-node, account for the topology/dependency expectations in that suite.

Use `tests/test_kit_compute_substrate.py`'s RAES compiler/planner pattern to
check that parameters preserve the intended typed requirements and that a
manifest lacking a required capability is refused. Its permissive stub does
not qualify a real backend. Use `tests/test_kit_materialization.py` helpers for
an ordinary composed pack with lock, ownership, asset/input references, and
artifact byte binding. Existing update/remove/conflict and security tests own
the generic machinery; add focused coverage only where Owlbear exercises a
new interaction. Reuse `tests/test_distribution_contents.py` for exact wheel,
sdist-derived wheel, and installed-source inventory/digest verification.

All six checks in `AGENTS.md` remain required. The default `--repo .` and
`release check --all` routes can pass without discovering a pack, and release
checks are pack checks: they do not replace the kit tests. Keep explicit
`--packs-root packs` checks and ordinary composed-pack release evidence.
Static success establishes authoring/composition compatibility, not service
readiness, protection effectiveness, runtime evidence, or backend portability.

## Non-goals

No issue implementation in this preflight. The subsequent kit work does not
add RAES semantics, a runtime adapter, backend bootstrap, cloud deployment,
credential acquisition, external processing, or a new hosting destination.
It does not include attacker behavior, jailbreak corpora, scoring, evidence
interpretation, paper/trial configuration, or downstream catalog conventions.
Existing API/model infrastructure may be composed, not copied into an Owlbear
framework. An absent required upstream contract is an explicit limitation to
resolve, never permission for a local schema or prose-based runtime protocol.

## Design Vocabulary That Applies

- **RAES-subordinate pack tooling**: reuse the existing kit carrier and pack
  authoring, validation, and release tooling described in
  [environment-packs](../public/environment-packs.md).
- **Boundary contract**: RAES owns SDL, runtime/scenario meaning, parameters,
  artifacts, and composition; this repository owns pack layout/tooling and the
  first-party release. Backends realize the composed scenario.
- **Binding ADR-036**: publish the reusable first-party kit under `kits/`;
  co-location creates no semantic authority or runtime API.
- **Applicable anti-recommendations**: do not extend or restate RAES semantics,
  including objectives, evidence, telemetry, scoring, or oracle models; do not
  encode downstream catalog vocabulary in canonical pack contracts.
