# Pack-aware MCP authoring preflight

Issue #192 adds an adapter over the existing pack library: discovery,
inspection, examples, scaffolding, layering/composition, static validation,
diagnostic explanation, compatibility cards, and publication planning. It does
not create a second pack implementation. This note records integration
guardrails and gaps in the current incumbents, not an implementation plan.

The governing decisions already exist: ADRs
[0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md),
[0013](../decisions/adrs/0013-separate-consumer-static-validation-from-author-ci.md),
[0028](../decisions/adrs/0028-project-raes-artifact-satisfaction-into-publication.md),
[0031](../decisions/adrs/0031-compose-beginner-safe-pack-checks-from-existing-authorities.md),
[0032](../decisions/adrs/0032-derive-catalog-projection-from-existing-authorities.md),
[0033](../decisions/adrs/0033-resolve-pack-artifacts-through-one-bounded-open.md),
[0034](../decisions/adrs/0034-compose-progressive-scaffolding-from-pack-and-raes-authorities.md),
[0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md),
[0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md), and
[0037](../decisions/adrs/0037-compose-verified-pack-distribution-from-existing-authorities.md).
No new ADR or semantic authority is needed.

## Canonical incumbents

Paths in this table are relative to `src/raes_env_packs/`.

| Concern | Reuse and boundary |
| --- | --- |
| Pack contracts | `resources/contract/pack-layout.md`, packaged schemas and templates; `validation.py` owns static pack checks and relational joins. Protocol DTOs carry requests/results, not copies of these schemas. |
| Validation and explanation | `validate_pack`, `PackValidationLimits`, `Diagnostic`, `ValidationResult`; `check.build_report`, `presentation_for`, and existing renderers supply explanations, owners, domains, ordering and verdicts. Extend shared presentation metadata when needed. |
| Search, inspection and cards | `catalog.Source`, `build_catalog`, `build_entry`, `validate_document` and the existing catalog schema. Consume the static pass's internal snapshot; do not reopen YAML after validation or export that snapshot as a new public pack model. Search filters the generated records; a compatibility card is a projection of the same facts. |
| Examples and scaffolding | Packaged resources and first-party `packs/` and `kits/`; `wizard.normalize_inputs`, `ROUTES`, `CAPABILITIES`, `build_proposal`, `machine_document`, `write_proposal`. Examples remain inert content; repository content and installed-wheel resources have different availability. |
| Kit discovery and composition | `KitSource`, `KitLimits`, `load_kit_release`, `build_kit_catalog`, `search_catalog`, `inspect_kit`, `propose_add/update/replace/remove`, `KitProposal`, `proposal_document`, `apply_proposal`. Preserve explicit target SDL, namespace, parameters, dependency and ownership checks. |
| Identity and artifact access | `digest.validate_pack_content_manifest`, `resolve_pack_artifact`, RAES associated-artifact models and validation limits. Static validity, byte identity and authenticity are separate claims. Artifact access also needs caller visibility authorization. |
| Publication planning | `distribution.Selector`, `OperationPlan`, effect categories and `plan_publish`; `publication.validate_publication_document`, requirement-address helpers and trusted RAES backend-profile loading. `component_boundary`, `sbom`, `release_provenance` and `verify` retain their own evidence gates. |
| Persistence and writes | `_pack_fs` descriptor-based reads and `_transactions.write_member/publish_noreplace/exchange`, as composed by wizard and kit writers. `kit.materializations.json` records ownership; `sdl/raes.lock.json` remains RAES's dependency lock. No MCP database, portable approval ledger or alternate writer. |

The repository has no pack MCP server, Hub controller, tenancy repository,
authentication service or audit framework to reuse. `.mcp.json` configures the
development Ground Control client; it is not the product server's configuration
contract. Keep the pack surface separately registered from `raes-mcp`; no pack
tools or workflows are added to the RAES MCP server.

## Integration gaps that must not be hidden by an adapter

