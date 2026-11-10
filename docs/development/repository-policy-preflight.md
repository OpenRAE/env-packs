# Repository policy migration preflight

ASP-0006 and issue #577 move repository governance checks out of Python without
losing an invariant. This note fixes the boundaries for that work; it does not specify
implementation steps or deliver the invariant inventory.

The inspected baseline is `c5df5bd`, rather than the issue's historical
`975bd78`. Compare assertions against the implementation revision too. Tests
have changed since the issue review, including Go platform and workflow checks.

## Decisions and authority

[ADR 0047](../decisions/adrs/0047-port-the-tooling-to-go-with-one-cutover.md)
already authorizes this migration. It preserves governance, external contracts,
and the Python documentation toolchain. This work needs no new ADR or pack contract.

Use local Rego policies through Conftest for repository-specific decisions.
Use actionlint for GitHub workflow syntax, expressions, and supported security
checks. Its documented checks do not establish this repository's release,
permission, pinning, or merge rules. See the official
[actionlint checks](https://github.com/rhysd/actionlint/blob/main/docs/checks.md)
and [Conftest policy interface](https://www.conftest.dev/).

Keep contract-alignment tests in Go. Repository governance policy must not
become another pack validator or another definition of RAES semantics.
Keep the distinction between repository security policy and the RAES reusable-asset
trust policy. They have different authorities and inputs.

## Coverage contract

The implementation must supply an assertion-level inventory for all sixteen
modules in the issue. A module-level replacement label cannot prove coverage.
Each row needs the source test and assertion, invariant, replacement rule or
linter check, and passing and failing fixture. A retired row needs its reason
and the governing cutover decision. One test can contain several invariants.

Include helper behavior and regression cases, and not only assertions over
today's compliant files. Preserve boolean versus integer checks, required presence,
ordering, error propagation, negative claims, and nonempty discovery checks.
Consolidate duplicate assertions under one rule, with each source assertion
mapped to it. Do not preserve weaker duplicate implementations.

These are the concern groups the inventory must cover, not the final inventory:

| Source tests (`tests/test_*.py`) | Boundary that must survive |
| --- | --- |
| `workflow_permissions` | Every workflow: explicit read-only defaults, scoped job writes, immutable action refs, and no unattended PR merges. |
| `dependency_pinning` | Install shapes, complete and consistent locks, compatibility floors, vulnerability floors, and update ownership. Separate product retirement from retained docs tooling. |
| `codeql_workflow` | PR and weekly coverage, whole-repository scanning, language/toolchain setup, exact permissions, action order, and cancellation. |
| `scorecard_workflow` | Trusted publication triggers, approved actions, scopes, checkout credentials, SARIF publication/order, cancellation, and current badge identity. |
| `release_workflow_attestation` | Build subjects, scoped OIDC/attestation rights, and build-before-attest-before-upload ordering. |
| `release_workflow_tag_signing` | Release authorization, maintenance/publication exclusion, recovery, signer pins/floors, exact identity and target, verification order, immutable tags, and rerun safety. Preserve verified-tag recovery artifacts. |
| `readthedocs_config` | Docs interpreter/locks, version derivation, public source root, strict warnings, navigation, links, edit targets, and exclusion of maintainer records. |
| `makefile` | Safe default, promotion direction/title/body, no extra GitHub actions, override seams, failure propagation, and all-platform checks. |
| `ground_control_review_config` | Explicit typed review values, key placement, retained charter, and integration branch. Ground Control owns config shape. |
| `ci_topology` | Stable aggregate, exact mandatory membership, independence, behavioral failure propagation, coverage authority, secret eligibility, cache inputs, and complete audits/checks. |
| `pack_distribution_workflow` | Dispatch, ephemeral registry, scoped signing, tool order, and environment-bound input without shell expression interpolation. |
| `ownership_boundary_doc` | Distinct owners, portable content versus runtime machinery, first-party hosting, project rename continuity, and reference reachability. |
| `pr_title_guard` | Workflow wiring to the one title validator; preserve event-data handling and trusted base checkout. See the scope caveat below. |
| `raes_identity` | Current identities, immutable history exceptions, bound external project ids, command names, schema ids/versions, locator scheme, and upstream lock name. |
| `concept_authority_alignment` | Forbidden pack classifications, live upstream vocabulary, schema vocabulary traversal, authority references, template shape, and validator rejection. |
| `provenance_raes_alignment` | Upstream trust authority, field disposition, no local evidence vocabulary, valid example, and template references. |

At this baseline, `policy_command` lists ten modules. It omits CI topology,
distribution, ownership, and the three alignment modules. Its list cannot define
the migration's coverage.

The current `test_pr_title_guard.py` tests validator behavior and its CLI; it
does not contain workflow-shape assertions. The issue names its workflow checks.
Account for this distinction without dropping the validator tests or creating a
second title grammar. The repository-tools port and final cutover also affect
`tools/check_pr_title.py`, release detection, and the documentation boundary tool.
Their replacements must remain the workflow authorities.

## One gate and one owner per rule

Define the repository policy gate once in the Makefile. CI and
`workflow.policy_command` must call that same target with the same inputs,
policy tests, lint options, and failure behavior. Gate membership includes
checks absent from the old ten-module command. Avoid another command list in
workflow YAML, Ground Control, or a second runner.

Prefer Conftest's native parsers for YAML, TOML, and JSON over another configuration
collector. Its combined input retains paths for rules that compare files.
Use a collector only for facts that native parsers cannot supply, such as text or
controlled behavior. It must not grow a duplicate configuration schema.

Preserve ADR 0029: `verify` remains the aggregate context. Every mandatory job
must appear in both its dependency set and its result check. Policy failure,
tool failure, cancellation, skipping, and empty results must block the gate.
Derive membership from the job graph with the existing explicit Sonar exception.
Keep unrelated mandatory jobs independent and Sonar outside the aggregate.

Preserve one coverage producer per language during the port, then Go's producer
after cutover. Policy checks must not rerun the full product suite.

Workflow/config policy decisions belong in Rego. Where files or behavior need
extraction, keep Go code limited to reading facts or controlled probes. Feed
those facts to the policy; do not hide governance decisions in a parallel Go
test suite. Rego unit fixtures alone do not prove that collection or CLI wiring
works. Exercise the real ingestion and gate boundaries too.

Rego treats missing references as undefined. Builtin conversion errors can also
produce undefined results instead of stopping evaluation. A comparison inside a
denial rule therefore cannot establish required presence or valid input shape.
Use explicit presence and type checks, and reject failed conversions.

Each failing fixture must identify its expected rule, not merely any nonzero exit.
Missing tests or rules must fail even if the native tool reports success.
See OPA's [builtin error behavior](https://www.openpolicyagent.org/docs/policy-language/#errors).

Select policy paths, namespaces, parsers, and failure options explicitly in the
common gate. Ambient `CONFTEST_*` values or local tool settings must not change
which rules CI or Ground Control evaluates. A new policy namespace requires gate
coverage, not an assumption that Conftest discovers it automatically.

The Makefile and aggregate tests execute real behavior today. Preserve that
evidence through controlled probes using fake `gh`, Go, and mise executables,
and per-job result matrices. A token search for `exit 1` cannot replace these
probes. Run them without credentials or network access, in disposable fixtures,
with bounded execution and captured output. Never invoke live promotion,
signing, publication, or rehearsal operations to check policy.

## Cross-cutting layers

| Layer and canonical incumbent | Required treatment |
| --- | --- |
| Workflow syntax: actionlint | Check every `.yml` and `.yaml` workflow. Make optional ShellCheck/pyflakes integrations explicit and reproducible. Missing required tools must fail. |
| Workflow authorization: existing workflow files and ADRs 0017, 0018, 0020 | Policy reads configuration without requesting tokens. Preserve job-specific scopes, credential-free checkout where required, trusted release events, and exact signer identity. Never run PR policy code with publication credentials. |
| Data binding: `pr-title.yml`, `pack-distribution.yml`, CI Sonar step | Keep event/dispatch data in parsed files or `env` mappings, followed by quoted arguments. Keep `SONAR_TOKEN` out of scripts, process arguments, fixtures, and reports. Do not evaluate GitHub expressions as code. |
| Config shape: Ground Control, actionlint, and Read the Docs | Their schemas remain authoritative. Rego pins required repository values and placement. Do not build another full config schema or accept `true` as integer `1`, missing as `false`, or strings as booleans. |
| YAML ingestion: `internal/strictyaml`, `internal/document`, and native tool parsers | Use the format owner's parser. Test bare `on`, duplicate keys, null/missing/wrong-shaped fields, aliases, and multiple documents at the real ingestion boundary. Never silently skip malformed input. |
| Shell commands: existing pinning and Makefile tests | Preserve continuations, quoting, comments, and complete argument lists. Use a standard shell parser when extraction needs syntax. Unsupported or malformed commands cannot become compliant through omission. |
| Pack schemas: `schemas.go`, `internal/schema`, `internal/document` | Alignment tests read the shipped schemas and use the full existing validator for examples. Do not copy schemas or port the Python subset validator. Preserve stable diagnostics through the product validator. |
| RAES: `internal/raes`, design 0007, and `raes-operations.md` | Use published upstream operations through the adapter. Keep RAES diagnostics structured and value-free. No Python bridge, network vocabulary fetch, local ontology, or substitute trust model. |
| Filesystem: repository-tool root handling; `internal/packfs` for pack operations | Bound repository reads to the selected checkout and named inputs. Identity scans retain tracked-file discovery and narrow historical exceptions. Do not follow symlinks outside the root or read ambient secret files. Pack validation retains its descriptor boundary. |
| Errors and output: `internal/report`, `internal/outcome`, `internal/terminal` | A Go tool returns findings through the existing report shape and statuses. Escape authored labels. Keep libraries silent. Preserve nonzero external-tool exits and bounded errors without document values, environment dumps, or raw subprocess output. |
| Toolchain: `mise.toml`, `mise.lock`, `go.mod`, `go.sum` | Pin and verify new lint/policy tools through the existing setup. Select compatible Rego syntax explicitly. No floating installer, embedded OPA engine, remote policy bundle, automatic policy update, or hosted scanner. |
| Architecture: `architecture/model.yaml`, numbered designs, `tools/archcheck` | Register actual new Go ownership/dependencies before coding, and regenerate the C4 view when structure changes. Do not extend the architecture model into a second workflow-policy language. |
| Tests: Go test standard, `internal/testgate`, conformance corpus | Use `testing` and `go-cmp`, targeted fixture tests, Go mutation/regression gates, and existing command-contract cases. Rego needs positive and negative tests for each rule, including missing input and boundary values. |

`internal/document.DecodeYAML` deliberately rejects Python/Go-ambiguous pack
scalars. Bare workflow `on` is such a scalar. Do not route workflow YAML through
that pack decoder or weaken it to admit GitHub syntax. `strictyaml` serves
repository-owned typed records; it does not supply a replacement GitHub schema.

Keep workflow syntax in actionlint and repository decisions in Rego.
If extraction needs another parser, verify its treatment of the owner's format
with real inputs. Do not use shell token splitting or a partial version parser
as a substitute for shell syntax, requirement specifiers, or version ordering.
Reuse standard parsers; retain applicable Python checks until their replacements
preserve those behaviors.

`os.DirFS` does not confine symlink targets to its root. Use bounded repository
reads, such as the standard `os.Root`, rather than treating a working directory
as confinement. The existing `networkless-code` rule excludes repository tools;
an architecture pass alone therefore cannot prove that the collector stays offline.

`internal/testgate.Runner` demonstrates fixed-environment, argument-vector
execution. Its current scope is Git, Go, and mutation tools. Reuse the pattern
without coupling policy checks to mutation internals or making a general
workflow executor. This work needs no new controller, repository layer, logger,
database, or persistent policy cache. Intermediate facts belong in memory or
private temporary files with cleanup; never persist credentials or raw events.

Give probes an explicit child environment and controlled tool paths.
Do not inherit credentials, shell startup settings, or Make overrides from the host.

The numbered design must distinguish collected facts from diagnostics.
Collected input can contain maintained text and command arguments needed for local
evaluation. Findings contain rule identifiers and escaped relative locations,
without echoing input values. A JSON collection failure must not leave partial
input that the evaluator accepts. Pipelines must preserve every failed stage.
No policy uses network builtins, remote bundles, trace dumps, or automatic fixes.

These files form the whole-repository review surface:

| Concern | Canonical inputs and consumers |
| --- | --- |
| Invocation and review | `Makefile`, `.ground-control.yaml`, `.gc/plan-rules.md`, `AGENTS.md`, and `CONTRIBUTING.md`. |
| CI and supply chain | Every `.github/workflows/*.yml` and `*.yaml`, `.github/codeql/codeql-config.yml`, `.github/dependabot.yml`, `mise.toml`, and `mise.lock`. |
| Product transition | `pyproject.toml`, `requirements/*.in`, `requirements/*.txt`, `go.mod`, `go.sum`, `.coveragerc`, and `sonar-project.properties`. |
| Release integrity | `release-please-config.json`, `.release-please-manifest.json`, `tools/release_tag_gate.py`, `tools/sync_pack_versions.py`, and their approved port replacements. |
| Publication and identity | `.readthedocs.yaml`, `docs/public/conf.py`, public navigation, `docs/README.md`, `README.md`, `SECURITY.md`, and `tools/check_docs_publication_boundary.py`. |
| Pack and upstream contracts | Embedded resources through `schemas.go`, shipped schemas, contract prose, templates, examples, `internal/raes`, and `raes-operations.md`. |
| Structural and runtime boundaries | Architecture model, numbered designs, generated C4 view, checkout filesystem, temporary directories, process arguments, environment, and output streams. |

## Cutover and upstream dependencies

Keep applicable Python checks until replacement coverage exists. The final
cutover owns removal of Python product files and tests. Policies cannot retire
themselves merely because an expected file disappears or a glob becomes empty.
Missing required files, no discovered workflows, unselected namespaces, missing
rule tests, and failed tools must all fail visibly.

Translate Python product pins into Go module integrity and toolchain checks.
Reuse `go-audit` for checksum verification and reachable vulnerabilities,
`go-lint` for module tidiness, and `archcheck platforms` for platform discovery.
Do not mistake `go mod verify` for vulnerability analysis or dependency-update
ownership. Check the existing Make targets rather than restating their commands.

ADR 0047 retains `requirements/docs.in`, `requirements/docs.txt`, Sphinx,
Read the Docs, and pack-local Python. Retain docs hashes, applicable security
floors, interpreter agreement, and update ownership. Adapt Python product
metadata, audit population, coverage, and cache assertions only when their
subjects actually retire. Retain Python SAST coverage for shipped pack-local code.

Docs version derivation must follow the one release-please version file after
the cutover; do not choose another version authority here.

`docs/public/conf.py` currently reads both version and author from `pyproject.toml`.
Its replacement metadata source must work without installing the product for docs.
Keep the source checks, strict Sphinx build, and generated-site publication check.
Configuration policy alone cannot prove the built site's publication boundary.

Release subject formats and tooling change under other port chunks. Attestation,
SBOM, exact target binding, signing-before-publication, recovery, immutable tags,
and idempotency remain. Record how wheel/sdist and PyPI-specific checks map to
Go artifacts, GitHub Releases/Packages, and the final PyPI handoff. Do not loosen
rules globally or restore historical release exceptions to accommodate migration.

The alignment tests need two upstream facts: the lock filename and controlled
tactic terms. `Modules.LockfileName` declares the former.
The initial interface lacked vocabulary access and the Python import mapping.
Design 0012 adds `VocabularyReader.VocabularyTerms` and updates the
[operation map](raes-operations.md).
The adapter reads the public catalog at upstream revision `17bf4515bf12`.

Extend that consumer contract and map through the upstream API when available.
Test vocabulary discovery as nonempty for each required vocabulary.
An unavailable corpus cannot pass as an empty set.
Issue #577 delivers this vocabulary operation; issue #643 covers the other adapter operations.

Keep provenance vocabulary checks distinct from tactic checks. Provenance
checks property keys, enums, and constants. Tactic checks enums and constants,
since property names can legitimately share ordinary words with RAES concepts.
Authority references in prose are valid. Historical ADRs and immutable source
archives retain their narrow exceptions; do not rewrite them to satisfy a scan.
Bound Ground Control and Sonar identities are not product branding aliases.

## Extensibility and non-goals

The extension points are a new local rule and its paired fixtures, file
discovery by supported suffix, and existing config values. New mandatory CI jobs
must enter the existing aggregate's dependencies and result checks.
Derive the expected mandatory set from the graph instead of another job-name list.

Cross-file rules need path-aware input; Conftest documents
[combined inputs and policy data](https://www.conftest.dev/options/).
Keep required files, namespace selection, and parameters explicit. Separate
evaluation inputs from policy data; checked configuration cannot supply its
own exemption. Any extracted facts form one private tool interface, not a new
pack schema or general policy framework.

This work does not change SDL, pack schemas, ownership, signing trust, release
authorization, protected-branch settings, or human merge requirements. It adds
no service, uploads, pack execution, backend realization, or automatic fixes.
It does not implement the other Go port chunks or expand PR-title policy.
Static policy checks cannot prove a real signature, registry round-trip,
attestation verification, or hosted branch protection; retain their separate
release/integration evidence.

This preflight changes guidance only. Design 0012 and the model
declare intended package ownership before code exists. They must agree with these
guardrails, including parser scope and existing report dependencies.
Do not infer adapter availability from a model declaration or an assumed upstream
package name. Design-mode validation checks intended structure; the full architecture
gate requires the declared code and the matching generated C4 view.

The inspected numbered draft names `contract/concept`. At the time of this
preflight, the checkout had no adapter or RAES Go module dependency that verified
that API. `internal/raesadapter` now implements vocabulary access with it.
Its proposed YAML/TOML collection needs justification against native Conftest parsing.
Its model dependencies must permit the existing output helpers that the collector uses.
Reconcile these draft assumptions before implementation; do not weaken the architecture gate to admit missing packages.
