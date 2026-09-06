# TechVault runtime desired-state preflight

Issue #259 must complete TechVault's portable runtime declarations without
turning this repository into a second RAES schema authority or a LilRAE
configuration repository. This note records the modeling boundary and the
cross-cutting gates for that work. It is not an implementation plan.

## Current baseline

The current SDL has 38 nodes: five network nodes and 33 compute nodes. All 33
compute nodes are now `type: compute` with an exact
`operating-system-container` realization constraint. The issue's original list
still names the right functional areas, but three entries have since gained
typed application contracts (`thehive`, `cortex`, and `shuffle-backend`), and
`cortex-index-init` has been replaced by the API-driven
`cortex-initializer`. Completion must extend those current contracts rather
than restore the earlier topology.

The retired Compose file is recovery evidence for effective environment,
restart, memory, listener, and mount facts. It is not a runtime authority and
must not be restored, referenced by a backend, or treated as stronger than the
current exact image/content identities and RAES SDL.

## Authority and modeling decisions

RAES 3.5.0, pinned in `pyproject.toml`, owns every SDL shape and controlled
value used here. TechVault authors instances of those contracts; LilRAE binds
them to a concrete container runtime. The following distinctions are binding:

| Concern | Canonical carrier | Guardrail |
| --- | --- | --- |
| Transport identity | `Node.services` plus `RuntimeServiceListener` | A service name/port/protocol and a listener's bind/scope are transport facts. They are not application readiness. The listener model has no `role` field; use its `service` reference and use typed endpoint/binding roles only where RAES defines them. |
| HTTP/API surface | `RuntimeApplicationSurface` and its routes | Use for a concrete HTTP/HTTPS surface or proxy route. Its `upstream_target` is the typed, semantically validated proxy join. Do not make a TCP proxy or non-HTTP collector invent a route. |
| Product capability | `RuntimePlatformApplication` | Use only for platform meaning such as threat intelligence, case management, SOAR, or analytics presentation. This may coexist with a generic HTTP surface because the two contracts answer different questions; it must not duplicate one logical platform into separate frontend/backend products. |
| Relational database | `RuntimeDatabaseService` | MISP MariaDB belongs here, with its owning service and intended logical database. Do not model it as a generic application or copy the database schema model. |
| Search/cache/trace store | `RuntimeDatastoreService` | Redis uses the native `redis`/`key_value` vocabulary. Tempo may use the existing `other` engine/data-model escape values with an honest description; no TechVault-only trace-store schema or enum is permitted. |
| Directory authority | `RuntimeIdentityAuthority` plus the existing scenario `identity_domains`, relationship, and accounts | Samba AD is a domain/directory authority, not a collection of local OS identities. Runtime services describe the authority's protocols; the existing global accounts remain the authored scenario identities and must not be copied into runtime `subjects`. |
| One-shot Cortex bootstrap | Existing `runtime.container.autoremove`, environment/value references, exact content placement, and infrastructure ordering | `RuntimeScheduledJob` explicitly means a recurring scheduled job. It must not be used to disguise the initializer. If a realizing backend requires a typed initialization-step family beyond the existing container contract, that is an upstream RAES expressivity gap and must be tracked there before authoring a workaround. |
| Kali capture sidecar | Existing namespace, capability, and persistent-volume contracts; `RuntimeNetworkSensor` only for the tcpdump/packet-capture portion | The capture sidecar is not an application or log-forwarding agent. Do not claim that a network-sensor record describes its audit/process-capture or authorization semantics. Those remain under the separate capture/evidence boundary. |
| TCP proxies | Container/environment, `Node.services`, and `RuntimeServiceListener` | `RuntimeForwardingAgent` covers log forwarding and content sync, not arbitrary TCP proxying. The web HTTP proxy may additionally use an application route with `upstream_target`; the Kali SSH proxy may not. |
| OpenTelemetry collector | Exact config content, services/listeners, environment, and container/operational policy | RAES's current forwarding-agent kinds are log forwarding and content sync. An OTLP trace pipeline must not be mislabeled as either. If a typed trace-collector family is required by the realizer, file the RAES gap rather than adding a field or magic setting here. |
| Dependency | `infrastructure.<node>.dependencies`, typed application upstream bindings where applicable, and effective endpoint configuration | Startup order, logical application dependency, and the concrete endpoint consumed by an image are three separate facts. Declare each applicable fact; never infer connectivity or configuration from order alone. |
| Mount intent | Existing `content` targets, `generated_artifacts[].consumers`, `persistent_volumes[].consumers`, or `runtime.mounts` for an otherwise unowned mount | Each destination has one authority. Do not repeat generated-artifact or persistent-volume consumers under `runtime.mounts`; RAES's collision/reference validation must remain authoritative. |
| Runtime policy | `RuntimeOperationalPolicy` and `resource_limits` | The historical per-service memory cap and restart policy are admissible recovery evidence. `Node.resources` requires both CPU and RAM, so it must not be populated with an invented CPU value. Keep provider reservations, cgroups, and host sizing backend-local. |