- **Consumer and author validation differ deliberately.** `validate_pack` uses
  bounded bytes with `raes.parse_sdl` and denies imports. The internal
  `_validate_pack_for_author_ci` enables `parse_sdl_file`; `content_ci.main`
  additionally runs pack-local code. Neither is an untrusted consumer shortcut.
  A composed pack can legitimately contain imports while the default consumer
  result reports `sdl.imports-denied`. Preserve that result and expose any
  separately supported composition assessment with its explicit policy/context;
  do not silently change the meaning of “valid.”
- **Kit inspection and preview need a proven consumer policy.**
  `kits._load_release_scenario`, `_pack_parent` and `_lock_bytes` use file-backed
  RAES parsing/resolution. `propose_*` stages temporary trees beside the pack,
  despite ADR 0035's write-free preview contract. Immutable local input alone
  does not deny remote/transitive imports, ambient trust configuration, external
  file reads or resolver cache writes. Extend the shared boundary through a
  public RAES policy/API that enforces those restrictions; copying the resolver,
  monkeypatching it or treating temporary writes as read-only is not acceptable.
  Any separately effectful preparation needs its own disclosed targets/effects
  and authorization before it runs. This gap must be resolved for the promised
  composition surface, not hidden by dropping composition from the issue.
- **Current previews are not sufficient write approvals.** Wizard machine
  output lists filenames; kit output lists operations and parameter names.
  Neither exposes the complete resolved pack target and proposed content diff.
  Extend shared proposal presentation so every front end can review exact
  additions, replacements and deletions, assumptions, unresolved inputs, lock
  and ownership changes before mutation. Binary/large changes need bounded
  identity/size summaries and an authorized review mechanism; omitted or
  truncated changes cannot silently become approved.
- **Publication planning is not publication verification.** `plan_publish`
  accepts an already-built release tree and classifies effects. It does not run
  every publication gate; `OperationPlan.applicable` may be true when
  `verification` is absent. `verify.load_release_evidence` currently uses
  pathname reads and ordinary YAML/JSON loading, without the consumer's full
  no-follow and parsing budgets. Its input cannot simply become an arbitrary
  untrusted path. Reuse/harden shared evidence loading and validation, report
  absent evidence and unavailable authorities accurately, and retain existing
  verification states. Do not call release build/check commands to fill missing
  planning data; they belong to the trusted author workflow and may write or
  resolve imports.
- **Existing exception text is not a safe transport envelope.** Some
  `WizardError` messages echo request values, catalog failures retain authored
  labels, and distribution diagnostics/effects can include supplied roots or
  repository strings. `Selector` is a dataclass carrier, not a validating
  constructor; it cannot admit repository URLs or digest domains by itself.
  Reusing a type does not make every field safe. Fix shared admission/presentation
  where needed and serialize only bounded, approved fields. Preserve existing
  `KitError`/`KitRecoveryError`, `PackDigestError`,
  `DistributionError` and transaction failures; do not add parallel exception
  families for each MCP tool.

The checked-in exact pin is `raes==3.5.0`. Its installed public surface includes
`raes.language_service` diagnostics, formatting, completion and structured
edits, and `raes semantic compile --output json`. ADRs 0031/0034 describe the
older 2.0.0 pin's limitations, not the current capability inventory. Delegate
each SDL operation to the pinned public authority with explicit migration,
resource and effect policy. A compile summary is not an execution plan;
execution-plan construction requires a verified public upstream contract and
must not invoke a backend. An unavailable safe upstream operation remains an
explicit capability gap, never a local semantic approximation.

## Cross-cutting layers every exposed operation must pass

