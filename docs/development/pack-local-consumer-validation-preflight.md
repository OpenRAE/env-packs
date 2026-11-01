# Pack-local consumer validation preflight

Issue #412 needs a public consumer check that accepts kit-generated local SDL
imports, requires their digest pins and lock records, and remains inert.
The change belongs in the shared pack validator, with composition delegated to
RAES. **The installed RAES 10.0.0 public parser lacks the required consumer
resolver seam.** Enabling the existing author parser is not a safe substitute.
This record supplies design guardrails, not an implementation plan or a claim
that the new check exists.

RAES 10.2.0 adds the required seam as `parse_sdl_sources()` (OpenRAE/rae issue
1757). The [design](pack-local-consumer-validation-design.md) uses it.
The maintainer chose default admission of pinned local imports, not a
keyword-only policy (ADR 0046).

## Existing contracts and the dependency gap

`kits._stage_import_locks` already writes a `local:` import with a SHA-256 digest
of the module's exact bytes. `kits._lock_bytes` uses public
`raes.module_registry.resolve_lock_records` with an explicit empty-registry
`TrustPolicy`; `kits._lock_path` places `raes.lock.json` beside the importing SDL.
The materialization ledger records ownership and provenance, not dependencies.

`validation._validate_pack_core` is the shared static authority.
`validate_pack()` uses bounded descriptor reads and content-only `parse_sdl`;
`_validate_pack_for_author_ci` enables `parse_sdl_file`. The latter may load
workspace policy and resolve imports. Its use by authoring does not authorize
it at an untrusted consumer boundary.

Inspection of the repository-local installed RAES 10.0.0 sources establishes:

- Public `parse_sdl` with a path and `parse_sdl_file` compose through workspace
  lock/trust discovery and pathname reads. Supplying a path is enough to enable
  resolution; it is not merely diagnostic context.
- Local resolution checks an import digest and a matching lock digest **when
  supplied**. Neither a pin nor a matching record is required. Loading a
  `Lockfile` model alone does not prove coverage, uniqueness, or byte identity.
- `resolve_lock_records` records direct imports of one root. It is not a
  transitive consumer-admission check. Local expansion consults workspace
  configuration again in imported directories.
- The public language-service path mode avoids registry fetching but returns
  editor diagnostics, still reads workspace files, and supplies no admitted
  scenario plus safe-reader contract. Private composition traversal and
  verified-source machinery are not supported consumer interfaces.

[ADR 0013](../decisions/adrs/0013-separate-consumer-static-validation-from-author-ci.md)
already makes a public RAES resolver seam the prerequisite for relaxing import
denial. [ADR 0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md)
also forbids a local replacement resolver or private RAES calls. Neither ADR
needs rewriting. A released public upstream operation must accept explicit
consumer policy and supplied, bounded source/lock bytes without ambient
discovery, support the full import closure, and return a semantically validated
RAES object or structured failure. Missing capability remains an upstream
dependency; do not catch it and fall back to author parsing.

## Public boundary and extension seam

Keep `validate_pack()` and `ValidationResult` as the public entry and result.
Preserve import denial by default; admit pinned, locked pack-local imports
through an explicit keyword-only consumer import policy on the same shared
core. Do not expose `author_sdl`, execution, or arbitrary trust-policy options.
This preserves existing callers and lets consumers select the new public check
without private helpers. Invalid policy values are invocation errors, not pack
diagnostics. No generic resolver/plugin registry or new configuration document
is needed.

The policy is independent of `PackValidationLimits`. Reuse its metadata/member/
SDL/diagnostic limits and `limits.sdl` composition budgets, including imports,
depth, composed nodes, and total composed bytes. Any additional aggregate read
budget belongs in the existing limits policy, not a second limits hierarchy.
Do not reset a graph budget per recursive import or multiply it by repeated
references; bound total work across direct roots as well.

The upstream public resolver/reader contract is the seam for future source
carriers. Env-packs supplies contained bytes; RAES owns import normalization,
module declarations, version/parameter/export/namespace checks, cycles, lock
semantics, composition, and final semantic validation. A future source kind
requires deliberate admission policy; it cannot become enabled by installing a
newer dependency, finding cached content, or adding a pack trust file.

