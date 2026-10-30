# Released RAES dependent-declaration variations

Issue #526 requires ordinary installation with a released RAES containing
OpenRAE/rae#1733 and successful pack content checks for its new targets.
This is dependency compatibility in RAES-subordinate pack tooling. Existing
ADRs cover the design; no new ADR or compatibility framework is needed.

## Dependency and release contract

The issue's exact-pin premise predates
[ADR 0043](../decisions/adrs/0043-require-a-minimum-raes-version.md).
At preflight, `pyproject.toml` and `requirements/runtime.in` declare
`raes>=9.2.0`; `requirements/runtime.txt` and `uv.lock` resolve RAES 9.2.0.
The release containing #1733 has not been established by this review.
Do not infer it from an issue number, merge status, or version ordering.
Native GitHub blocked-by relationships remain the dependency authority.

Preserve the minimum-version declaration. Its floor is the oldest release
supplying every RAES API the package uses; raise it when the change requires
a newer release. A consumer choosing a newer RAES and CI testing that release
are separate claims. Existing published metadata may already permit the
required installation; determine that before assuming a metadata change or
new package release is necessary. Historical exact-pin preflights do not
override ADR 0043.

`pyproject.toml` owns distributed dependencies and Python support
(`>=3.14,<3.15`); `requirements/runtime.in` is its checked mirror.
Generate locks using the existing tools and recorded command headers. Preserve
hash verification, upstream governed pins, and agreement between co-installed
locks, including the SBOM tool closure. Do not hand-edit hashes or use Git/path
RAES dependencies, extra indexes, overrides, prereleases, or resolver bypasses
to stand in for a released dependency. Retain unrelated versions where possible.

Record the capable upstream release and built wheel's `Requires-Dist` and
`Requires-Python`. Ordinary resolution must install that wheel together with
the capable released RAES in a clean supported environment, without
`--no-deps`. The existing hash-locked CI install and
`tests/test_distribution_contents.py` installed-resource check use
`--no-deps`; neither alone proves this acceptance criterion.

Release Please owns the project version and changelog. A runtime dependency
fix uses the existing `fix(deps):` release convention. Reuse
`.github/workflows/release-please.yml` and `tools/release_tag_gate.py` for signed
tags, build attestations, CycloneDX SBOMs, and trusted PyPI publication.
A merged change or successful local build is not evidence of publication.
No publication or protected-branch merge is authorized by this preflight.

## Validation and security layers to preserve