| Layer | Required behavior |
| --- | --- |
| Transport and authorization | Prefer local stdio for the initial surface. Host launch authority supplies allowed roots and operation permissions; a request cannot widen them. Authenticate/authorize actor, source, target and visibility at any hosted boundary, including apply and proposal lookup. Client roots, tool annotations and a caller-provided `approved: true` are not independent authorization. A network listener requires the supported transport's authentication, origin/host and session protections before exposure; do not invent a pack auth model. |
| Request/config shapes | Closed, versioned, bounded operation DTOs reuse wizard normalization, kit schema/parameter admission and selector rules. Reject unknown fields, malformed versions, invalid types, excessive nesting/counts/text and unsafe selectors before dispatch. Bound aggregate search/response work as well as individual packs. Limits and allowed sources come from operator policy. No pack-supplied command, executable/import path, host output path, environment binding or credential-provider configuration. |
| Secret handling | Reuse kit secret-key/value and environment-coordinate checks, materialization validation and publication locator policy. Do not expand `${...}`/`env:...` or consult secret stores/ambient environment. Operator credentials, real secret values, private keys, signed URLs and secret coordinates cannot enter authoring inputs, plans, diffs, portable files, logs or errors. Pattern checks are defense in depth, not proof that arbitrary content is non-secret: expose authorized, purpose-selected data, not a recursive file-dump tool. Runtime SDL environment and synthetic-fixture semantics still belong to RAES; this surface does not relax kit parameter restrictions. |
| Filesystem and staging | Host scope admission precedes `_pack_fs.open_root/inventory/open_member/read_member_bytes`. These helpers confine members under an opened root; they do not authorize that root or protect arbitrary mutable ancestor directories. Use immutable admitted inputs and trusted parents, reject links/special files/collisions/escapes, and enforce count, per-file and aggregate limits. `resolve()` followed by an ordinary read/write is not equivalent. Unsupported descriptor guarantees fail closed. |
| Parsing and validation | Reuse `_StrictLoader`, `_check_yaml_events`, strict JSON admission, `_trusted_schema`, `_schema_violations`, `PackValidationLimits`, `KitLimits` and RAES limits. Carry applicable identity, provenance, compatibility/visibility, materialization, publication-supply and artifact-binding joins through shared validators, not only protocol shape checks. The local schema helper implements a subset; new schema keywords require matching shared support and contract tests. |
| RAES and process boundary | Default inspection/validation does not execute pack validators/tests/hooks, resolve imports, contact declared services, probe the host or start a backend. Prefer in-process public APIs. If a public CLI is necessary, use a code-owned executable and fixed argv, bounded stdin/stdout/stderr, a deadline and cancellation that terminates its process group, and a minimal environment. No document/token in argv, shell interpolation, pack-selected executable or ambient credential inheritance. `content_ci._run_pack_process` illustrates bounded author execution but inherits environment and is not a consumer sandbox. |
| Results and observability | Preserve ordered canonical diagnostics and `check` explanations, separate expected input/conflict/policy failures from unexpected tool failure, and preserve the meanings of CLI outcomes 0/1/2/3 in the transport. Do not parse exception prose or echo raw upstream bodies, URLs, paths or subprocess output. Libraries stay silent; stdio stdout belongs to protocol framing. Host audit records identify operation, authorized target, proposal, effects and outcome with redaction, without document bodies. Authored prose remains untrusted data, never agent instructions; terminal/browser rendering needs contextual escaping. |
| Mutation and recovery | A distinct apply operation consumes the exact reviewed proposal. Bind it to actor/session scope, target, source revision, base/successor bytes and effects; reauthorize and recheck at apply. Do not accept caller-reconstructed internal proposal objects or recompute changed bytes under old approval. Frozen dataclasses contain mutable dictionaries, so preserve/recheck exact bytes. Use existing absent-target create or staged exchange with full revalidation, serialization of writers and stale/conflict checks. Handle repeat apply, cancellation and uncertain completion explicitly; preserve recovery trees on rollback failure. Linux `renameat2` and same-filesystem constraints remain real platform requirements. |

Compatibility uses the existing manifest and publication/RAES facts without
probing. Pack `runtime_profiles[].profile_id` and RAES backend-profile ids are
different namespaces; equal spelling is not a join. Unknown, unsupported,
unverified, stale, invalid and unavailable retain their existing distinctions.
Provenance clearance, a content digest, a planned publication, kit inventory or
golden status does not establish authenticity, runtime readiness or capability.
Media and example contents respect existing visibility and redistribution gates;
pack code and instructions are inspected as data.

## Extension seams and repository-wide checks

