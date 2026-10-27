# Released RAES consumer compatibility preflight

Issue #514 makes `raes-env-packs` installable alongside released RAES 8.1.0.
Treat it as a reviewed runtime dependency fix under ADRs 0011 and 0016.
Existing architecture covers the change; no new ADR or compatibility framework
is needed. This note records design constraints, not implementation steps.

## Authorities and scope

`pyproject.toml` `[project].dependencies` owns the exact RAES pin.
`requirements/runtime.in` is its checked mirror for Dependabot, and
`requirements/runtime.txt` is the generated, hash-locked CI/runtime closure.
Its header records the existing `uv pip compile --generate-hashes` invocation
and Python target. `uv.lock` is the other generated dependency artifact.
Regenerate these through their existing tools, including the editable project's
metadata; do not patch hashes, URLs, or resolved versions by hand.

At preflight, the declared dependency is 8.0.0, the package version is 6.4.0,
and `uv.lock` still records editable-project version 6.3.4. Refreshing generated
or installed metadata must follow `pyproject.toml`; it does not authorize editing
the release-please-owned project version. The dependency comment referring to
the "7.x SDL contract corpus" is stale explanatory text, not another authority.
ADRs and historical preflights remain dated records, not version mirrors.

RAES owns the new public runtime-descendant and materialization-attestation
contracts. Consume their released public exports directly. Keep these distinct:

- `kit.materializations.json` records authoring inputs and file ownership under
  ADR 0035; it is neither runtime evidence nor a replacement RAES module lock.
- Pack SBOMs, `release_provenance.py`, and publication profiles describe a pack
  release. They do not attest a backend's realized environment.
- Python wheel/sdist build attestations describe distribution provenance.
  Neither those nor the RAES dependency version prove runtime conformance.

No new fields in pack schemas, mirrored RAES models, wrapper contracts,
attestation store, or downstream runtime behavior follow from this dependency
update. LilRAE integration remains outside this repository.

## Cross-cutting layers and required reuse

