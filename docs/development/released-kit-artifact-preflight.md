# Released kit artifact guardrails (#415)

Issue #415 requires a pinned, released kit collection obtainable without a Git
checkout, with a digest for each kit. Prefer package data in `raes-env-packs`:
the existing Hatch build and release workflow already distribute first-party
example packs. A separate archive, publisher, or registry is unnecessary for
this scope. This is design guidance; the issue is not implemented here.

[ADR 0002](../decisions/adrs/0002-distribute-as-installable-package.md),
[ADR 0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md),
and [ADR 0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
already establish the package-resource, kit, and first-party-content boundaries.
[ADR 0041](../decisions/adrs/0041-distribute-kits-as-package-resources.md)
records the installed-source accessor and package-release revision form. No new
portable schema is needed.

## Carrier, identity, and consumer boundary

The inspected `pyproject.toml` includes example packs through wheel
`force-include` and explicit sdist inputs, but includes `kits/` in neither.
Carry the complete canonical `kits/<id>/<version>/` tree as package resources,
including historical versions, manifests, modules, assets, documentation, and
test declarations. Keep `kits/` the sole authored source; do not maintain a
second copy under `src/`, select only the newest releases, or rewrite YAML/JSON
during the build. Exclude caches and operator files rather than silently
altering the inventory bound by a kit's manifest. Invalid releases must fail
validation, not be dropped or repaired at packaging time.

All bundled bytes are accessible to whoever acquires the distribution.
An asset's `operator` visibility governs later pack projections; it does not
make package data confidential. Preserve licensing, attribution, and public
redistribution review. Kit-schema admission also supports private catalogs and
is not, by itself, permission to publish restricted content.
All 136 releases currently declare MIT and `redistribution: open`. Keep a
package-publication gate that rejects any canonical release not cleared for
redistribution. Do not silently omit a restricted release: that would make the
released collection differ from the canonical collection while still appearing
complete. Restricted content belongs in a separately admitted source, not in
this public package tree.

Wheel and sdist must carry identical kit payload bytes. A wheel rebuilt from
the sdist must contain the same complete kit tree as a direct wheel build;
testing two independent builds from the checkout misses a missing sdist input.
This concerns payload equality, not an assertion that ZIP/tar carrier bytes
are identical. Existing example-pack resources must remain complete too.

Use the existing RAES-associated identity:
`load_kit_release(path).associated_artifacts.set_digest`. That loader checks
the manifest's exact inventory, payload checksums and sizes, semantic parent,
and set digest. A copied `set_digest` string alone is not verification. Keep
these claims distinct:

| Value | Meaning |
| --- | --- |
| Exact `raes-env-packs` release and acquired wheel/sdist hash | Collection selection and transport integrity |
| Kit id and independent kit version | Selection within that collection |
| Validated associated-artifact set digest | Kit content identity, including its bound module and supporting files |
| RAES semantic/module digest | Module identity, not the entire kit |
| Existing distribution build attestation | Origin of the distribution; a content digest alone proves no authenticity |

Every kit already carries its digest in `associated-artifacts.json`. Document
how a consumer obtains and verifies it through the existing loader. Do not add
a checksum algorithm, directory hash, checksum sidecar, or collection lock.
`inspect_kit()` and the closed `kit-catalog.schema.yaml` currently do not expose
the set digest. Do not inject a field into catalog JSON without its matching
contract change; #415 does not require that schema expansion.

Resolve installed resources through `importlib.resources` under ADR 0002, but
admit only a filesystem-backed resource tree. The source root supplied to
`KitSource` must **contain** `kits/`, rather than point at an individual kit or
at `kits/` itself. Discovery, inspection, and composition continue through
`build_kit_catalog`, `source_release`, and the existing proposal APIs. Reading
installed resources must work from an unrelated working directory without
`.git`, a repository-relative fallback, network access, temporary extraction,
or writes to site-packages. ADR 0041's `bundled_kit_source()` remains a thin
adapter to `KitSource`, with no second discovery or validation implementation.

Keep source id/revision traceable to the acquired immutable release. ADR 0041
uses `openrae-env-packs` and `raes-env-packs==<installed-version>` for a normal
filesystem installation; checkout and third-party sources retain explicit
caller-supplied revisions. The attested source commit remains a distinct fact.
Do not infer provenance from ambient `HEAD`, a directory name, a mutable tag,
or the installed package version of an editable checkout. Package version,
source revision, kit version, and content digest remain separate. The caller
admits the source; a revision label is not evidence that its bytes were verified.
ADR 0041 supersedes ADR 0036's Git-only revision rule for installed first-party
kits; preserve the original accepted ADR rather than editing it in place.
Installed metadata remains the version authority used by `__init__.py`.
That module imports `kits` before assigning `__version__`; accessor wiring must
avoid introducing an import cycle or a second version constant.

## Cross-cutting layers and canonical incumbents

Paths below are relative to `src/raes_env_packs/` unless stated otherwise.

| Layer and incumbent | Required treatment |
| --- | --- |
| Build/configuration: `pyproject.toml`, `requirements/build.in` / `build.txt`, `tests/test_distribution_contents.py` | Reuse Hatch's resource mapping and sdist selection. Include future kit families and versions without another per-kit packaging entry. Keep the locked build backend, `--no-isolation`, and Python compatibility floor. No custom build hook or dependency is justified by copying data. |
| Safe filesystem and admission: `_pack_fs`, `_authoring_safety.admit_members`, `KitLimits`, kits `_validate_source`, `load_kit_release` | Preserve bounded non-secret source metadata, descriptor-relative no-follow reads, regular-file admission, canonical paths, collision detection, link/special-file rejection, inventory rechecks, and member/byte/parser bounds. Packaging data does not make these gates optional. Secret-file and `raes-trust.yaml` rejection happens before content reads. |
| Shape and semantics: `validate_kit_document`, kit `_strict_yaml`, `validation._StrictLoader` / `_check_yaml_events`, `resources/schemas/kit.schema.yaml`, public APIs of the exact RAES pin | Reuse closed kit fields, duplicate-key rejection, bounded parsing, infrastructure-only admission, and kit/module version agreement. RAES owns SDL, exports, parameters, imports, locks, and semantic identity. A kit is not a pack: do not force it through the `pack.yaml` contract or duplicate semantic validation. |
| Integrity: `kits._load_release_manifest` through `load_kit_release`, public RAES associated-artifact loader/validator | Verify the released bytes against the existing parent, exact member set, checksum, size, and set-digest contract. Preserve the manifest carrier's exclusion from its own payload set. Never recompute a bad manifest during consumer verification or substitute a wheel `RECORD` hash for kit identity. |
| Execution boundary: `load_kit_release`, `validation`, `content_ci` | Consumer inspection remains import-denying, networkless, and non-executing. Trusted author CI is the separate lane that may execute pack-local validators/tests. Shipping kit test declarations does not authorize running them during installation or inspection. Materialized assets retain the existing non-executable destination allowlist. |
| Secrets, environment bindings, licensing, and OS exposure: `admit_members`, kit manifest/parameter secret checks, kit `license.redistribution`, `kit_cli._parameters` | Ship only admitted, publicly redistributable content. Reject restricted releases at the package-publication boundary without changing the reusable kit schema. No credentials, real private data, signed URLs, operator trust files, environment-variable coordinates, new env-binding shape, shell interpolation, or executable install hooks. These checks do not scan every arbitrary payload string; retain content review. Public parameter documents remain bounded stdin input, not values in argv. |
| Host authentication/authorization: `authoring.AuthoringSession`, `_trusted_root`, `_bounded`, `_authoring_tools.TOOLS`, `mcp_server` | A bundled source may be admitted by the host through the existing source handles; it grants no additional root access, preparation, or apply rights. Preserve closed request shapes, output/secret limits, review binding, and explicit write grants. No new endpoint or automatic MCP source admission is required. |
| Persistence and materialization: `KitSource`, `propose_*`, `apply_proposal`, `_transactions`, `validation.validate_kit_materializations_document` | Resources are read-only authoring inputs, not a cache or database. Retain the existing ownership ledger, RAES lock, full-successor validation, concurrent-change checks, atomic promotion, and recovery preservation when composing a pack. Keep safe fixed modes. Unsupported descriptor/transaction platforms still fail closed; wheel portability is not a promise of universal OS support. |
| Component inventory and publication: `component_boundary.KitSourceResolver`, `release._default_kit_source_resolver`, existing SBOM/provenance gates | The resolver already accepts an explicit staged source root. Do not add a second resolver or silently replace the recorded source/revision with the installed collection merely because id/version exists. The current default resolver checks only directory presence and is not provenance evidence. Unavailable historical sources remain unavailable. Distribution SBOM/attestations do not certify realized kit services or resolve their external/unresolved components. |
| Errors and observability: `KitError` / `KitRecoveryError`, `validation.Diagnostic`, `kit_cli`, `authoring._safe_diagnostics` | Keep silent libraries, bounded value-free errors, terminal-safe text, CLI outcomes `0`/`1`/`2`/`3`, and existing host envelopes/audit responsibility. Missing package resources must fail clearly; no silent checkout fallback or partial catalog. Do not add an exception hierarchy/logger or expose payloads, absolute installation paths, parser prose, credentials, or subprocess output in errors. |
| Release/workflow: `.github/workflows/release-please.yml`, `ci.yml`, `.gc/plan-rules.md`, `tests/test_dependency_pinning.py`, `test_workflow_permissions.py`, release attestation/tag tests | Reuse the authorized release target, hash-locked tooling, least-privilege job permissions, pinned actions, signed tags, OIDC PyPI publication, and existing wheel/sdist attestations. Preserve the fail-closed `verify` aggregate. No parallel publisher, new destination, or manual version/changelog edit. The content-shipping change adds a public consumer capability, so `feat:` is the appropriate release-producing title; `build:` alone produces no release. |

## Extension seam and acceptance evidence

The existing seam is `KitSource(id, revision, root)` over an ordinary staged
collection. Keep explicit roots for third-party and historical catalogs; any
installed-resource convenience belongs only at source selection. Do not make
the installed first-party collection an implicit override of a caller's source.
The current descriptor-anchored reader requires a real filesystem root. If the
package resource does not provide one, fail with `KitError`; do not create a
temporary extraction lifecycle or widen `KitSource` for this issue. Include the
whole `kits/` tree so future kit families and versions need no packaging edit.

Extend the existing distribution-content tests for exact, non-empty release
membership and payload equality. Demonstrate the sdist rebuild and a fresh
non-editable wheel installation outside the checkout, with no source-tree
`PYTHONPATH` or runtime Git command. From that installation, discover the
collection and validate **every** kit/digest through `load_kit_release`; use
existing kit/CLI tests for representative inspection and composition. Missing,
extra, and changed payloads must still fail the existing integrity boundary.
Discover membership rather than copying the present release count into build
configuration. Keep read-only installed data usable without generating cache
files inside it. An editable install or a wheel member-name assertion alone
does not prove the consumer contract.

Local artifact tests prove the release is buildable, not that it has been
released. Issue acceptance also requires the resulting version to pass the same
installed-consumer check after publication through the existing release route.

The repository's required unittest, content, release, and compile gates remain
mandatory. `tests/test_published_kits.py` validates checkout releases and
parameter variation, but does not prove installed artifact availability.
`tests_integration/kit_author_walkthrough.py` sets source-tree `PYTHONPATH`, so
it also cannot supply that proof. Public instructions in `docs/public/kits.md`
must eventually describe the released route alongside explicit local sources;
keep this maintainer note outside the public documentation source root.

## Non-goals

No RAES semantics, kit-content corrections, historical-release rewrites,
backend provisioning, service readiness, OCI workflow, kit acquisition service,
new catalog/lock/SBOM schema, plugin mechanism, runtime kit API, or new trust
policy. This preflight changes guidance only; it does not change packaging,
publish an artifact, update consumers, or claim that #415's release acceptance
has already been demonstrated.
