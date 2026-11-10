# RAES interface preflight

Issue #552 needs complete operation contracts before callers depend on the Go
interface. This note supplements [design 0007](designs/0007-raes-interface.md).
It adds no component, dependency, or architecture exception.

## Current evidence and delivery boundary

After synchronization with `go-cutover`, `src/raes_env_packs/` and `tools/`
import 93 distinct RAES symbols.
The combined inventory has 101 symbols with the scoped contract tests.
The [operations inventory](raes-operations.md) must cover each symbol.
The issue's count of 72 describes an earlier commit; do not remove newer imports
to match that count.

`internal/raes` already declares interfaces. At the time of this
preflight, the checkout had no adapter and no RAES Go dependency in `go.mod`. Since then,
`go.mod` pins the RAES Go module, and `internal/raesadapter` implements
vocabulary access. `TestErrorMessage` checks error formatting, not upstream
compatibility. Existing documents describe upstream delivery at
their writing date; they do not prove current upstream availability.

Keep one inventory for the RAES Go plan. Distinguish a related upstream issue
from an issue that delivers the exact required operation. Mark an uncovered
operation explicitly. Record the upstream version and contract-test evidence
when delivery occurs. An unavailable operation blocks its dependent chunks;
a mock, skipped test, or local replacement cannot establish runtime parity.

The interface and inventory preparation can merge before those operations arrive.
The other adapter operations and their real tests belong to #643, before the
final cutover.

## Caller contracts

The production symbol map does not establish coverage of retained tests.
The interfaces must preserve the arguments and inspected results below:

| Incumbent | Required contract |
| --- | --- |
| `tests/test_raes_runtime_contracts.py` | Validate runtime inventory and materialization archive documents through RAES. Preserve the archive round-trip, nested inventory, and upstream default fields. Generic validation alone does not prove round-trip behavior. |
| `tests/test_techvault_pack.py` | Preserve `designation_records` and designation resolution. Expose compiled realization requirements and constraints through RAES's published forms. Node and network counts cannot support these checks. |
| `tests/test_techvault_pack.py` | Preserve `has_required_observation_support`: requirement, support declarations, and observation kind determine a Boolean. Admission of an observation document is a different operation. |
| `tests/test_kit_compute_substrate.py` | Preserve realization concern descriptors, observation capabilities, and vocabulary access where chunk 27 retains these checks. |
| `tests/test_techvault_study_pack.py` | Preserve runtime compilation, participant inject deliveries, and admitted time-model facts. The MCP compilation summary cannot replace this data. |
| `tests/test_concept_authority_alignment.py` | Preserve controlled-vocabulary catalog access where chunk 27 retains the check. Do not copy vocabulary values into local enums. |
| `_experiment_set.PackExperiment.compilation_request` | Preserve the admitted family handle, apparatus and participant manifests, realization envelope, execution authority, limits, and caller-supplied configuration validators. JSON alone cannot carry a validator or an adapter-owned handle. |

Name the retained tests in the inventory. Do not require every Python test
import indiscriminately: implementation-specific tests can disappear under
ADR 0047. Retained contract behavior cannot disappear because the interface
omits its inputs or outputs.

## Ownership and type rules

Keep the existing operation groups in one interface package. Callers take only
the group they need; command main packages supply the adapter. Do not introduce
a second facade, service layer, or general command dispatcher.

RAES owns schemas, enums, compiled addresses, canonical digests, defaults, and
semantic validation. `internal/schema` validates pack-owned schemas only.
`ContractValidator` delegates named, versioned RAES contracts to RAES. It must
not become a local schema registry or fetch schemas from document URLs.

Published JSON forms are transport values, not proof of admission. Document
each method's accepted form, normalization, result validity, and error behavior.
Keep number precision through decoding and upstream conversion. Neither
`internal/jsondoc` nor a local hash substitutes for a canonical RAES digest.

Keep parsed and compiled handles adapter-owned. Reject foreign handles without
a panic. Returned maps must not permit mutation of admitted state. An authored
fragment is not an expanded, semantically validated scenario. Preserve that
distinction when `AuthoredScenario` and `AdmitScenarioFamily` return handles.

Use explicit method parameters for caller context and resource limits. Preserve
participant configuration validators as caller-supplied behavior, not serialized
data or adapter globals. Retain separate pack and associated-artifact budgets,
including artifact counts, per-artifact bytes, and total bytes (ADR 0033).
Defaults come from RAES; a local zero must not silently disable a limit.

## Cross-cutting layers

