# TechVault Cortex enrichment preflight

Issue #286 is not a Cortex liveness defect. TechVault currently declares an
exact Cortex image, its Elasticsearch configuration and initial index schema,
the Cortex listener, a jobs volume, and TheHive command-line endpoint
coordinates. It does not declare an analyzer catalog or runner, per-organization
analyzer enablement, a least-privilege TheHive identity, a shared API-key
binding, or enrichment readiness. A healthy `/api/status` and authenticated
`/api/user/current` therefore do not establish an enrichment service.

The issue permits two honest outcomes: a complete, clean-start enrichment
contract or an explicit status-only Cortex. A partial connector that remains
`ERROR`, a non-empty analyzer list whose workers cannot run, or undocumented
post-realization bootstrap satisfies neither. This note fixes the architecture
boundary and the decision gate; it is not an implementation plan.

## Current contract and gaps

| Concern | Current authority | Missing contract |
| --- | --- | --- |
| Cortex artifact and listener | Exact `thehiveproject/cortex` source, `cortex-api`, loopback host publication | The selected digest's analyzer/runtime contents and native readiness are not declared or proven. |
| Cortex configuration | `content.cortex-app-config` selects Elasticsearch and local/key auth | No `analyzer.urls`, local analyzer path, runner, execution limits, or offline policy. |
| Cortex stored state | `content.cortex-job-index-schema` uses RAES `service_materialization` with readback evidence | No organization, users, analyzer enablement/configuration, or API-key state. `/api/analyzer` lists enabled analyzers for the caller's organization, not installed definitions. |
| Analyzer bytes | None | No exact definitions, executable code, dependencies, licensing/provenance, or immutable acquisition route. |
| TheHive connector | Endpoint flags name `http://cortex:9001`; TheHive depends on Cortex | No API key is supplied. Dependency order is not readiness or authentication. |
| Credentials | A comment claims an eventual generated `cortex-apikey`, but no such generated artifact or binding exists | Bootstrap authority, runtime identity, key lifecycle, producer, consumers, and redacted evidence are absent. |
| Persistence | `cortex_data` retains `/opt/cortex/jobs`; Elasticsearch has its own retained volume | No idempotent reconciliation or restart readback proves organization, key, enabled analyzers, and connector state survive. |
| Observability | Listener/status observations only | No expected analyzer-set readback, connector-OK assertion, or successful offline enrichment probe. |

The existing `infrastructure.thehive-case-management-service` kit does not fill
these gaps. It exports static TheHive surfaces and benign seed inventory and
explicitly does not claim launch, credential delivery, readiness, or runtime
evidence. TechVault does not compose that kit, so changing it would broaden the
issue without fixing TechVault's current contract.

## Authority and selected boundary

Keep these facts separate:

| Class | Owner and carrier | Guardrail |
| --- | --- | --- |
| Portable desired service state | TechVault through existing RAES SDL carriers | Declare the offline analyzer baseline, per-organization enablement, integration identity, and readiness intent only where the pinned RAES contract already has meaning for them. |
| Analyzer distribution | Exact source/artifact identity plus environment-pack associated-artifact binding when bytes ship in the pack | Pin definitions, code, and dependency closure together. A moving catalog URL or runtime clone is not authored offline capability. |
| Native materialization | LilRAE's admitted backend adapter implementing a governed RAES service interface profile | Reconcile through Cortex/TheHive APIs or native configuration, then read back. Do not encode API calls, shell scripts, host paths, or Compose fragments as portable semantics. |
| Bootstrap authority | Backend credential/secret boundary | Use only while reconciling organization, identities, and analyzer state. It is not the TheHive connector identity. |
| TheHive runtime identity | Dedicated Cortex account with `read` and `analyze` only | `orgAdmin` may enable analyzers but must not be retained in the connector. Official Cortex guidance calls for a dedicated TheHive account and API key. |
| API-key value and lifecycle | An existing RAES secret-output/reference contract if one can express the producer-to-consumer join; otherwise backend-local for status-only mode | Never infer shared identity from matching environment-variable names or an opaque `provenance` string. Never put the key in portable evidence. |
| Observed satisfaction | RAES assertions/evidence plus backend realization observations | Record expected analyzer ids, safe status classes, and result digests/counts without raw keys, complete API responses, analyzer input, or report bodies. |