Under [ADR 0043](../decisions/adrs/0043-require-a-minimum-raes-version.md), raise
the RAES floor in `pyproject.toml` and `requirements/runtime.in` if the new public
API requires it. Generated, hash-locked `requirements/*.txt` and `uv.lock`, the
Python compatibility contract, and dependency-pinning tests must agree with the
released API used. Do not guess a future version or vendor upstream internals.

## Cross-cutting gates

| Layer and canonical incumbent | Required property |
| --- | --- |
| Pack filesystem: `_pack_fs.open_root`, `inventory`, `normalize_relpath`, `read_member_bytes` | Read root SDL, every imported module, and locks in one descriptor-anchored validation lifetime. Reject escapes, symlinks, hardlinks, special files, non-canonical paths, case/Unicode collisions, and unsupported platforms. Supply the exact captured bytes to RAES; do not validate a path then reopen it through `Path` or the author parser. Keep immutable staging and same-byte promotion as caller obligations. |
| Secret/configuration admission: `_authoring_safety.sensitive_member`, ADR 0035 | Reject sensitive import targets before opening them. Never consult pack-supplied or ambient `raes-trust.yaml`, environment variables, home configuration, credentials, or network/cache configuration. Reuse the existing sensitive-member rule; do not add a second denylist or blindly apply authoring inventory/cache exclusions to consumer validation. |
| Source and lock ingress: `_strict_json_member`, `_check_json_shape`, public RAES `Lockfile`/`LockRecord` and SDL parser | Bound lock bytes and structure, reject duplicate JSON keys/non-finite numbers/invalid UTF-8, then admit through the upstream closed models. SDL uses RAES's bounded duplicate-key/source-profile handling and existing explicit migration policy. No local SDL or lock schema. |
| Resolver policy: public RAES import/composition authority | Admit only local sources under the pack boundary, retaining upstream relative-path containment. Deny registry, network, and unsupported sources at every depth, before transport/cache access, including aliases that resolve to denied sources. Require an unambiguous applicable lock record and a digest pin for every admitted import. Verify both against the same captured module bytes and upstream module facts. Missing, empty, malformed, conflicting, or stale required pins/records fail closed. |
| Shared static checks: `_validate_pack_core`, `_validate_sdl_documents`, packaged provenance/compatibility/materialization schemas | Keep identity, safety/review attestations, visibility joins, ownership joins, content-set inventory, concept-binding admission, and experiment-family admission. Feed these checks the RAES-validated expanded object; do not return early after imports pass or flatten away alternatives. |
| Errors and observability: `Diagnostic`, `ValidationResult`, `_Errors`, `check.py`, existing digest/experiment errors | Translate documented input/filesystem/upstream failures to bounded deterministic codes and safe locations. Do not echo source locators, parameter values, lock bodies, absolute paths, exception prose, or RAES diagnostic messages. Use structured upstream failure codes rather than expanding the incumbent exception-message matching. Libraries remain silent, including upstream error paths; never suppress logging by changing process-global settings. Programming defects still raise. |
| Host/OS and authorization: existing consumer adapters, `AuthoringSession`, `_authoring_tools`, `mcp_server` | No Git, subprocess, shell, environment interpolation, cache/temp-tree writes, or pack-code execution. No new argv payloads, credential channels, grants, or auth service. Hosts retain actor/tenant/path authorization and immutable staging; static admission grants no execution or publication authority. |
| Persistence and release: `_transactions`, `digest.py`, `release`, `verify`, `component_boundary`, `release_provenance` | Consumer admission only reads the existing RAES lock. It never repairs/generates locks or materialization baselines. Author-side corrections retain proposal review, transactional replacement, exact associated-artifact coverage, component/SBOM projection, and release evidence. Reuse these paths rather than adding a cache, store, copier, or release workflow. |

Imported declarations still pass RAES's closed account, credential, and
environment-binding shapes, including literal/secret-reference distinctions.
Treat references as data; validation neither resolves secrets nor expands
environment syntax. Do not weaken these checks for kit-generated content.

