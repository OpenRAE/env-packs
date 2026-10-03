# Missing infrastructure kits preflight

Issue #225 adds eight first-party infrastructure kit releases. This note fixes
their architecture boundary before content is authored; it does not implement
the releases or prescribe an implementation sequence. Existing ADRs
[0009](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md),
[0035](../decisions/adrs/0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md),
and [0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
already govern the change. No new ADR or schema version is needed.

## Release boundary

Add exactly eight independently versioned `1.0.0` releases under `kits/`. Use
capability-oriented kit and module identities; the named implementation belongs
in the RAES node `source`, not in another product-specific manifest field.
`concern` remains a discovery aid, not a semantic or deployment classification.

| Kit identity | RAES source | Existing concern | Domain variation seam | Declared service boundary |
| --- | --- | --- | --- | --- |
| `infrastructure.certificate-authority` | `step-ca` | `identity-domain` | authority name | HTTPS CA API, normally `9000/tcp` for the selected source release |
| `infrastructure.dhcp-ipam-service` | `kea` | `network-shared` | address pool or subnet | server-side DHCP surfaces (`67/udp`, and `547/udp` only when DHCPv6 is declared) |
| `infrastructure.secrets-store` | `openbao` | `policy-operations` | non-secret mount or namespace name | client API `8200/tcp`; cluster `8201/tcp` only if the module actually declares clustering |
| `infrastructure.message-broker` | `rabbitmq` | `data-workflow` | virtual host | AMQP `5672/tcp`; management `15672/tcp` only if that plugin is part of the declared surface |
| `infrastructure.cache-key-value-store` | `valkey` | `data-workflow` | key prefix or cache profile | client service `6379/tcp` |
| `infrastructure.firewall-nat` | `nftables` | `network-shared` | ruleset name | no invented listener; filtering/NAT policy ports are seeded state, not node services |
| `infrastructure.ldap-directory` | `openldap` | `identity-domain` | directory suffix | LDAP `389/tcp`; LDAPS `636/tcp` only when the TLS surface is declared |
| `infrastructure.container-orchestration` | `k3s` | `data-workflow` | cluster name | author-facing API `6443/tcp`; node/overlay ports only when corresponding topology is modeled |

The numeric surfaces above are guardrails, not permission to copy every port an
upstream deployment might use. Confirm the selected source release and declare
only stable, author-relevant listeners. A RAES node service is a scenario-visible
service, not a Docker host publish, firewall opening, process bind address, or
complete vendor firewall matrix. In particular, `nftables` has no application
listener of its own; adding SSH or a fake management port would misdescribe it.

Every module retains the collection's established shared parameters
`deployment_profile` and `service_label`, plus the domain seam above. It exports
its node and `content.seed_inventory`, with other RAES declarations only where
the exact RAES 5.0.0 public contract supports the meaning. Generic LDAP must not
copy Active Directory forests, profiles, or controller relationships merely to
look like the existing AD kits. Relationships between DHCP/DNS, CA/consumers,
broker/clients, cache/applications, firewall/protected nodes, LDAP/members, or
k3s/workloads belong at the consuming pack root.

Seed inventories describe at least three useful, benign objects such as policy
names, pools, queues, exchanges, cache policies, directory containers, or
cluster namespaces. They contain no private keys, bootstrap tokens, unseal
material, RabbitMQ credentials, LDAP bind passwords, kubeconfigs, environment
variable coordinates, signed URLs, or example values that resemble live
secrets. A certificate name or secret-engine mount is acceptable metadata; a
certificate authority private key or stored secret value is not.

The existing
[`infrastructure.reverse-proxy-api-gateway`](../../kits/infrastructure.reverse-proxy-api-gateway/1.0.0/module.sdl.yaml)
already covers the load-balancer boundary: it declares a Traefik source,
HTTP/HTTPS services, route and upstream-binding seed objects, and an explicit
pack-root upstream relationship. Do not add a duplicate load-balancer kit.
A future demonstrated L4-only or algorithm-specific need should first test
whether it is a compatible new release/parameter of that kit; a product synonym
is not a separate reusable unit.

## Contracts and cross-cutting layers

The releases are ordinary inputs to the existing RAES-subordinate pack tooling;
they require no new controller, DTO, service, repository, persistence
store, exception family, logger, catalog registry, or workflow.

| Layer and canonical incumbent | Required guardrail |
| --- | --- |
| Carrier and schema: `src/raes_env_packs/resources/schemas/kit.schema.yaml`, `validate_kit_document()` | Keep `environment-pack-kit/v1` closed. Reuse its existing concern enum, resources, prerequisites, limitations, license, tests, component inventory, and associated-artifact pointer. Do not add product, port, seed, or runtime fields to the manifest. |
| Semantic authority: exact `raes==5.0.0`, `parse_sdl()`, `canonical_sdl_digest()` | Nodes, sources, services, parameters, exports, accounts, identity declarations, relationships, content and realization constraints are ordinary RAES SDL. Do not restate their schema or accept RAES-invalid vocabulary locally. |
| Infrastructure admission: `_validate_raw_module()` and `_verify_infrastructure_only()` | No agents, actions, behavior, conditions, objectives, injects, events, scripts, stories, workflows, scoring, telemetry, oracle, or runtime lifecycle semantics. Seed names are not a loophole for behavior. |
| Input and filesystem safety: `KitLimits`, strict YAML/JSON readers, `_pack_fs`, `_authoring_safety.admit_members()` | Preserve duplicate-key rejection, bounded nodes/depth/aliases/bytes/members, canonical relative paths, no links or special files, no sensitive filenames, and unchanged-inventory checks. All assets stay below the four safe non-executable destinations. |
| Secret and environment admission: `_secret_shape_violations()`, `_secret_parameter_name()`, `_normalize_parameters()`, `kit_cli._parameters()`, `AuthoringSession.call()` | Keep parameters bounded, public scalars. No secret-shaped names or values and no environment coordinates. Automation continues to pass parameter JSON through stdin, never argv. The loader does not inspect arbitrary module prose or asset values for every secret shape, so authored module descriptions, README, integration, and seed files still need explicit review. |
| Integrity and supply boundary: RAES associated-artifact models, `validate_associated_artifact_manifest()`, `associated_artifact_set_digest()` | Bind the exact release inventory, real byte checksums/sizes, canonical SDL parent digest, manifest id/version, and one immutable set digest. The kit's MIT license covers authored kit content; it does not relabel upstream product licensing. Keep the product source unresolved unless an immutable artifact is actually shipped or pinned. |
| Discovery and persistence: `load_kit_release()`, `build_kit_catalog()`, `inspect_kit()`, `KitRelease`/`KitSource` | Directory identity, manifest identity, module identity/version, and deterministic catalog projection must agree. The checked-in release directory is the source of truth; add no hand-maintained catalog index or database. A consumer's materialization ledger remains inert ownership/provenance, not a second module lock. |
| Materialization: `KitProposal`, `propose_*()`, `apply_proposal()`, `_transactions` | Existing proposal review, static successor validation, ownership conflict handling, concurrent-change checks, and atomic exchange apply unchanged. Kit assets never install validators, tests, hooks, workflows, or backend configuration. |
| Host authorization and write admission: `AuthoringSession`, `create_server()`, `_trusted_root()`, `_admit_tree()` | Discovery and inspection remain limited to host-admitted local source handles. MCP preparation and apply remain separate stored-proposal operations behind `allow_prepare` and `allow_writes`, a dedicated write root, review, and exact-input recapture. The local library adds no authentication or authorization policy; a hosting adapter retains actor authorization and redacted audit responsibility. |
| Errors and observability: `KitError`, `KitRecoveryError`, `Diagnostic`, CLI exits `0/1/2/3`, authoring safe envelopes | Keep failures bounded and value-free. Libraries remain silent; no kit-specific exception or logging layer. CLI/MCP output must not echo parameter values, credentials, parser internals, or upstream responses. |
| Repository gates: `tests/test_published_kits.py`, `tests/test_kits.py`, `.github/workflows/ci.yml`, `AGENTS.md` | The publication count becomes 46; every release must load deterministically, compose with default and materially different domain parameters, contain substantive authoring material, and preserve representative multi-kit composition. Use the repository's full verification commands; do not create a parallel kit validator. |

`raes-pack-validate --repo .` and `raes-pack-release check --all` remain pack
gates. Checked-in kit release admission is exercised by the unit suite through
`load_kit_release()` and the published-kit tests. Passing a YAML parse alone is
not release validation.

## Non-goals and anti-patterns

- Do not change the kit, catalog, materialization, pack, or RAES schemas for this
  collection extension, and do not duplicate any of their validation logic.
- Do not add a ninth load-balancer kit, product aliases, an authored catalog
  file, kit generator framework, runtime plugin, deployment recipe, container
  image, package installation, health probe, or backend capability claim.
- Do not treat a source name/version as an immutable artifact, SBOM, signature,
  vulnerability result, runtime readiness claim, or proof that a backend can
  realize the node.
- Do not turn OpenBao secret values, step-ca key material, RabbitMQ credentials,
  LDAP passwords, or k3s join tokens into parameters or benign seed examples.
- Do not represent nftables policy as a listening daemon, client ports as server
  listeners, optional management plugins as mandatory services, or every
  intra-cluster port as a public endpoint.
- Do not hand-edit `pyproject.toml` version or `CHANGELOG.md`. Each kit has its
  own `1.0.0` identity; repository package release metadata remains owned by
  release-please.

The extension seam is the existing RAES module parameter/export contract. One
reasonable future variation should be expressible by a domain parameter and
pack-root relationship without changing the kit carrier. If it instead needs a
new semantic concept, resolution belongs upstream in RAES; if it needs runtime
realization, it belongs in a backend.