The resulting family classification is bounded as follows:

- MISP, the Wazuh dashboard, and the Grafana dashboard may carry both a generic
  application surface and a platform-application capability because the
  records are complementary. TheHive, Cortex, and Shuffle backend retain their
  existing platform application identities; generic surfaces may describe
  their actual APIs without replacing those identities.
- MISP MariaDB, MISP Redis, and Tempo use the database/datastore families.
- Shuffle frontend and the web HTTP proxy use generic application surfaces,
  with upstream joins where the route is truly proxied.
- Samba AD uses the identity-authority family. Kali capture uses the
  network-sensor family only for its packet-capture role.
- Cortex initializer, Kali SSH proxy, and the OTLP collector remain honestly
  described by the existing common runtime contracts unless RAES gains an
  applicable semantic family. A non-matching family is worse than an explicit
  upstream gap.

RAES 3.5 validates that application, listener, datastore, and identity-service
records reference a service declared on the same node. It also validates
network-sensor network references and duplicate runtime identifiers and
environment names. It does not currently resolve
`RuntimePlatformApplication.upstream_bindings.target_node_ref` or
`target_service_ref`. A TechVault regression test must lock each exact authored
platform join, but reusable referential validation belongs upstream in RAES,
not in a new pack validator.

## Security and cross-cutting gates

| Layer | Required outcome |
| --- | --- |
| RAES source/shape/semantics | Parse through the pinned `raes.parse_sdl` and `parse_sdl_file` paths. Preserve closed models, portable identifiers, unique ids/environment names, service and network references, generated-value references, mount collision checks, and realization constraints. Add no local SDL schema, parser, enum, or exception hierarchy. |
| Authentication surfaces | Operator-facing publications remain explicit and loopback-only. Internal listeners remain internal/network-scoped. A listener or open port does not imply anonymous access, authenticated readiness, or authorization. Application/datastore bindings must agree with the effective scheme, service, and authentication posture. |
| Secret shape and lifecycle | Use `RuntimeEnvironmentVariable.value_classification` and `value_from`. `operator_secret` and `redacted` values carry no authored secret value; a generated value is referenced by one output from every consumer that must share it. Use `secret_fixture` only for an intentional synthetic scenario credential. Do not coordinate two consumers through an environment-variable name convention. |
| OS/container exposure | No secret belongs in container command/entrypoint arguments, a healthcheck command, logs, diagnostics, evidence, or an environment dump. The existing TheHive `--secret` literal and the historical Redis `--requirepass` argv pattern must not be copied as the completed design; use an image-supported environment/configuration carrier or raise an upstream expressivity gap. Account for `/proc`, container inspection, child inheritance, shell tracing, UID/GID access, modes, and crash output. |
| TLS and generated material | Keep certificate/key/password outputs in the existing generated-artifact authority, select only the outputs each node needs, and mount them read-only. Effective application configuration must reference the declared in-container destinations and the endpoint scheme must match. Never place a host certificate path or trust-store coordinate in SDL. |
| Network exposure | Use `RuntimeNetworkRealization.published_ports` for intended host publication and retain `127.0.0.1` for operator-only surfaces. `0.0.0.0` is valid as an in-container listener address, not as evidence that a host port should be globally published. No implicit `publish_all_ports`. |
| Capabilities and namespaces | Preserve least privilege: Samba's existing provisioning/network capabilities and Kali capture's capture-only capabilities stay scoped to those nodes. The capture sidecar shares only Kali's network namespace; no PID-namespace or capture-volume exposure to Kali is introduced. |
| Static pack validation | `validate_pack()` is the consumer authority and returns bounded, payload-free `Diagnostic`/`ValidationResult` records. Author CI composes it with the RAES file-backed parse, pack-local validators/tests, visibility scan, anti-extension guard, provenance, and manifest checks. Unexpected defects still raise instead of becoming input errors. |
| Content identity | `validate_pack_content_manifest()` and `PackDigestError` own byte/set/parent validation. An SDL-only change is rebound with `tools/refresh_pack_sdl_binding.py`; a changed or added pack member requires full `derive_pack_content_manifest()` derivation. Do not hand-patch independent checksums, sizes, or the set digest. |
| Logging/error envelope | This content change adds no logging layer. Any new exact-contract test or pack-local diagnostic names only stable node/service/field identifiers, never environment values, secret material, raw SDL, absolute paths, or raw upstream exception text. Do not introduce a runtime error model in this repository. |
| Release/package workflow | TechVault is force-included in the wheel and sdist. Preserve `raes-pack-validate --packs-root packs`, `raes-pack-release check --packs-root packs`, distribution-content tests, and the full repository verification sequence. Release Please alone owns project version and `CHANGELOG.md`. |