The module pin is a digest of **raw module bytes**. It is not
`canonical_sdl_digest`, an export hash, an associated-artifact set digest, a
materialization baseline, or release authenticity evidence. Matching a
self-authored lock proves consistency, not trust or authorization.

## Whole-repository gotchas

Several direct SDL documents can share `sdl/raes.lock.json`.
`kits._stage_import_locks` currently writes each target's generated lock to its
sibling path; processing several targets in the same directory can overwrite
earlier coverage. Admission must verify each importing root against RAES's lock
scope, not accept the last generated lock by existence alone. Any producer
correction must use RAES-owned lock operations and the existing transaction.
Unrelated records in a shared lock cannot authorize a missing or ambiguous
edge; do not assume every record belongs to the first root. Transitive imports
need pins and applicable records too, or they remain rejected. Do not invent a
second transitive graph or flatten nested records locally.

`check.py`, `catalog` via `validation._validate_pack_snapshot`,
`experiments.load_pack_experiments`, `verify`'s static gate, and authoring
read/check tools consume the shared validator. Make consumer policy selection
explicit and consistent across the surfaces that offer it. Preserve safe
defaults in adapters that remain deny-only.
`digest._consumer_parent_candidates` independently denies imports for
`resolve_pack_artifact`; `digest._parse_parent_candidates` instead uses the
author parser for content-manifest operations. Neither is a safe shortcut for
the new check. Reuse the bounded consumer parsing seam where local-import
support is offered; document any remaining deny-only surface rather than
claiming all consumer APIs support composed packs.

Preserve authored-family, expanded-family, and selected-scenario distinctions.
`authored_sdl_parent` documents the upstream limitation on composed
`scenario-snapshot` parents. Do not change parent identity, stringify an
expanded object, discard imports from authored bytes, or weaken artifact
binding to make admission succeed. Preserve ADR 0033's selected-artifact
single-open contract when sharing parsing with artifact resolution.

Public behavior documentation and diagnostic presentation live in
`docs/public/validating.md`, `checking.md`, `mcp.md`, and `check.py`. Update them
with the implemented policy; retain default-denial explanations where they
still apply. This preflight belongs only in developer documentation under
ADR 0030. Accepted ADRs and historical preflights remain historical records.

## Evidence required of the eventual implementation

Use the existing synthetic-kit/materialization/CLI fixtures and public
validation tests, not a hand-assembled success object or a mock composer.
Evidence must include kit-add output passing the opted-in public check,
unchanged default denial, several roots sharing a lock, and direct/transitive
denied sources, missing/conflicting pins and records, changed module bytes,
unsafe filesystem members, malformed lock input, and resource exhaustion.
Use hostile trust/cache/secret fixtures and intercepted reads to prove denial
before access. Intercept environment reads, network, processes, writes, and
logging on both successful and failing imported documents; assert deterministic
bounded diagnostics and propagation of unexpected defects. Positive resolution
must still exercise RAES's real semantic checks and downstream joins.

Reuse the relevant tests in `test_validation`, `test_authoring_safety`,
`test_kit_materialization`, `test_kit_cli`, `test_check`, `test_catalog`,
`test_pack_experiments`, `test_digest`, and `test_dependency_pinning`, plus the
existing `fuzz/fuzz_validate_pack.py` boundary. The completion commands in
`AGENTS.md`/`.ground-control.yaml`, `Makefile`, mandatory CI `verify` jobs,
warning-strict Sphinx build, and `tools/check_docs_publication_boundary.py`
remain the repository gates. No new workflow is needed.

## Non-goals

No RAES semantics, local resolver/composer, duplicate DTO/schema/exception
hierarchy, generic plugin system, registry/network support, acquisition,
authentication, secret brokering, runtime realization, or pack execution.
No consumer lock repair, mutable-storage snapshot guarantee, new persistence,
publication, version/changelog edits, or downstream product assumptions.
This preflight changes guidance only; implementation and upstream API work
remain outside this change.
