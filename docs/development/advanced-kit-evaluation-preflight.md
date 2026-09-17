# Advanced kit evaluation preflight

Issue #224 asks for an evidence-based decision about future reusable content,
after #190's infrastructure collection is available and authors have used it.
This note sets evaluation boundaries; it does not evaluate candidates, approve
families, or prescribe an implementation plan. Existing ADRs
[0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md),
[0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md),
and [0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
already establish the architecture. No new ADR is needed.

## Evidence and decision boundary

The checkout contains 38 infrastructure kit releases, the `raes-pack-kit` author
workflow, `tests/test_published_kits.py`, and the
[integration walkthrough](kits-integration-runbook.md). Commits `ff8149d` (#226)
and `079cb84` (#232) record the tooling and collection landing. These establish
a working basis in repository history, not proof of external release availability
or observed author demand. The walkthrough is reproducible static authoring
evidence; it proves neither independent adoption nor backend realization.

Establish the available collection revision and workflow, and distinguish
concrete author-task analysis from observed usage. Author feedback is not yet
available for this evaluation. Task analysis may support narrow worked examples
over existing contracts; new reusable families still require the working basis
and validation evidence stated in their admission decision. Do not turn
hypothetical reuse, directory counts, or passing tests into adoption claims.
Author reports
must be sanitized under the [scrub policy](scrub-policy.md); keep credentials,
private deployment details, participant data, and raw runtime traces out of
decision records and follow-up issues.

The eventual matrix must cover all ten issue-listed families and preserve
separate judgments for author value, portability, semantic cohesion, and
maintenance cost, with supporting observations and uncertainty. A rank is not
semantic authority or approval. Keep rejection/deferment rationale and the
evidence needed to reconsider a decision. No mandatory numerical score or new
machine-readable evaluation schema is warranted.

Use the issue's six disposition labels exactly: `kit`, `module-only`, `profile`,
`complete-pack`, `documentation`, or `do-not-standardize`. Deferral describes
decision status, not another carrier. Each positive disposition must identify
the existing authority and concrete working basis:

- A `kit` adds useful pack assets and authoring support to a RAES module. A
  module already supplying the whole reusable boundary needs no extra carrier.
- `profile` must name the precise owning contract. This repository's
  publication profile describes release supply and views; a RAES backend
  profile describes capabilities. Audience selection instead uses the existing
  `profiles/bundles.yaml` delivery-bundle contract in `contract/pack-layout.md`.
  None is a generic behavior or deployment overlay. An absent profile contract
  is a dependency, not permission to invent one here.
- A `complete-pack` may keep purpose inseparable from scenario content. That
  does not make its behavior universal infrastructure. Documentation can explain
  a composition pattern without creating a reusable artifact.

Approved families receive separate, narrowly scoped issues with an executable
working basis, acceptance criteria, authority dependencies, and limitations.
Use `.github/ISSUE_TEMPLATE/feature_request.md`; `issue_skeleton.py` scaffolds a
particular pack and is not a family-evaluation workflow. Admission guidance
changes belong in `docs/public/kit-content-strategy.md` and must trace to
observed use. Internal evidence and decision history belong in developer docs.
This preflight creates neither those decisions nor their implementation issues.

## Contracts that must not be conflated

`environment-pack-kit/v1` is infrastructure-specific. Its schema has eight
closed concerns, positive infrastructure resource estimates, required component
inventory, and a closed test-kind vocabulary. In `kits.py`, both
`_validate_raw_module` and `_verify_infrastructure_only` reject behavior and
narrative sections, including agents, action contracts, behavior specifications,
conditions, objectives, injects, events, scripts, stories, and workflows.
`tests/test_kits.py` explicitly tests rejection of RAES-valid behavior.
`tests/test_published_kits.py` also assumes domain parameters, benign seed
inventory, meaningful parameter variation, and the 38-release collection.

Do not relax these gates, extend a concern enum, invent placeholder resources,
or hide behavior in seed assets to make a candidate fit. Approval of a future
family is not admission under today's schema. Any necessary carrier change
requires a separate compatibility decision covering the loader, catalog,
materialization, adapters, and release tests. ADR 0036 supersedes ADR 0035's old
content-location statements; it does not broaden kit semantics.

Existing workflow-orchestrator, evaluation-worker, policy-engine, telemetry,
observability, and security-tool kits describe infrastructure. Their names do
not authorize portable workflow engines, scoring, oracle models, or runtime
evidence semantics. Likewise, a licensed OT asset is not evidence of physical
safety or hardware portability, and an assessment overlay must not expose
restricted solutions through participant assets or add pack-owned scoring.
Use RAES-owned meanings; unsupported semantics require an upstream dependency.
Domain names in the evaluation are descriptions, never new canonical enums.
Where classifications are needed, reuse RAES concept bindings and pinned scheme
snapshots under [ADR 0038](../decisions/adrs/0038-ship-raes-concept-bindings-beside-pack-sdl.md),
not a pack-local ontology.

## Cross-cutting layers to preserve

The evaluation itself adds prose and issue records. It needs no new parser,
configuration, persistence service, auth surface, exception hierarchy, or logs.
When inspecting a working basis or describing a later implementation, the
following existing layers still constrain what may be claimed. Source paths
below are relative to `src/raes_env_packs/`.

| Layer and canonical incumbent | Guardrail |
| --- | --- |
| Semantic authority: exact RAES pin in `pyproject.toml` (5.0.0 at preflight); public RAES parsers, module descriptors, structured edits and resolver used by `kits.py` | Parameters, exports, namespaces, imports, composition and `sdl/raes.lock.json` remain RAES-owned. No copied SDL schema, private API, parallel composer, or locally invented behavior vocabulary. |
| Discovery: `KitSource`, `build_kit_catalog`, `search_catalog`, `inspect_kit` | Inspect admitted releases at immutable revisions through the existing deterministic projection. The evaluation matrix is a decision record, not another catalog or authored module descriptor. Repository kit availability does not imply inclusion in the installed wheel. |
| Input/config shape: `resources/schemas/kit*.schema.yaml`, `validate_kit_document`, `load_kit_release`, shared `validation._StrictLoader`, `_check_yaml_events`, strict JSON readers, `KitLimits` and `PackValidationLimits` | Reuse closed shapes, duplicate-key rejection, type/size/depth limits and relational checks. The shared schema evaluator supports a subset; a schema declaration alone does not establish enforcement. Do not add a candidate config or environment-binding dialect. |
| Secrets and OS exposure: `_authoring_safety.admit_members`, kit secret-key/value and parameter admission, `kit_cli._parameters` | Reject operator/secret files and `raes-trust.yaml` before reads. Parameters are bounded non-secret scalars; credentials, secret-store coordinates and environment bindings are not variation seams. Use the CLI's `--parameters -` stdin input, not JSON in argv. Secret-pattern checks do not replace review of prose or arbitrary assets. |
| Auth and host scope: `authoring.AuthoringSession`, `_authoring_tools.TOOLS`, `mcp_server.create_server` | If the existing adapter is used, retain host-granted operations, admitted immutable sources, controlled roots and exact proposal review. Host identity/authorization is not inferred from a pack, catalog revision or proposal handle. Local CLI access is not a multi-tenant authorization service. No new grants or transport are needed. |
| Filesystem and persistence: `_pack_fs`; `_transactions`; `KitProposal`, `propose_*`, `apply_proposal` | Confine bounded regular-file reads; reject links, special files, escapes and collisions. Reuse full-successor validation and atomic exchange, explicit ownership and author-modification conflicts, fixed safe modes and preserved recovery trees. Trusted parents and serialized/immutable inputs remain required; unsupported OS guarantees fail closed. The materialization ledger is ownership/provenance, not a second dependency lock or database. |
| Execution and validation: `validation.validate_pack`, `_validate_pack_for_author_ci`, `content_ci` | Consumer parsing denies imports; staged kit composition uses RAES with an empty registry policy. Trusted author CI may execute pack validators/tests. Do not run imported candidate code to collect inspection evidence or mistake static composition for runtime qualification. Kit assets remain confined to `assets/briefing/`, `assets/content/`, `assets/kits/`, and `docs/kits/`; they cannot install tests, validators, hooks or workflows. |
| Identity, visibility and release: RAES associated-artifact models; `digest`, `validation`, `publication`, `component_boundary`, `sbom`, `release`, `verify` | Keep exact bytes/semantic parent, visibility joins, licensing, source identity and component scope together. Inventory and provenance are not authenticity, safety or runtime evidence. Mutable/external dependencies stay explicit; no fabricated dependency closure or unproven capability claim. Publication cannot change RAES author intent. |
| Errors and observability: `Diagnostic`, `ValidationResult`, `KitError`/`KitRecoveryError`, `check` presentation, `authoring._safe_diagnostics` | Preserve bounded value-free diagnostics and CLI outcomes 0/1/2/3. Library operations stay silent; hosts own redacted audit events. Do not expose raw parser exceptions, parameter values, secret paths or upstream responses in errors, logs, evidence excerpts or issues. No family-specific error or logging framework. |

## Extensibility, repository gates, and non-goals

The useful variation seam is the RAES module's declared parameters and exports,
with relationships composed at the consuming pack root. Record what actually
varies between observed tasks; do not replace the whole scenario with an opaque
parameter or couple kits through hidden runtime dependencies. Supporting assets,
tests, evidence limitations, licensing and maintenance ownership travel with the
proposed reusable unit. A future carrier change uses the existing independently
versioned kit manifest/catalog/ledger and RAES adapter boundaries; no plugin
system or arbitrary template engine is justified.

Reuse `tests/test_kits.py`, `test_published_kits.py`, `test_kit_materialization.py`,
`test_authoring_safety.py`, `test_kit_cli.py`, and the integration walkthrough
for the authoring claims they actually test. Keep pack/schema/concept-authority,
visibility, publication and release contract tests as their existing authorities.
Do not weaken infrastructure tests or add tests that merely assert evaluation
prose. `content_ci.check_anti_extension` remains the repository/schema boundary
gate, not a new semantic validator.

`AGENTS.md`, `.ground-control.yaml` and `.github/workflows/ci.yml` define the
verification surface. Public guidance must also pass warning-strict Sphinx and
`tools/check_docs_publication_boundary.py`; developer records stay outside the
published site. Preserve pinned dependencies/actions and existing workflow
permissions. Use Conventional Commit metadata and the existing review/merge
workflow; leave package versions and `CHANGELOG.md` to release-please.

Neither #224 nor this preflight implements candidate content, broadens #190,
changes schemas or runtime behavior, introduces domain vocabulary into canonical
contracts, qualifies a backend, deploys services, or creates a general plugin
system. A decision to standardize is work for a separate implementation issue.