| Layer and canonical incumbent | Constraint for this change |
| --- | --- |
| Dependency and configuration policy: `pyproject.toml`, `requirements/*.in` / `*.txt`, `uv.lock`, `.github/dependabot.yml`, `tests/test_dependency_pinning.py`, `tests/test_package_metadata.py` | Retain one exact RAES requirement. Generate real release hashes and satisfy the declared Python floor. Locks installed into the same workflow environment must agree on shared packages; regenerate affected companions only as required by the resolved closure. Preserve governed upstream pins such as `z3-solver`. Do not solve drift by broadening the RAES requirement, adding an override, or replacing the release with a Git/path dependency. |
| Pack configuration and SDL validation: `validation.validate_pack`, `PackValidationLimits`, strict YAML/JSON loaders, packaged compatibility/provenance/materialization schemas, RAES `parse_sdl` / `parse_sdl_file` | Keep closed shapes, duplicate-key rejection, bounded parsing, concept-binding admission, visibility joins, safety attestations, and provenance review gates. RAES remains the SDL and semantic authority. Existing `migration_policy="accept"` is an explicit incumbent policy, not permission to weaken semantic checks or suppress new errors. No local SDL pre-parser or second schema. |
| Consumer versus author execution: `validation._validate_pack_core`, `_validate_pack_for_author_ci`, `content_ci`, `digest._consumer_parent_candidates` | Consumer validation and artifact resolution use bounded content parsing with imports denied, no network/cache writes, and no pack-local execution. Author CI retains file-backed parsing and separately trusted pack validators/tests. Preserve that separation even if the new RAES release exposes additional resolver options. Upstream owns module resolution and trust policy. |
| Filesystem and artifact identity: `_pack_fs`, `digest.validate_pack_content_manifest`, `resolve_pack_artifact`, `kits.load_kit_release`, RAES associated-artifact loaders/validators | Retain descriptor-anchored no-follow reads, canonical paths, member/byte limits, race checks, exact inventory, sizes, checksums, semantic parent, and set digest. Unsafe links/special files and unsupported descriptor platforms fail closed. Existing fixture manifests must still validate; do not regenerate identity merely to erase a regression. Investigate any changed canonical digest before changing content. |
| Secrets, environment-binding shapes, and OS exposure: `_authoring_safety.admit_members`, kit manifest/parameter checks, `validation` ledger checks, `publication` availability validation, `kit_cli._parameters`, `content_ci` process runner | Retain sensitive-member admission, non-secret scalar parameters, rejection of environment-variable coordinates and credential-bearing locations, bounded duplicate-free stdin JSON, and argv-sequence subprocesses. No new environment binding or credential input is needed. Keep secrets and SDL bodies out of argv, shell interpolation, errors, and logs. Author code runs only in its existing trusted, least-privilege lane. |
| Host authorization and transport: `authoring.AuthoringSession`, `_trusted_root`, `_bounded`, `_authoring_tools.TOOLS`, `mcp_server` | Dependency compatibility grants no new root, tool, prepare/apply permission, or trusted source. Preserve closed request schemas, explicit host grants, session/proposal binding, bounded secret-checked output, and the local stdio transport. No new endpoint or authentication mechanism. |
| Persistence and authoring: `KitSource`, `bundled_kit_source`, `kits.propose_*` / `apply_proposal`, `validation.validate_kit_materializations_document`, `_transactions` | Bundled resources remain read-only inputs with no checkout fallback or extraction cache. Kit operations retain RAES lock authority, explicit file ownership, successor validation, concurrent-change checks, atomic promotion, and recovery preservation. No database, runtime attestation persistence, or new transaction machinery. |
| Errors and observability: RAES `SDLError`, `validation.Diagnostic` / `ValidationResult`, `PackDigestError`, `KitError` / `KitRecoveryError`, publication diagnostics, `authoring._safe_diagnostics`, existing CLI/host envelopes | Keep silent libraries, deterministic bounded codes/locations, terminal-safe output, existing status/exit conventions, and host-owned redacted audit storage. Preserve upstream error versus advisory severity. Never expose raw parser/exception prose, source payloads, credentials, or absolute host paths through consumer envelopes. Unexpected package defects must remain distinguishable from malformed input; no catch-all compatibility fallback or parallel exception/logger hierarchy. |
| Inventory, supply chain, and workflow: `component_boundary`, `publication`, `sbom`, `release_provenance`, `verify`, `.github/workflows/ci.yml`, `release-please.yml`, `tools/release_tag_gate.py` | Reuse upstream identity/addressing/mechanism models and existing inventory/evidence gates. Retain hash-locked installation, vulnerability audit, pinned actions, least-privilege tokens, fail-closed `verify`, authorized release detection, signed tags, wheel/sdist provenance, CycloneDX generation, and OIDC PyPI publication. Package dependency inventory and pack component inventory remain distinct. No new publisher or destination. |

## Compatibility evidence and extension seams

Acceptance evidence must identify the installed RAES distribution/version and
its released wheel, plus the candidate package's `Requires-Dist`. A normal
consumer dependency resolution must install both together without an override,
source patch, or editable RAES checkout. The canonical CI pattern still installs
the hash-locked dependency closure before installing the local package with
`--no-deps`; that alone is not evidence of ordinary consumer resolution.

Review the released wheel's `Requires-Python` and dependency metadata against
the project's declared Python floor and CI interpreter. A lock generated for
CI's Python 3.14 does not prove compatibility at the declared Python 3.11 floor.
The runtime lock also feeds `fuzz.yml`, `pack-distribution.yml`, and release SBOM
generation. Read the co-installation groups from the existing workflows; the
separate documentation toolchain is not a reason to refresh unrelated locks.

Build on the existing tests rather than add another compatibility runner:

- `test_validation`, `test_digest`, `test_pack_artifact_resolver`, publication,
  verification, and concept-alignment tests cover the public consumer boundary,
  including rejection behavior and bounded diagnostics.