The preferred product outcome is working enrichment, but it is gated by the
portable contract. The current repository contains no Cortex organization,
analyzer-enable, or shared API-key profile, and its existing Shuffle preflight
records that pinned RAES 3.3 has no typed shared-operator-secret equality join.
Implementation may select operational mode only after confirming that an
already-governed RAES initial-service-state and secret-reference contract covers
all of those joins and that LilRAE realizes it from a clean admitted plan. If
that contract does not exist, the self-contained repository outcome is
status-only: remove the claimed TheHive connector configuration, stop describing
Cortex as an analyzer backend, and document that no enrichment is available.
Do not invent a TechVault-only `service_materialization` profile or magic
generated-artifact provenance string to force operational mode.

## Canonical contracts to reuse

- RAES `Content` placement and `service_materialization`, as already used by
  `cortex-job-index-schema`, are the initial-state seam. Reuse their target
  service reference, conflict policy, readback assertions, evidence
  requirements, and observation boundary. An interface profile must be an
  existing governed profile; this repository does not define profile semantics.
- `RuntimeEnvironmentVariable`, `GeneratedArtifact`, node services,
  `RuntimeNetworkRealization`, infrastructure dependencies, and
  `PersistentVolume` remain separate authorities for effective environment,
  generated output projection, transport, topology, and storage. A topology
  dependency never substitutes for an authenticated readiness gate.
- `validate_pack()` and author CI must continue to parse the SDL only through
  pinned `raes==3.3.0`. Do not add a Cortex schema or reusable semantic validator
  under `raes_env_packs`.
- Exact shipped bytes use the existing associated-artifact manifest,
  `resolve_pack_artifact()`, the `raes-env-pack-exact-copy` profile,
  `validate_pack_content_manifest()`, and `PackDigestError`. SDL-only edits use
  `tools/refresh_pack_sdl_binding.py`; changed or added bytes require full
  manifest derivation rather than independent checksum edits.
- TechVault-specific regression joins belong in `tests/test_techvault_pack.py`.
  `packs/techvault/validation/validate_techvault.py` is the Suricata authoring
  gate, not a general runtime bootstrap framework or a second exception system.
- The TechVault provenance ledger remains the source for licensing,
  attribution, sensitive-data, real-credential, malware, and offensive-tooling
  review. New analyzer code cannot inherit the old APTL source attribution by
  convenience.

## Security and whole-repo gates

Any operational design crosses every layer below:

| Layer | Required guardrail |
| --- | --- |
| RAES shape and semantics | Parse through the pinned RAES models with their closed shapes, unique ids, reference checks, secret redaction, and `service_materialization` validation. A pack-local API payload schema or analyzer/connector semantic extension is forbidden. |
| Analyzer-content admission | Admit an exact, reviewed offline baseline. Definitions, executables, dependency manifests, licenses, and checksums must agree; reject extra files, symlinks, unsafe archive members, unpinned network installation, and analyzers that require undeclared external credentials or services. |
| Authentication and authorization | Separate temporary bootstrap authority from the dedicated connector principal. The connector has `read` and `analyze`, not `orgAdmin` or `superAdmin`; analyzer enablement runs only with the narrower administrative scope and is followed by readback. |
| Secret shape and binding | `operator_secret` entries omit values and are resolved only at the runtime secret boundary. A fixture key, if a governed RAES contract deliberately permits that research choice, is classified `secret_fixture` everywhere and equality is tested without printing it. Two same-named variables are not a key binding. |
| TheHive configuration | Do not use `--cortex-keys`: the official entrypoint accepts it, but the key then appears in process arguments. Prefer an existing typed secret-file/reference projection consumed by native configuration; account for ownership, mode, read-only mounts, reload, and deletion/rotation. |
| OS/container exposure | Run local offline analyzers as the existing non-root Cortex identity with bounded CPU, memory, time, output, and job directories. Do not mount the host Docker socket, make it world-writable, clone at startup, or grant analyzers ambient host/network authority. Account for `/proc`, inherited environment, shell tracing, crash dumps, temporary files, and container inspection. |
| Network and transport | The current Cortex and TheHive ports are loopback-published, while their internal hop is HTTP on `security-net`. If retained as a disposable-lab exception, describe it as unencrypted transport carrying API-key authentication, not TLS or production-safe trust. TLS/SAN/trust-store redesign is separate work. |
| Persistence and reconciliation | Reconcile desired state idempotently: create missing owned objects, accept matching state, and reject or safely report foreign/conflicting state. Never delete an organization, rotate a key, disable analyzers, or rebuild an Elasticsearch index merely to converge. Prove state after restart against the declared retained storage. |
| Readiness | Require Cortex API readiness, the exact enabled offline analyzer set, valid connector authentication, TheHive connector `OK`, and one bounded benign enrichment whose result is visible through the intended TheHive path. Port-open, `/api/status`, `/api/user/current`, or `/api/analyzer != []` alone is insufficient. Retry only transient startup states with a deadline. |
| Errors, logs, and evidence | Reuse bounded stable diagnostics and correlation ids. Never expose raw API responses, authorization headers, keys, passwords, analyzer inputs/reports, absolute host paths, environment dumps, or upstream exception text. Distinguish unavailable, unauthorized, missing definition, disabled, execution failure, timeout, and connector failure. |
| Pack content identity | Any SDL, analyzer asset, provenance, or documentation edit changes the exact pack inventory. Derive all sizes, checksums, exact-source identities, and the RAES associated-artifact set digest from the final immutable bytes. |

