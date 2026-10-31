# TechVault case management removal preflight

Issue #536 retires TheHive and Cortex from both TechVault packs and withdraws
all three TheHive kit releases from the current collection. Remove the services
and their supporting declarations together. Keep the defensive-tooling guide
as a Wazuh/Suricata composition example, with no replacement case service.

ADRs [0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md),
[0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md),
[0038](../decisions/adrs/0038-ship-raes-concept-bindings-beside-pack-sdl.md), and
[0041](../decisions/adrs/0041-distribute-kits-as-package-resources.md) already
cover the boundaries. No new ADR, schema, licensing engine, or runtime API is
needed. This note governs the proposed removal; it does not implement it.

## Removal boundary

Both `packs/techvault` and `packs/techvault-participant-study` must have a
consistent remaining scenario. Besides the issue's named nodes, accounts,
principal, relationship, content, analyzer assets, proposition, assertion, and
evidence requirement, the affected declarations include:

- `infrastructure` entries and dependency references for all four removed
  nodes; their applications, listeners, datastores, and authorization disappear
  with those nodes.
- `generated_artifacts.techvault-soc-certificates`: TheHive keystore/password
  outputs and TheHive/Cortex consumers. Preserve the shared CA and the selected
  outputs and least-privilege mounts used by MISP and Shuffle.
- The five dedicated volumes: `cortex_data`, `thehive_cassandra_data`,
  `thehive_data`, `thehive_es_data`, and `thehive_index`.
- `observation_boundaries.participant-cortex-enrichment-view` and every
  remaining reference to the removed evidence and subjects. Preserve the
  participant-study boundaries, injects, timing, agents, and affiliations.
- The SOC workstation's `mcp-casemgmt` software-component declaration and the
  corresponding package inside **both** checked-in blue source archives.
- Forward DNS records `casemgmt` and `thehive`, and the TheHive reverse record.
  These are executable scenario content, even though SDL references them only
  through exact artifacts. Preserve unrelated records and valid zone syntax.
- Current pack README/concepts/provenance claims and the two analyzer entries
  in each associated-artifact manifest.

Withdraw the entire `kits/infrastructure.thehive-case-management-service/`
tree, including releases 1.0.0, 1.1.0, and 1.2.0 and all their supporting files.
`kits.build_kit_catalog()` derives offerings from release directories. Hiding a
catalog row, adding a packaging exclusion, relabeling the license, or leaving
orphan kit assets would retain distributable content. Preserve all surviving
kit release bytes and the generic support for separately admitted sources.
A kit's own MIT declaration does not establish redistribution rights for the
service software it describes.

The public composition guide, `tests_integration/defensive_tooling_composition.py`,
and its regression test must describe the same two-kit example. Retain its
RAES-authored Suricata-to-Wazuh relationship and ownership/conflict behavior;
static composition still proves no event delivery or backend readiness.
Update current links and descriptions in `docs/public/kits.md` and
`docs/public/index.md` as needed. `tests/test_published_kits.py` and
`tests_integration/kit_author_walkthrough.py` hard-code 136 releases;
removing three changes this checkout's expected total to 133.
Keep catalog membership assertions in agreement without encoding that count
in discovery or packaging logic.

## Cross-cutting contracts

Paths in this table are relative to `src/raes_env_packs/` unless qualified.

| Layer and canonical incumbent | Required guardrail |
| --- | --- |
| SDL shapes and references: `validation.validate_pack`, `_validate_pack_for_author_ci`, public `raes.parse_sdl` / `parse_sdl_file` | Use the dependency selected by `requirements/runtime.txt` and `uv.lock`, satisfying `pyproject.toml`'s RAES floor. Preserve bounded parsing, closed shapes, reference admission, concept bindings, and compiler coverage. No local SDL schema or second reference validator. |
| Pack/config schemas: `resources/schemas/pack-compatibility.schema.yaml`, `provenance.schema.yaml`, `kit.schema.yaml`, `kit-catalog.schema.yaml`, `kit-materializations.schema.yaml` | Existing strict loaders, duplicate-key rejection, `PackValidationLimits`, and `KitLimits` remain authoritative. This removal needs no schema or config-shape change and no new environment/secret-binding carrier. |
| Pack policy and trusted execution: both `validation/validate_techvault.py` copies, `content_ci` | Retire `validate_cortex_contract`, its call, and its dedicated error helper rather than retaining a mandatory or silently optional Cortex contract. Preserve MISP, Suricata, Wazuh, Shuffle/Orborus, and open-realization checks. Consumer validation stays static; author CI alone runs pack tests/validators with existing time, output, process-group, and snapshot bounds. |
| Secrets, authorization, and exposure: provenance safety/review gates, `kits` secret-shape checks, `_authoring_safety.admit_members`, `validate_realization_method_contract` | Remove retired account fixtures and connector authority; preserve surviving authentication, TLS, fixture classifications, and credential isolation. Add no real credentials, environment coordinates, host bindings, socket mounts, or secrets in argv/output. Kit CLI examples retain bounded stdin parameters via `--parameters -`. Local content removal adds no auth endpoint; `AuthoringSession`/MCP host authorization remains unchanged. |
| Byte identity: `digest.derive_pack_content_manifest`, `validate_pack_content_manifest`, `resolve_pack_artifact`, `tools/refresh_pack_sdl_binding.py` | Retired inventory entries and files must agree. Derive checksums, sizes, and set identity from final bytes; update SDL exact-artifact digests from those same bytes. Refresh surviving concept subject digests without removing the webapp's CWE classifications or changing scheme snapshots. Never invent another checksum/lock format or relax exact resolution. |
| Filesystem and persistence: `_pack_fs`, builder `build_archive`, `_transactions`, kit proposal/apply APIs | Preserve bounded regular-file admission, descriptor-relative no-follow reads, deterministic safe archive modes, staged replacement, and concurrent-change checks. A source-tree deletion is not a kit-materialization transaction or runtime volume cleanup. The guide continues to use ordinary kit proposals, the ownership ledger, RAES lock, and atomic apply; never silently rebaseline author edits. |
| Errors and observability: `Diagnostic` / `ValidationResult`, `PackDigestError`, `KitError` / `KitRecoveryError`, CLI and author-CI adapters | Preserve silent libraries, stable bounded diagnostics/outcomes, and existing host envelopes. Do not add a logger or exception hierarchy, swallow failed validation, or print raw parser/subprocess errors, SDL bodies, environment dumps, credentials, or absolute paths. Retain content-free MCP telemetry. |
| Catalog, package, and release: `KitSource`, `build_kit_catalog`, `source_release`, `bundled_kit_source`, `pyproject.toml`, `component_boundary`, `release` | Canonical `kits/` and `packs/` feed checkout, sdist, wheel, installed discovery, and component/evidence projections. Keep existing source selection, redistribution admission, inventory equality, SBOM/provenance, and release gates. No tombstone service, hidden package copy, fallback to historical TheHive, custom build hook, or parallel publisher. |
| Documentation/workflow: `.ground-control.yaml`, `.gc/plan-rules.md`, `.github/workflows/ci.yml`, public Sphinx root and publication-boundary checker | Use existing verification and warning-strict documentation checks. Keep this record under `docs/development/`. Release-please owns project version/changelog; choose the implementation's Conventional Commit type with the removed public kit capability in view. Do not hand-bump versions or rewrite accepted ADRs. |