- `test_published_kits` exercises every release and parameter variation;
  `test_kit_compute_substrate` checks compiler/planner compatibility, and
  `test_kit_materialization` covers lock/ownership/transaction behavior.
  Hosted-pack binding and first-party pack tests cover the existing examples.
- `test_distribution_contents` already builds the sdist-derived wheel, compares
  exact shipped content, and exercises public bundled-kit APIs outside the
  checkout. Preserve that installed-artifact evidence. Its consumer process
  uses the test interpreter's installed dependency closure, so it proves 8.1.0
  compatibility only when that closure actually contains the released wheel.
- A focused compatibility check should exercise the new upstream public
  runtime-descendant and materialization-attestation surface that motivates
  #514. Use RAES public models/helpers and a small synthetic example; assert
  usable behavior rather than only import success or a version string. Do not
  reproduce upstream's conformance suite or implement a backend here.

Run the complete verification contract in `AGENTS.md`, including both
`--repo .` and explicit `--packs-root packs` gates. The former defaults to the
external `environments/` layout and does not establish first-party coverage.
CI's audit and all mandatory `verify` jobs remain required. A preflight baseline
on 8.0.0 does not establish compatibility with 8.1.0.

The local 8.0.0 baseline passed all four pack validation/release commands and
compilation. The full unit run stalled in
`test_mcp_server.StdioTests.test_frame_reader_stops_before_reading_an_unbounded_line`;
an isolated run also hit a 20-second diagnostic timeout. The full run was
interrupted. Its cause remains unresolved; do not classify it as an 8.1.0
regression or suppress the test to obtain a green dependency update.

The next dependency update belongs at the same metadata/generation seam.
Keep tests about the exact-pin invariant derived from project metadata; do not
hard-code the new version throughout tests or general documentation. Keep
caller resource budgets in `PackValidationLimits` / `KitLimits`, source choice
in `KitSource`, and trusted resolver policy in its existing authoring lane.
No version-dispatch adapter, feature-flag matrix, or automatic capability probe
is needed for a release that supports one exactly pinned RAES runtime.

## Release and non-goals

Use a release-producing `fix(deps):` title under ADR 0016. A `chore:` or `build:`
title alone would leave consumers without the compatible release required by
the issue. Release-please owns `[project].version`, `.release-please-manifest.json`,
and `CHANGELOG.md`. Human merges remain required by ADR 0020. Feature PRs use
squash merges; `make devmain` promotions use merge commits under ADR 0019.
Completion requires the compatible artifact to be published through the existing
release workflow; a green dependency PR alone does not satisfy publication.

This preflight changes guidance only. Implementation is limited to dependency
metadata, generated dependency artifacts, compatibility evidence, and any
demonstrated minimal adaptation to the released public API. It excludes RAES
semantics, new pack/kit formats, scenario redesign, historical kit rewrites,
backend execution, LilRAE changes, new services or hosting, release-workflow
redesign, manual publication, and bypasses of human merge approval.

## Design Vocabulary That Applies

- **RAES-subordinate pack tooling**: reuse environment-pack validation,
  authoring, packaging, and release tooling; see
  [environment-packs](../public/environment-packs.md).
- **Boundary contract**: RAES owns SDL and scenario/runtime semantics; this
  repository owns pack layout/tooling and its first-party content. Updating
  the consumed dependency introduces zero RAES semantic extensions here.
- **Binding ADR-036**: first-party kits under `kits/` and major example packs
  under `packs/` participate in compatibility verification; RAES keeps semantic
  authority. ADR 0041 governs their installed-resource distribution.
- **Applicable anti-recommendations**: do not define or extend RAES semantics
  or duplicate upstream contracts/validation; do not import downstream catalog
  vocabulary into canonical pack contracts or validation exceptions.

The target release is available as a
[published RAES 8.1.0 wheel](https://pypi.org/project/raes/8.1.0/).
This note does not claim that its compatibility checks have already passed.