## Maintainability and proof boundary

The implementation must build on these incumbents:

- the pinned RAES runtime models and parser, not a copied SDL schema;
- `Node.services`, `infrastructure.dependencies`, `content`,
  `generated_artifacts`, and `persistent_volumes` already in the TechVault SDL;
- the existing TheHive/Cortex/Shuffle platform-application identities and
  Cortex generated-secret pattern;
- the generic application and database examples under `kits/` as examples of
  authored RAES values, while treating the pinned RAES package as normative;
- `validate_pack()`, the author-CI composition in `content_ci.py`,
  `validate_pack_content_manifest()`, and `PackDigestError`;
- TechVault exact-contract regression tests in `tests/test_techvault_pack.py`;
  and
- `tools/refresh_pack_sdl_binding.py` for an SDL-only byte change.

Static tests can prove that all 33 compute nodes have an admitted container
substrate, that the issue's 16 functional areas carry their selected existing
RAES contracts, and that service, endpoint, dependency, environment,
mount/persistence, secret, listener, and platform joins agree. They can also
prove that host publications stay loopback-only and that no backend fields or
host paths were added. They cannot prove that LilRAE created containers,
resolved operator inputs, generated secrets, enforced OS permissions, reached
readiness, or persisted data. Those are admitted-plan realization and observed
state, not pack validation.

The extensibility seam is the stable RAES node/service identity and typed
reference between families. A future UI, datastore, or backend should add
another data instance and reference existing service ids; it must not require a
new TechVault schema branch or a realizer switch on node names. Provider choice,
container names, host storage, profile selection, and probe implementation stay
behind the LilRAE realization boundary.

## Non-goals and rejected shortcuts

- No RAES model, vocabulary, or semantic-validator changes in this repository.
- No Compose file, backend adapter, host path, container name, runtime label,
  profile-selection rule, or LilRAE-specific DTO.
- No reintroduction of `cortex-index-init` or its retired Elasticsearch mapping.
- No claim that dependency order proves connectivity, a listener proves
  readiness, or persistent-volume declaration proves persisted behavior.
- No duplicate application, identity, datastore, mount, secret, validation,
  exception, logging, or workflow model.
- No invented CPU values, listener `role` field, cache-binding role,
  trace-forwarder kind, initialization-job family, or magic provenance string.
- No new environment outside TechVault and no downstream catalog vocabulary in
  the portable contract.
- No version or changelog edit.

If deterministic realization requires a fact that the pinned RAES contracts
cannot express, issue #259 stops at that boundary: record the upstream RAES
issue and link it rather than encoding the fact in a comment, environment-name
convention, pack-local schema, or backend special case.