| Layer and canonical incumbent | Required boundary behavior |
| --- | --- |
| Host authority: `AuthoringSession`, `_authoring_tools.TOOLS`, `docs/public/mcp.md` | Keep closed request schemas, host-selected roots and source handles, read-only defaults, and proposal review. Parsing or digest agreement grants no write, execution, or trust authority. The adapter adds no authentication service. |
| Pack reads: `internal/packfs`, design 0004 | Give RAES bounded bytes or a constrained filesystem over admitted members. `fs.FS` alone provides neither containment nor budgets. Do not reopen a host pathname inside RAES. Preserve immutable staging and same-byte validation. |
| SDL imports: ADR 0046, `validation._consumer_sdl_members`, `_read_consumer_sdl_sources`, `_parse_consumer_sdl` | Consumers supply only admitted SDL and lock bytes, excluding sensitive members. Enforce the aggregate composed-byte budget. RAES enforces local imports, digest pins, and agreeing locks at every depth. Preserve the structured phase-refusal fallback for import-free materialized roots. |
| Author resolver policy: `internal/packfs.AdmitMembers`, `kits._lock_bytes` | Reject `raes-trust.yaml` in every letter case before resolution. Keep RAES's empty registry trust policy. Preserve directory-wide locks; one document must not erase sibling records. Never route consumer parsing through an ambient author resolver. |
| Pack shapes and public parameter policy: `internal/document`, `internal/schema`, `internal/secretshape`, design 0005 | Keep strict, bounded decoding and full packaged-schema validation. Preserve secret-shape and environment-coordinate checks at their owning entry points. RAES parses its own SDL and contracts; do not pre-parse SDL with the pack metadata decoder. |
| Publication policy: `publication.py`, ADR 0028 | Preserve exact artifact identity and capability joins, backend profile admission, and the separate URL query allowlist. Generic secret scanning does not replace publication policy. |
| Errors and output: `internal/raes.Error`, `internal/diagnostic`, `internal/outcome`, `internal/jsondoc`, `internal/terminal`, design 0006 | Keep RAES code, pointer, range, stage, and severity at the interface. Product output uses the existing bounded catalog and envelopes. Never render upstream prose, raw errors, unrestricted paths, or authored values as diagnostic explanations. |
| Process and runtime: `architecture/model.yaml` | Preserve `silent-libraries`, `networkless-code`, `no-process-execution`, and `files-through-packfs`. The adapter reads no environment, credentials, clock, or user configuration. It starts no Python process and puts no document or secret in process arguments. |
| Persistence: `internal/packfs` transactions, ADRs 0033 and 0035 | The adapter adds no cache, registry state, or artifact store. Existing callers own staged publication and recovery. Parsing, validation, compilation, and stub planning must not provision resources or persist runtime state. |

Architecture rules inspect this repository's code. They do not prove that a
dependency avoids environment reads, filesystem access, network calls, or logs.
Adapter contract tests must exercise these boundaries against the real module.

## Diagnostics and failures

The RAES diagnostic is an upstream transport record. It is not a second product
diagnostic model or presentation catalog. Keep its required fields through
adaptation, then project them for the receiving surface. The MCP surface needs
ranges; static checks need safe member locations. Do not discard stage or
severity merely because today's product diagnostic has fewer fields.

Treat upstream sources and pointers as untrusted locations. Resolve a source
only against the supplied member set, as `validation._import_refusal_location`
does. Never trim an arbitrary absolute path into apparent safety. Bound
diagnostic counts and location lengths before output. Check code shape and range
coordinates before presentation; document index bases and range endpoints.

Use `errors.As` or `errors.Is` for documented upstream failures. Expected input
failures use the existing `raes.Error` transport. Unexpected defects remain tool
failures through `outcome.Run`; do not convert every error or panic into invalid
pack input. Define whether diagnostics accompany successful results and whether
any result remains usable beside a non-nil error. Message text never controls
fallbacks, severity, or acceptance.

## Extensibility and verification

The adapter is the seam for upstream API changes and delivery in stages.
Existing narrow interfaces let callers depend on available operation groups.
New contract versions, limits, supplied sources, and caller context belong in
explicit inputs. Do not make them ambient configuration or duplicate semantic
policy. Preserve handles when a published document cannot represent a result.

`architecture/model.yaml` already defines `raes-through-adapter`, including test
files and repository tools. An adapter design record must register its package,
dependency, and sole import exception before code changes. Use the actual
upstream module path, including any version suffix or additional module roots.
Do not exempt callers or all tests. Review dependency side effects as well as
direct imports. Keep `go.mod` and `go.sum` as the dependency authorities.

Use the existing `Makefile`, `.ground-control.yaml`, and CI gates; add no second
workflow. Follow the [Go test standard](go-test-standard.md) and conformance
corpus. Real adapter contract tests cover each delivered operation's successful
results, structured failures, bounds, and policy refusals. Include round-trip,
digest, handle ownership, and mutation-isolation checks where applicable.
Fuzz untrusted ingress; keep tests offline, deterministic, and race-safe.
Mocks can test callers but cannot prove the adapter's compatibility.

## Non-goals

This preflight implements no operation, adapter, symbol-map extension, or caller
migration. It changes no RAES contract, pack schema, content, version, release
workflow, or command envelope. It creates no upstream issue and sends no
cross-repository message.
The implementation run separately posted the
[consumer handoff](https://github.com/OpenRAE/rae/issues/1825#issuecomment-6573945905).
Public operation delivery and adapter contract tests remain in #643.
They do not block this preparation chunk.

Do not add Python bridges, copied schemas or enums, local semantic fallbacks,
per-caller adapters, duplicate validators, broad exception hierarchies, or
downstream catalog vocabulary. Missing upstream functionality remains a stated
dependency, not permission to implement RAES semantics here.
