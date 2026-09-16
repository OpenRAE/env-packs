# TechVault internal service ports preflight

Issue #373 is a realization-boundary correction, not a new networking model.
TechVault must state the services that exist inside the scenario and the
topology over which participants and scenario components reach them. It must
not select a host interface, allocate a host port, or require host publication.

The current `dev` baseline already has the intended shape: the listed services
are declared through RAES `Node.services`, relevant runtime contracts refer to
those service ids, the nodes are joined through `infrastructure` links, and the
pack-local realization validator rejects both
`runtime.network.published_ports` and listener `published_port_refs`. The
earlier `publication.non-loopback-host-ip` policy has already been replaced by
that stronger backend-neutral rule. Work for this issue must preserve and prove
that contract rather than introduce another port or exposure abstraction.

## Authority and modeling boundary

RAES 5.0.0, exactly pinned by this repository, owns the SDL shapes and semantic
validation. The applicable carriers remain:

- `Node.services` for the in-world service name, service port, and protocol;
- `RuntimeServiceListener` when bind/listener state is itself an authored
  in-world fact;
- typed application, datastore, database, forwarding, and security-monitoring
  service references for semantic joins; and
- `infrastructure.<node>.links` for membership in the scenario network graph.

These are complementary facts. A dependency orders realization but does not
prove reachability. A listener does not prove readiness, authentication, or
authorization. A wildcard listener address such as `0.0.0.0` describes an
in-world bind and must not be reinterpreted as a host publication request.

The internal ports are the service ports, not the retired host translations.
The issue's bounded contract is:

| Node | Service | Port/protocol |
| --- | --- | --- |
| `wazuh-indexer` | `indexer-api` | `9200/tcp` |
| `wazuh-dashboard` | `dashboard` | `5601/tcp` |
| `wazuh-manager` | `wazuh-api`, `agent-events`, `agent-enrollment`, `syslog` | `55000/tcp`, `1514/tcp`, `1515/tcp`, `514/udp` |
| `misp` | `https` | `443/tcp` |
| `thehive` | `thehive-api` | `9000/tcp` |
| `cortex` | `cortex-api` | `9001/tcp` |
| `shuffle-frontend` | `https`, `http` | `443/tcp`, `80/tcp` |

Former host ports such as `443` for the Wazuh dashboard or `8443` for MISP and
`3443`/`3001` for Shuffle are not portable service facts.
No Docker `expose`, Compose `ports`, reverse-proxy, ephemeral-port, or
service-name-DNS schema belongs in this repository. A backend derives its
networking from the admitted RAES scenario and reports its realized choice.

The prohibition is TechVault's pack-specific open-realization policy. It must
remain in `validate_realization_method_contract`; it must not be generalized
into a second repository-owned SDL rule or used to reject RAES-valid content in
other packs whose authors deliberately select a realization constraint.

## Cross-cutting contracts

| Layer | Required guardrail |
| --- | --- |
| RAES parsing and semantics | Reuse `raes.parse_sdl` / `parse_sdl_file` through `validate_pack()` and author CI. Preserve closed shapes, service-reference checks, topology semantics, and parser resource limits. Add no local SDL schema, DTO, enum, parser, or exception hierarchy. |
| TechVault policy | Reuse `validate_realization_method_contract` and its stable `realization.host-publication` / `realization.listener-publication-ref` diagnostics. Replace neither with a loopback allow-list nor with duplicated service-port validation already owned by RAES. |
| Authentication and secrets | Port modeling neither grants anonymous access nor changes existing application authorization, TLS, generated-secret, or `operator_secret` contracts. Add no credential, environment-variable delivery shape, host trust path, or secret value. |
| OS and network exposure | The portable pack names no host IP, host port, socket-forwarding rule, reverse proxy, container engine, or firewall operation. In-container wildcard binds remain distinct from host interfaces. Host exposure is optional deployer state and must be collision-safe outside the pack. |
| Errors and logging | `validate_pack()` remains silent and returns bounded `Diagnostic` / `ValidationResult` data. The pack-local validator remains an author-CI subprocess with bounded output. Diagnostics identify stable fields only; they do not include SDL bodies, credentials, absolute paths, environment dumps, or raw exception text. Unexpected defects still fail rather than becoming successful validation results. |
| Persistence and artifacts | Port removal changes no persistent-volume or evidence-persistence contract. An SDL byte change must use `tools/refresh_pack_sdl_binding.py` so external-concept subject digests and the RAES associated-artifact manifest remain bound to the same bytes; hashes and set digests are never hand-edited. |
| Packaging and release | `packs/techvault` is the source; wheel installation projects it under package resources. Preserve the hosted-pack validation/release gates and release-please ownership of version and changelog. Do not patch a generated installed-resource copy. |

Tests should prove the exact TechVault service identities and internal ports,
their typed references and shared-network topology, plus the absence of the two
host-publication carriers. Absence checks must target `published_ports` and
`published_port_refs`; banning the entire `runtime.network` object would
foreclose unrelated RAES-valid in-world network facts. Static validation cannot
prove live DNS, firewall behavior, port allocation, reverse-proxy routing, or
concurrent-lab isolation; those are backend realization and integration proof.

The extensibility seam is the stable RAES node/service identity. A future
deployer may choose no publication, an ephemeral host port, or a per-lab proxy
without changing TechVault. A future in-world consumer refers to the same node
and service ids and joins the applicable scenario network; it does not depend
on a host port or a TechVault-specific mapping table.

## Non-goals and rejected shortcuts

- Do not change RAES models, copy their schema, or invent a pack-owned
  `expose`, DNS, endpoint, or publication contract.
- Do not rename internal service ports to historical host ports or retain a
  host binding as a participant-reachability hint.
- Do not encode LilRAE/APTL, Docker, Compose, rootless-daemon, reverse-proxy, or
  downstream catalog vocabulary in the portable pack.
- Do not weaken authentication, TLS, readiness, topology, or typed service
  references while removing a host-publication field.
- Do not add runtime logging, persistence, credentials, environment bindings,
  controllers, services, repositories, or deployment code.
- Do not broaden the generic pack validator with a TechVault policy or create a
  second validation workflow.
- Do not edit captured upstream asset prose merely to make it the portable
  contract; the RAES SDL and current TechVault docs are authoritative. Treat a
  source-artifact refresh as separate provenance and byte-identity work.
- Do not hand-edit the project version, changelog, binding digests, member
  checksums, sizes, or associated-artifact set digest.