The exact selected Cortex image must be inspected before choosing the local
runner. If it does not contain the required interpreter and native libraries,
use an independently reviewed immutable source artifact that contains the exact
offline analyzer closure and pin it through the existing source requirement.
Do not install `latest` packages during startup or silently mutate the selected
Cortex container after realization.

## Extensibility and proof boundary

The extension seam is a versioned, data-driven offline analyzer baseline joined
to a provider-neutral initial-service-state contract and a dedicated integration
identity/secret reference. The baseline carries exact analyzer definition ids,
supported data types, runtime/dependency identity, non-secret configuration,
and enablement policy. Adding another offline analyzer should extend that data,
not add another bootstrap script or hard-coded API call. Analyzers requiring
external APIs belong in a separate optional profile with explicit operator
credentials and egress policy.

Pack-local tests can prove typed declarations, exact artifact resolution,
expected analyzer ids, classifications, absence of Docker-socket/argv-key
shortcuts, topology and persistence joins, readback intent, and status-only
wording. They cannot prove a native analyzer executes or that TheHive observes
its report.

LilRAE integration evidence for operational mode must start from a clean
admitted pack, execute one benign offline analyzer through the intended TheHive
path, verify bounded output, restart Cortex and TheHive, and repeat the
readback. Negative cases cover missing/invalid connector credentials, excess or
missing analyzers, unavailable runner dependencies, timeout, conflicting owned
state, and no secret leakage. Status-only mode instead proves that TheHive has
no configured Cortex connector and exposes no enrichment affordance; it must
not suppress or relabel a real connector `ERROR`.

## Non-goals and rejected shortcuts

- Do not add responders, online reputation services, third-party API keys,
  unrestricted egress, or a general Cortex analyzer marketplace.
- Do not mount `/var/run/docker.sock`, run Cortex/analyzers privileged, install
  dependencies from the network at startup, or use mutable catalog URLs.
- Do not reuse an `orgAdmin` service account as TheHive's runtime credential or
  put an API key in command arguments, checked-in real secrets, logs, evidence,
  or error messages.
- Do not add another init container, shell/curl reconciler, pack-local schema,
  exception hierarchy, or downstream-specific bootstrap hook.
- Do not treat installed definitions as enabled analyzers, an enabled analyzer
  as executable, connector `OK` as successful enrichment, or container health
  as any of those outcomes.
- Do not modify the reusable TheHive kit, pack tooling schemas, release
  machinery, or RAES semantics for this TechVault-specific decision.
- Do not upgrade TheHive, Cortex, or Elasticsearch, redesign the SOC PKI, or
  claim production hardening as part of this issue.
- Do not encode LilRAE host paths, Compose names, catalog vocabulary, or secret
  store coordinates into the canonical pack contract.

No new ADR is required. ADR 0009, ADR 0036, and the public
[ownership boundary](../public/ownership-boundary.md) already decide the
authority split. The relevant component contracts are documented by the
official [Cortex first-start guide](https://docs.strangebee.com/cortex/user-guides/first-start/),
[Cortex API guide](https://docs.strangebee.com/cortex/api/api-guide/),
[analyzer installation guidance](https://docs.strangebee.com/cortex/installation-and-configuration/analyzers-responders/),
and [TheHive Cortex connector guidance](https://docs.strangebee.com/thehive/administration/cortex/add-a-cortex-server/).