## Identity and rebuild traps

The refresh tool does **not** remove deleted manifest entries, discover new
ones, update `content.*.source.artifact_requirement.exact_artifact.digest`, or
repair removed concept subjects. `derive_pack_content_manifest()` also uses the
declared inventory. Descriptor edits are authoring changes; hashes, sizes, and
set digests are derived values. The pack-local exact-resolution tests must
still compare every retained SDL artifact requirement against resolved bytes.
The current concept bindings all address surviving webapp routes; their subject
digests still change when the scenario changes.

The shipped red and blue archives contain a documented adaptation to
`aptl-mcp-common/src/tools/api-definitions.ts` for Wazuh raw-XML rule writes.
The current builder only implements the telemetry adaptation. A naive builder
rerun would lose that correction. The removal must preserve retained member
bytes and adaptation metadata, the reviewed source revision, license, safe tar
metadata/order, and telemetry privacy behavior. Reconcile the existing builder
with the retained correction before treating a rebuild as reproducible; do not
introduce a second archive builder, fetch an unreviewed revision, regenerate the
red archive unnecessarily, or quietly change unrelated packages. The builder's
current destination is the base pack only; the study copy must receive identical
blue artifact bytes while retaining its distinct scenario and manifest identity.

Captured `misp-sync-readme.md` and members of `misp-sync-src.tar` also name the
retired products, including upstream collector/backend code. They are upstream
source material, not current TechVault service declarations. The declared MISP
sync entrypoint must remain independent of those retired paths. Review
reachability rather than rewriting captured source or erasing attribution to
satisfy a repository-wide zero-match search. Preserve historical changelog and
decision evidence; mark superseded operational guidance clearly. Generic RAES
`case_management` vocabulary and another kit's generic integration label do not
by themselves declare TheHive and are outside this removal.

## Verification and extension seam

Reuse `tests/test_techvault_pack.py`, `tests/test_techvault_study_pack.py`, both
pack-local exact-resolution suites, `tests/test_published_kits.py`,
`tests/test_distribution_contents.py`, and the walkthrough regressions. Retire
Cortex-positive tests, including `tests/test_techvault_cortex.py`, while keeping
shared TLS, safety, realization, and identity coverage. Regression evidence must
show absence of retired declarations/references, analyzer files/descriptors,
blue archive package members/metadata, and kit offerings in both checkout and
installed distributions. Merely deleting old tests or changing expected counts
does not establish absence. Preserve the study overlay and identical shared
assets, every surviving kit's validation, and exact wheel/sdist inventories.

The required unittest, repository and first-party content/release gates, and
compile check remain those in `AGENTS.md`; public guide changes also require
the existing warning-strict Sphinx build and publication-boundary check.
Static evidence establishes portable content consistency, not live retirement.

The existing variation seams suffice: `BLUE_PACKAGES` selects reviewed source
packages; the walkthrough's `_KITS` table selects exact releases, namespaces,
parameters, and expected exports; `KitSource` selects an admitted collection.
Keep future membership changes at those inputs. Do not add product-specific
blacklists to generic validators/catalogs, a replacement-service abstraction,
or a second list in packaging configuration.

## Non-goals

No replacement case manager/analyzer, license/trial bypass, optional disabled
service, RAES semantic extension, new schema, runtime controller, credential
delivery, or backend deployment change. Do not remove live containers, revoke
credentials, delete retained runtime data, migrate cases, rewrite Git history,
retract published artifacts, or modify related repositories. Those effects
need their own scope and authorization. This preflight changes guidance only.