| Layer and canonical incumbent | Guardrail |
| --- | --- |
| Pack reads: `_pack_fs`, `PackValidationLimits` | Keep descriptor-anchored no-follow reads, canonical relative paths, link/special-file rejection, byte/member/parser limits, and change detection. Unsupported descriptor platforms fail closed. |
| Pack configuration: `validation._validate_pack_core`, strict YAML/JSON loaders, packaged provenance/compatibility/materialization schemas | Preserve duplicate-key rejection, closed shapes, provenance safety/review gates, visibility joins, and content inventory checks. The new targets belong in RAES SDL, not pack schemas. |
| SDL authority: `validation._parse_sdl_document`, RAES `parse_sdl` / `parse_sdl_file`, `SDLError` | Consume released upstream target shapes and semantic checks. Retain parser limits and `migration_policy="accept"`; do not add a pre-parser, local dependency graph, pruning pass, monkeypatch, or fallback accepting rejected SDL. |
| Experiment admission: `_experiment_set`, RAES `admit_scenario_family`, `ExpandedScenarioBindingTargetResolver`, `validate_experiment_selection_against_family` | Preserve family admission, selection/treatment/binding checks and canonical references. A valid individual target does not prove that a selected combination is valid. Reuse the RAES trial compiler with supplied trusted context for compilation evidence; static validation does not grant runtime authority. |
| Consumer versus author workflow: `validate_pack`, `_validate_pack_for_author_ci`, `content_ci` | Consumers remain silent and do not execute pack code, resolve imports, access the network, or write resolver caches. Author CI retains file-backed parsing and trusted validators/tests under its existing discovery policy, argv runner, process-group deadline, and output bounds. It is not a sandbox for foreign packs. |
| Secrets, bindings, and host access: `validation` materialization checks, `_authoring_safety`, `kit_cli._parameters`, `AuthoringSession`, `mcp_server` | No new credentials, environment interpolation, host grants, request fields, or transport. Retain secret admission, non-secret scalar parameters, rejection of environment coordinates, typed upstream literal/secret-reference shapes, bounded stdin, and prepare/apply authorization. Keep credentials and authored payloads out of argv and shell text. |
| Errors and observability: `Diagnostic`, `ValidationResult`, `_Errors`, `check` renderers, existing domain errors and host envelopes | Keep deterministic bounded codes and locations, terminal-safe presentation, and silent libraries. Do not expose raw upstream exception prose, SDL, secrets, or absolute paths. Expected input failures retain existing mappings; programming defects must not be swallowed by a catch-all compatibility handler. No new exception or logging hierarchy. |
| Identity and persistence: `digest`, concept-binding admission, `tools/refresh_pack_sdl_binding.py`, release/publication/verification checks, `_transactions` | Preserve byte inventories, canonical SDL parents, digests, scheme/binding admission, and atomic authoring writes. Node absence in a selected scenario does not authorize deleting packaged files, provenance, or family declarations. Investigate changed canonical identities before refreshing evidence; a dependency bump alone does not justify rewriting immutable kits. No new cache, database, receipt, or runtime store. |
| Supply chain and workflow: dependency policy tests, `.github/workflows/ci.yml`, `fuzz.yml`, `pack-distribution.yml`, `release-please.yml`, `.github/dependabot.yml` | Keep supported Python/runtime metadata aligned, generated dependency closures coherent, hash-locked installs, vulnerability audit, pinned actions, least-privilege tokens, and fail-closed `verify`. Use existing approved destinations and publication credentials only. Read the co-install groups from workflows rather than inventing another dependency list. |

## Compatibility evidence and extension seam

Reuse the temporary synthetic pack helpers in `tests/test_validation.py` and
`tests/test_content_ci.py`; `tests/test_pack_experiments.py` already covers
structural selections, renamed targets, invalid combinations, compilation,
and archive/reload. The regression must exercise real pack validation and the
`raes-pack-validate --pack` entry point with the capable released RAES, not just
a parser import, mocked success, or version assertion.

Cover a node-absent selection together with the dependent declarations supported
by the released upstream contract, and the corresponding node-present case.
Include an unresolved target and an invalid dependent selection/combination
that upstream rejects. Check actual selected results through upstream APIs
where needed; do not assume absent-node handling automatically removes every
dependent declaration. Do not invent upstream slot names before the release is
identified or duplicate its complete semantic test suite here.

The existing `test_an_invalid_requested_combination_rejects_the_whole_design`
deliberately passes static pack validation, then fails trial compilation when
content still targets the absent node. Assert rejection at the owning layer.
Content-check success alone does not prove the dependent effects work; preserve
that distinction without moving full trial compilation into consumer ingest or
enumerating an unbounded Cartesian product locally.

The extension seam is authored RAES target/selection data and existing
caller-supplied parser/compilation limits, not a pack-side target registry.
Renamed nodes and the next upstream dependent-target kind should require no
new dispatch branch here. Dependency tests should assert minimum-version and
lock invariants rather than hard-code the chosen release number.

The whole-repository compatibility surface includes public validation/check
APIs, CLI/MCP adapters, family/experiment admission, artifact and concept
bindings, catalog/kit composition, release/publication/verification, and bundled
wheel/sdist resources. Reuse their existing tests and every verification gate
in `AGENTS.md`, including explicit `--packs-root packs` checks: default repository
discovery can pass with no releasable packs and does not cover first-party packs.
Installed metadata and the editable-project entry in `uv.lock` can lag
`pyproject.toml`; build acceptance
evidence from the candidate artifact, without hand-bumping the project version.

## Non-goals

RAES owns dependent-declaration semantics, SDL models, target resolution, and
trial compilation. This change does not introduce local equivalents, a pack
layout revision, new runtime/backend behavior, or a new publisher. It does not
modify an external consumer pack or import downstream catalog vocabulary into
canonical contracts. First-party kits and examples retain their roles under
[ADR 0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md).