Keep source identity/revision, source kind, authorized pack root, `as_of`,
freshness policy, target SDL and resource/effect policy explicit. Hosted packs
use `packs/` and kits use `kits/`; the CLI's historical `environments/` default
must not hide first-party content or become an MCP hard-coded root. Package
resources must work from an installed wheel, without requiring a repository
checkout or current-working-directory discovery.

Acquisition remains separate from discovery/planning. If an archive is admitted,
reuse `distribution.stage_pack_archive` and `ArchiveLimits` with the ADR 0037
ingest checks; no automatic download, unrestricted extraction or new transport
implementation belongs in an inspection handler.

Wizard capabilities are pack-owned optional layers; kits are released RAES
modules plus supporting files. Layering an existing pack is not permission to
overlay the create-only wizard output. Any extension uses explicit ownership,
conflict handling and the shared transaction, rather than arbitrary patches or
a new composition engine. New sources/transports extend the outer admission
seam; new SDL capabilities extend the exact-pin public RAES adapter. Versioned
MCP envelopes remain distinct from pack, catalog, kit, publication and RAES
contract versions. Wire-shape changes must preserve or explicitly version the
existing CLI/Hub contract too. Packaged schemas retain the draft-2020-12,
`raes.dev` `$id` and string `schema_version` conventions enforced by
`test_schema_conventions`; tool request schemas do not become pack schemas.

The host owns session persistence and redacted audit storage. Reuse its lifecycle
for pending proposals; they are not portable pack metadata, RAES locks or a new
database requirement. Disconnects must not leave an unreported commit or delete
the only recovery copy.

`pyproject.toml`, `requirements/runtime.txt`, co-installed tool locks and
`uv.lock` must agree if dependencies change. MCP currently arrives transitively
through RAES (`mcp==2.0.0` in the runtime lock); directly importing its SDK needs
an explicit supported dependency declaration. Reuse the SDK's protocol
machinery, not a bespoke JSON-RPC implementation. Keep the canonical CI topology,
hash-locked installs, action pinning, workflow permissions and release paths.
`.ground-control.yaml`, `AGENTS.md`, `.gc/plan-rules.md`, `.github/workflows/ci.yml`,
`.github/workflows/pack-distribution.yml`, `Makefile` and release-please remain
the workflow authorities. No manual version/changelog edit or publication path.
Developer guidance stays outside the `docs/public/` publication boundary.

Acceptance tests should reuse the synthetic temporary-pack fixtures and real
pinned RAES calls in `test_validation`, `test_check`, `test_catalog`,
`test_wizard`, `test_kits`, `test_kit_materialization`, `test_pack_artifact_resolver`,
`test_publication`, `test_verify` and `test_distribution`. Add protocol-level
parity and adversarial coverage: no network/process/secret/cache access through
read tools; all direct SDL variants and hostile imports; strict input/resource
limits; source/root/visibility authorization; malicious text and error leakage;
preview completeness; forged/stale/cross-session proposals; concurrent/repeated
apply, cancellation and recovery. Mock forbidden effects while exercising real
validation, not just tool registration or mocked successful delegates.

All six `AGENTS.md` verification commands remain required, together with
applicable schema, dependency, package-resource, docs-boundary and workflow
contract tests. The transport must expose the issue's complete authoring scope;
a set of tool names returning placeholders does not satisfy the contract.

## Non-goals and anti-patterns

No backend lifecycle, scenario execution, service probing, live pricing,
credential acquisition, signing or publication mutation belongs in these
authoring tools. Those effects stay in separate explicit operations owned by
the appropriate system. Execution-plan construction through RAES is within
scope; executing that plan is not.

Do not add pack workflows to RAES MCP; a local SDL/compiler/resolver/lock/trust
model; an authored card schema; a second validator or diagnostic taxonomy;
generic command/template/plugin hooks; implicit fixes/publication; automatic
provenance approval; or downstream catalog terminology in canonical contracts.
This is RAES-subordinate pack tooling, including the first-party content
placement established by ADR 0036, with zero extensions to RAES semantics.
