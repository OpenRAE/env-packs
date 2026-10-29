# Pack experiment artifact set preflight

Issue #504 adds pack layout, validation, and release support for RAES experiment
authoring inputs, tasks, capture specifications, and scenario families. Existing
ADRs 0009, 0011–0014, 0028, 0033, 0036–0038, and 0041 cover the architecture;
no new ADR or experiment framework is needed. This is design guidance, not an
implementation plan or a claim that experiment packs already work.

## Authority and contract

RAES owns experiment schemas, references, variation targets, factorial expansion,
bindings, selection, and compilation. Pack authors own the concrete experiment;
this package owns its portable files and safe validation/release integration.
The [ownership boundary](../public/ownership-boundary.md) also applies to capture:
packs request observations, while a runtime chooses collectors and persists
results. A capture specification is neither a collector configuration nor
captured evidence.

At preflight the project and installed distribution are `raes-env-packs` 6.4.2,
exactly pinning released `raes==9.1.0` on CPython `>=3.14,<3.15`. The packaged
layout contract is version 7. The older 8.1.0 dependency in the issue is not an instruction to downgrade.
The delivery requires `raes>=9.2.0` (ADR 0043). RAES 9.2.0 adds the public
`admit_scenario_family` function (OpenRAE/rae#1696). The installed public API includes
`parse_experiment_spec`, `ExperimentTaskModel`, `ExperimentCaptureSpecModel`,
`validate_experiment_selection_against_family`,
`validate_experiment_binding_targets`, and `compile_admitted_trial_plan`.
RAES's typed structural-factorial profile is `factorial-treatments-v1`.
Presence of these exports alone does not establish the issue's acceptance.
Native blocked-by relationships remain authoritative; this local inspection
does not establish that those dependencies are closed.

Use an optional `experiments/` authoring root, preserving RAES's direct
`*.exp.yaml` convention. Define task/capture member discovery and reference-path
rules once in the shipped layout contract; keep them deterministic and bounded.
Use RAES reference fields and document identities to join members, rather than
assuming filenames, task ids, experiment ids, scenario ids, and pack ids match.
Allow multiple experiments and shared task/capture inputs. Existing packs without
experiments retain their behavior. A malformed or unsupported recognized document
must fail, even if no experiment selects it; absence is different from invalidity.
Any pack index is only a presence/path projection, never a second experiment
manifest. No local copy of an upstream schema belongs under `resources/schemas/`.

There are currently no experiment-specific gates in `validation.py`:
`_direct_sdl_documents` discovers only direct `sdl/*.sdl.yaml` members. Extend
the shared static authority, so consumer checks, author CI, catalog projections,
and release publication cannot disagree about experiment validity. Retain
validated data within the existing internal `_PackSnapshot` only as needed;
do not expose a new persistent validated-pack object or parallel repository layer.

## Cross-cutting layers

| Layer and canonical incumbent | Required guardrail |
| --- | --- |
| Filesystem and OS: `_pack_fs`, `PackValidationLimits`, `digest.resolve_pack_artifact` | Load untrusted members from bounded, descriptor-anchored bytes. Normalize every reference path before opening; reject traversal, absolute/ambient paths, links, special files, collisions, invalid UTF-8, and unsupported descriptor platforms. Resolve only within the admitted immutable pack. Do not validate a pathname and reopen it later. |
| Parsing and shapes: `validation._load_yaml_member`, `_strict_json_member`, RAES `parse_experiment_spec`, `ExperimentTaskModel`, `ExperimentCaptureSpecModel` | Preserve duplicate-key, finite-value, byte, node, alias, and depth limits before model validation. The upstream experiment parser has its own 64 KiB input bound; the effective policy must respect both limits. Task/capture model validation does not itself provide a bounded YAML reader. Unsupported schema/profile discriminators fail through RAES, with no fallback to generic assets. |
| Semantic references: `_validate_pack_core`, RAES experiment parser/models, family-selection and binding-target validators | Supply the validated task to the experiment parser; context-free parsing does not resolve its task reference. Resolve scenario, task, capture, binding-owner, model, and immutable prompt references using their upstream identity/version/digest rules and admitted local inputs. Missing, ambiguous, conflicting-path, stale, or mismatched references fail. Never fetch a URI, infer identity from a label, ignore a declared digest, or invent a digest convention when the upstream reference kind is unclear. |
| SDL and composition: `_parse_sdl_document`, `_validate_sdl_documents`, `digest._consumer_parent_candidates`, RAES `parse_sdl` / `parse_sdl_file` | Keep the authored family, expanded family, and selected scenario distinct. Preserve all alternatives and variation points; never replace authored family bytes with one selection. Consumer parsing continues to deny imports, network access, and cache writes. Trusted author CI keeps its separate file-backed resolution lane; experiment references do not grant consumer import authority. |
| Existing content joins: `_validate_content_set_inventory`, flag placement in `content_ci`, concept-binding admission under ADR 0038 | Structural treatments can remove nodes or change runtime inventory. Do not assume a base-family node exists in every selected scenario or validate only one convenient selection. Reuse RAES's selected-scenario semantics; retain existing inventory, placement, and digest-bound concept checks without rewriting their targets or silently dropping stale bindings. |
| Configuration and secrets: `_authoring_safety.admit_members`, materialization/kit parameter admission, RAES binding target/value models, compatibility/provenance schemas | Keep operator secret files and registry policy out of admitted local authoring inputs. Kit parameters remain bounded non-secret authoring scalars, not experiment bindings or environment configuration. RAES's typed binding sensitivity/ownership rules remain authoritative; a legal typed secret reference is not permission to resolve it, read the environment, or ship a credential. Do not add backend commands, collector import paths, host persistence paths, environment-variable keys, or secret-store coordinates to the portable pack. |
| Visibility: `_boundary_overlaps`, `content_ci.check_visibility`, `release._stage_views` and staged participant leak scan | Explicitly classify experiment/task/capture/prompt/manifests in existing artifact boundaries and provenance. Treatment labels and prompt content can reveal the experiment or participant answers. Directory placement and upstream sensitivity labels do not grant participant access. Keep restricted roots disjoint and scan actual participant exports. A split view must not claim a complete reloadable experiment while omitting its required inputs. |
| Content identity: `digest.py`, upstream associated-artifact models, `derive_pack_content_manifest`, `validate_pack_content_manifest` | Include every new input and prompt payload in the exact inventory, with canonical pack-local locators and verified sizes/checksums. Preserve immutable prompt references as well as their supplied bytes. The pack manifest remains scenario-scoped under ADR 0012; an experiment inside a pack does not change its parent to `experiment`. Preserve the unique-parent rule and single-open resolver budgets of ADR 0033. |
| Release and persistence: `release.build_release`, `_bind_view_sets`, `_publication_failures`, `distribution.stage_pack_archive`, `verify.verify_pack_release`, `_transactions` | Keep source-set and filtered-view identities separate. Use existing contained staging, fixed safe modes, cleanup, validation before promotion, and installed-byte verification. Reload from the actual staged/exported artifact; source-tree validity alone cannot prove a complete release. No new copier, archive extractor, cache, evidence store, or alternate promotion workflow. |
| Publication evidence: `publication.authored_artifact_requirements`, `component_boundary`, `sbom`, `release_provenance` | Exercise requirements/components carried by family alternatives and treatments, including changed configuration/model sources. Preserve compiled-address joins and ambiguity rejection; never key requirements by display label or collapse different alternatives into one selected source. Reuse existing inventory projections, recording unavailable authority honestly. SBOM, provenance, schema validity, and content digests are distinct claims and do not prove runtime success or authenticity. |
| Errors and observability: `Diagnostic`, `ValidationResult`, `_Errors`, `PackDigestError`, `check.py`, author-CI bounded process envelope | Adapt expected upstream failures to stable bounded codes and safe field locations. Never forward raw Pydantic/RAES exception prose, authored keys/target labels, prompt bodies, credentials, absolute paths, or command lines. Keep deterministic ordering and total diagnostic bounds. Library validation remains silent; programming defects still raise. Reuse CLI/JSON presentation and host envelopes rather than add an exception hierarchy or logger. |
| Authorization and host adapters: `AuthoringSession`, `_authoring_tools`, `mcp_server`, distribution promotion policy | No new auth surface is required. Existing read/check tools inherit shared validation. If an existing write path is touched, preserve controlled roots, operation grants, bounded arguments, exact proposal review, and apply authorization. Artifact ids, capture requirements, and apparatus identities are data, not capabilities. Do not widen MCP permissions or treat a valid experiment as publication approval. |

Preserve scalar types and RAES's discriminated literal/secret-reference binding
shapes; strings containing environment syntax are not permission to interpolate.
Use in-process owning validators. Existing author-CI subprocesses keep their argv sequences, deadlines, and output
limits. Prompt bodies, binding values, tokens, and secret references must not
enter process arguments or shell text.

Factorial expansion needs work bounds as well as file-size bounds: retain RAES's
condition/expanded-byte limits, and use its compilation limits for trial work.
Do not enumerate an unrestricted Cartesian product locally, multiply budgets
per reference or parent candidate, or promote full trial compilation into every
consumer ingest call. `validate_experiment_selection_against_family` explicitly
does **not** compile selected scenarios. Its success is necessary context checking,
not proof that all requested treatment combinations compile.

The validation/release contract must reject invalid requested combinations, not
merely demonstrate one valid compilation in a test. Use RAES's owning gates for
the declared effects and supplied manifest context. If the available gate needs runtime authority that a static pack cannot provide,
report that as an upstream validation-seam dependency. Do not fabricate
authority, silently skip the check, or implement local treatment semantics. A context-free shape check must never be
reported as complete experiment admission. Static validity, artifact byte binding,
and trial admission remain separate checks with explicit claims.

## Compatibility evidence and extension seam

The fixture must be a complete, synthetic pack artifact set, not disconnected
model-validation snippets. Exercise the released upstream compiler with supplied
apparatus and participant manifests, capture specs, and other required typed
compilation inputs. Runtime realization envelopes and execution authority used by
the test are trusted test context, not new pack-controlled runtime settings.
Check model/prompt bindings, scalar and structural selections, factor/condition
joins, node presence and configuration inventory, and immutable references after
release and reload. Renamed arbitrary labels and different author-declared
targets must still work; fixed strings such as particular model names or node
ids must not select validator behavior. Include invalid combinations, unresolved
and stale references, unsupported profiles, malformed inputs, and bounded
redacted failures. Do not fabricate upstream admissions to make compilation pass.

Build on `tests/test_validation.py`, `test_digest.py`,
`test_pack_artifact_resolver.py`, release/publication/verification tests,
`test_distribution_archive_safety.py`, and hosted-pack byte-binding tests.
`test_distribution_contents.py` already proves wheel/sdist content and installed
resource access outside the checkout. Extend that evidence for any shipped
fixture; a fixture only under `tests/` does not prove it is available in a wheel.
Use existing synthetic fixture helpers and temporary negative copies rather than
add another test runner or commit invalid packs. Compilation assertions must
check the actual treatment results, not just import success or a version string.

The extension seam is data: upstream document identities/references, declared
factor targets and levels, and caller-supplied manifest mappings and limits.
A second experiment, shared capture spec, or differently named model/prompt
target must need only ordinary authored data. It must not need a new schema,
selector branch, profile alias, or compatibility adapter. Keep pack member discovery and
containment shared; leave semantic dispatch to the RAES models.

## Whole-repository and release boundaries

The eventual diff must account for these areas:

- the shipped layout/template and public validation/release documentation;
- package APIs and CLI/MCP adapters;
- schemas and anti-extension guards;
- provenance and visibility;
- content identity, publication, SBOM, and release evidence;
- archive acquisition and verification; and
- installed wheel/sdist resources under `pyproject.toml`.

First-party reusable kits live under
`kits/`; major example packs live under `packs/`. A major shipped fixture must
participate in the existing explicit first-party gates, not just default
`environments/` discovery. Guidance here stays in developer docs under ADR 0030.

`pyproject.toml` owns the RAES minimum version and Python support;
`requirements/runtime.in` is its checked mirror, and `requirements/runtime.txt` and `uv.lock` are generated
dependency artifacts. If a different released RAES is needed, use the existing
lock-generation tools and dependency-policy tests, including co-installed tool
closures. No source patches, editable upstream checkout, monkeypatch, or Git
dependency can satisfy the released-package acceptance criterion.
Record the **tested and published** tuple: environment-pack package version,
RAES release, Python support, layout contract, fixture pack version, and released
artifact identity. The preflight baseline tuple above is not that evidence.

Use the existing CI `verify` aggregate, dependency audit, content gates,
workflow-permission/pinning tests, and `AGENTS.md` completion checks. Both
`--repo .`/`check --all` and explicit `--packs-root packs` lanes are required.
Release-please owns versions and `CHANGELOG.md`; feature PRs squash, dev-to-main
promotions use `make devmain` and merge commits, and human merge gates remain.
A release-producing implementation and compatible published package **and**
pack artifact are needed; a guidance PR or green source tests do not deliver #504.

Non-goals are experiment execution, scheduling, collectors, result/evidence
persistence, scoring, new RAES semantics, generic plugin/hook systems, backend
capability claims, new hosting, and release-workflow redesign. Do not conflate a factorial profile with delivery bundles, runtime profiles,
publication views, or kit parameter variation. Do not preselect a family to
avoid validation failures.
Any missing owning validator or unresolved upstream contract is an upstream
dependency gap, not permission for a local schema or success-shaped fallback.

## Design Vocabulary That Applies

- **RAES-subordinate pack tooling**: environment-pack layout and shared
  authoring/validation/release tooling; see
  [environment packs](../public/environment-packs.md).
- **Boundary contract**: RAES owns SDL, experiment, capture, evidence, and
  participant/attacker semantics. This repository carries authored inputs and
  owns pack layout/tooling, with zero semantic extensions.
- **Binding ADR-036**: first-party kits and major example packs publish here
  under `kits/` and `packs/`; co-location leaves semantics with RAES.
- **Applicable anti-recommendations**: consume RAES schemas/validators rather
  than redefine semantics, and keep downstream catalog vocabulary out of
  canonical pack contracts. The supplied vocabulary names no canonical helper;
  the reuse table above identifies the inspected incumbents.
