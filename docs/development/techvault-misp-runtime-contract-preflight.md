# TechVault MISP runtime-contract preflight

Issue #280 is a missing portable service contract plus a downstream realization
failure. TechVault must state the observable MISP, MariaDB, Redis, trust, and
readiness outcomes that belong to the scenario. LilRAE must select components,
lower those outcomes into each selected component's configuration interface,
and prove them without recreating or mutating containers after realization.
Neither side may use the other's data as a substitute for its own authority.

This note records the current contract, the ownership classification, and the
cross-cutting gates for that work. It is not an implementation plan.

## Current contract and recovery evidence

The checked-in SDL is backend-neutral. It declares `realization.default: open`,
has no realization constraints or node sources, and the TechVault validator
rejects node images, runtime environment, container commands, backend mounts,
capability grants, restart policy, and host publication. The current authored
MISP graph contains:

- an HTTPS MISP application and threat-intelligence capability at product
  version 2.5.44, with an operator-secret API principal;
- MariaDB 10.11, the logical `misp` database, and retained database state;
- Redis 7 at `misp-redis:6379`, with `noeviction`, AOF disabled, and ephemeral
  cache intent;
- dependency order from MISP to both services, but no typed application
  upstream bindings or authenticated readiness criteria;
- retained MISP configuration and data volumes; and
- a generated SOC certificate bundle whose MISP leaf, private key, and public
  CA are projected read-only to MISP, while the sync client receives only the
  CA and requires certificate verification.

The repository history retains useful recovery evidence, but it is not current
authority. The retired realization selected the exact MISP 2.5.44 image digest
and MariaDB/Redis images, configured database facts on both peers, supplied an
administrator/API key, and mounted the MISP leaf at nginx-specific paths. It
also started Redis with a password in process arguments while giving MISP only
`REDIS_HOST`; those two authentication contracts could not agree. Its login-page
healthcheck did not prove authenticated API readiness.

The historical MISP digest resolves to the upstream MISP Docker 2.5.44 image.
That component's published contract includes MySQL host/port/user/password/
database, Redis host/port/password and an explicit passwordless opt-in,
administrator/base-URL settings, and certificate files named `cert.pem` and
`key.pem` under its nginx certificate directory. The MariaDB image initializes
database, user, and password state only for a fresh data directory. These facts
identify obligations for a backend that selects those components; they do not
restore image or environment selection to the pack.

## Authority and fact classification

Every fact in the completed contract must retain one of these owners:

| Fact | Classification and carrier | Observable satisfaction |
| --- | --- | --- |
| MISP capability, version, HTTPS service, and authenticated API | Authored TechVault outcome through existing RAES application, platform-application, authorization, service, and listener fields | The declared HTTPS service presents MISP 2.5.44 behavior and rejects an unauthenticated API request. |
| MISP-to-MariaDB relation | Authored TechVault outcome through a `RuntimePlatformApplication.upstream_bindings` data-source join plus the existing database service | An authenticated MISP API write and read uses the declared `misp` database on the declared node/service. Dependency order alone is not satisfaction. |
| Database name, application role, grants, and authentication posture | Authored TechVault outcome through `RuntimeDatabaseService` databases, roles, grants, and settings | Native database readback shows exactly the declared logical database/role/grants and authenticated application access. |
| MISP-to-Redis relation and Redis authentication posture | Authored TechVault outcome through an application upstream binding, the existing datastore service, and an authorization reference/principal where the pinned RAES contract fits | MISP performs an authenticated Redis operation against the declared endpoint; anonymous and mismatched credentials fail. |
| Base URL and TLS server identity | Authored observable product settings, not environment-variable names | MISP reports the authored canonical URL and a verification-required client accepts the leaf for the authored internal service identity. |
| MISP administrator and sync API principals | Authored identities and privilege/posture; credential bytes are operator input and remain `operator_secret` | Authenticated administrative/API operations succeed with the supplied principal; evidence carries no credential value. |
| MariaDB and Redis credential bytes | Backend-selected open realization unless the scenario owner deliberately makes exact bytes participant-relevant | The backend applies one internally consistent choice to both peers and records the choice class, not the bytes. Do not relabel infrastructure credentials as fixture secrets merely because the retired Compose file used literals. |
| Fixture credentials | Authored only when exact synthetic bytes are intentional participant-visible scenario content | No MISP, database, or Redis credential is a fixture by default. A future fixture must be explicitly justified and classified without leaking into evidence. |
| MISP leaf, private key, and CA | Existing RAES generated-artifact outputs; bytes are backend-generated, not pack content | Output selection, sensitivity, lifecycle, hostname identity, permissions, and verification are corroborated. The CA private key remains producer-private. |
| Image-specific certificate/configuration placement | Backend-selected realization detail | The selected image starts with the declared certificate and settings effective before readiness; any extra open-realization placement is disclosed. There is no post-start copy, exec fixup, or container recreation. |
| Component image, image defaults, and entrypoint behavior | Backend-selected open realization and digest-bound artifact inspection | The admitted plan names the immutable selected artifact and separately records which defaults were relied on. A useful default is not an authored requirement. |
| Probe implementation and retry policy | Backend choice constrained by authored readiness criteria | Bounded, authenticated probes exercise the real database, Redis, and HTTPS trust paths; an open port or login page is insufficient. |
| Retained MISP/DB state and ephemeral Redis state | Existing RAES persistent-volume and datastore persistence declarations | Clean-start evidence uses fresh retained volumes; separate restart evidence proves intended persistence without letting stale state mask missing configuration. |

Do not force all values into one environment map. Authored requirements,
operator inputs, generated outputs, backend choices, image defaults, and
observations have different provenance and lifecycle even when one selected
image eventually consumes them as environment variables.

## Canonical contracts and incumbents

The implementation must compose the existing authorities:

- The exactly pinned RAES models and `raes.parse_sdl` / `parse_sdl_file` own SDL
  shape and meaning. Reuse `RuntimePlatformApplication.upstream_bindings` and
  `settings`, `RuntimeDatabaseService`, `RuntimeDatastoreService`,
  `RuntimeAppAuthorization`, `RuntimeServiceListener.readiness`,
  `generated_artifacts`, and `persistent_volumes`. Add no MISP schema, DTO,
  enum, parser, or exception hierarchy here.
- `infrastructure.dependencies` remains startup ordering. It does not replace
  an application binding, effective endpoint, authentication contract, or
  readiness observation.
- `validate_pack()` and author CI in `content_ci.py` remain the pack gates.
  `packs/techvault/validation/validate_techvault.py` may enforce the exact
  first-party MISP joins the generic upstream semantic pass does not yet
  resolve, following the existing Cortex/Suricata/Wazuh contract checks. It
  must not become a reusable database, Redis, TLS, or readiness validator.
- `tests/test_techvault_pack.py` is the canonical exact-contract regression
  surface. Mutations should prove each join and classification fails
  independently, without printing raw SDL or values.
- `validate_pack_content_manifest()` and `PackDigestError` own pack byte/set/
  parent binding. An SDL-only edit uses `tools/refresh_pack_sdl_binding.py`; a
  changed or added pack member requires full content-manifest derivation.
  Checksums, sizes, concept subject digests, and the set digest are never
  hand-patched.
- `associated-artifacts.json` identifies immutable files shipped by the pack.
  It is not an inventory of selected images, runtime-generated certificates,
  credentials, retained volumes, or realization evidence. The provenance
  ledger must continue to attest that no real credentials or sensitive data
  ship in the pack.
- LilRAE's admitted-plan, secret-resolution, generated-artifact, component
  adapter, observation, diagnostic, and realized-form reporting paths are the
  runtime incumbents. Extend their generic seams rather than adding a
  TechVault-named post-start fixup.

The pinned RAES contract has two relevant expressivity limits. Generated
certificate artifacts do not type a subject/SAN/issuer/key-usage profile, and
separately classified secret requirements do not create a typed shared-secret
equality reference. A prose label, matching setting id, environment name, or
generated-artifact `provenance` string must not acquire either meaning. If the
required author-owned identity or shared-secret join cannot be represented by
an already governed RAES profile, the change is blocked on an upstream RAES
contract and exact-pin advance; do not encode a private convention here or in
LilRAE.

## Cross-cutting security and reliability gates

| Layer | Required behavior |
| --- | --- |
| RAES shape and semantic validation | Preserve closed models, unique ids and settings, same-node service ownership, generated-output selection, stateful-resource references, mount-collision checks, authorization references, realization designation, and compiled verification requirements. Unknown convenience fields fail closed. |
| TechVault realization-method policy | Keep the open, backend-neutral contract and the existing prohibition on node sources, runtime environment, container commands, backend mounts, capabilities, host publication, and restart policy. Product settings describe observable final state; they must not smuggle image variable names or launch recipes back into SDL. |
| Authentication and authorization | MISP API, database, and Redis authentication postures must be explicit and mutually consistent. Model MISP principals, database roles/grants, and Redis authorization with their existing typed families; do not treat connectivity, a configured username, or a successful anonymous ping as authorization. |
| Secret handling | `operator_secret` and `redacted` fields carry no raw value. Fixture secrets require deliberate scenario ownership. Generated outputs use value-free RAES references only where the governed contract supports them. No credential appears in pack assets, associated-artifact metadata, process argv, healthchecks, evidence, logs, diagnostics, container names, or exception text. |
| OS/container exposure | Do not repeat the retired `redis-server --requirepass ...` pattern. A selected adapter must use a component-supported secret/configuration carrier, restrict file ownership/modes and process visibility, account for `/proc`, container inspection, child inheritance, shell tracing and crash output, and fail before start if it cannot do so safely. |
| TLS and generated material | Preserve output sensitivity, producer-private CA key, least-output consumer selection, and read-only projection. Validate certificate identity before `reuse_valid`; existence and expiry alone are insufficient. Never copy a private key into evidence or use an image self-signed default as the declared trust result. |
| Configuration shape | Backend component adapters validate their closed input shape before side effects, reject missing/unknown/conflicting values, and map only admitted authored facts and disclosed backend choices. They must not scrape an environment dump or infer authority from a node name. |
| Readiness | Database readiness proves authenticated connectivity and expected logical state; Redis readiness proves the selected auth posture and cache policy; MISP readiness performs an authenticated API operation with certificate verification and database/Redis dependencies effective. Apply bounded timeouts and retry only transient startup states. |
| Persistence | Test a truly fresh realization separately from restart/reuse. MariaDB initialization variables do not repair an existing retained data directory, MISP's retained config can preserve old bootstrap state, and `reuse_valid` certificates can preserve the wrong identity. Stale state must fail or be deliberately migrated, never mask drift. |
| Evidence and provenance | Keep author-declared requirements, processor-derived requirements, admitted backend choices, artifact-satisfaction disclosure, and observed results as separate records. Runtime evidence is not the pack provenance ledger or associated-artifact manifest. Report the selected image digest and value-free configuration classes, observations, and correlation ids. |
| Error and logging envelope | Static failures reuse bounded `Diagnostic` / `ValidationResult` and stable pack-relative ids; libraries remain silent and unexpected defects still raise. Runtime failures use LilRAE's existing correlated realization diagnostics. Neither side emits raw upstream exceptions, responses, configuration bodies, absolute host paths, certificate bytes, or secrets. |
| Release workflow | Preserve TechVault wheel/sdist inclusion, pack validation, release checks, distribution tests, byte compilation, and Release Please ownership of version and changelog. |

## Extensibility seam

The seam is the provider-neutral application-to-service binding plus observable
auth, trust, and readiness policy. A future MariaDB-compatible database, Redis
implementation, MISP image, secret carrier, certificate generator, or probe
varies behind the admitted backend component adapter and realization evidence.
It must not require a TechVault node-name switch, a new pack field, or edits to
the canonical scenario merely to rename an image environment variable.

The adapter input is the compiled RAES requirement plus the selected immutable
component contract. Its output is a pre-start configuration and value-free
realization disclosure. Component-specific variable names, file paths,
entrypoints, and health commands stay inside that adapter. The same seam must
support a future component whose supported carrier is a secret file or native
configuration document rather than an environment variable.

## Proof boundary and failure cases

This repository can prove the portable declarations, classifications,
cross-references, generated-output selection, retained/ephemeral state intent,
readiness criteria, pack identity, and rejection of inconsistent authored
variants. It cannot prove a container reached readiness or that a backend did
not mutate it.

Downstream integration evidence is therefore part of issue completion. It must
start from fresh storage and a clean admitted plan; cover database connectivity,
Redis authentication, certificate identity/placement, and an authenticated
MISP API operation; reject missing, substituted, anonymous, or contradictory
configuration; compare planned and realized component/configuration
inventories; and show no undeclared post-plan mutation or recreation. Restart
coverage is separate and must prove the declared persistence behavior. Negative
tests must include wrong database endpoint/name/role/credential, mismatched or
disabled Redis authentication, wrong or unreadable certificate/key, wrong TLS
identity or CA, stale retained configuration, and an API key that does not match
the declared principal.

A port-open result, container health, TLS handshake, login-page response,
successful configuration write, echoed desired state, or evidence collected
only after a replacement container does not satisfy the contract.

## Non-goals and rejected shortcuts

- Do not restore historical exact images, Compose environment, container names,
  host paths, launch commands, healthchecks, or APTL vocabulary to TechVault.
- Do not copy MISP Docker's current `main`/`latest` defaults into product-version
  requirements. A backend selecting the historical 2.5.44 digest must inspect
  and bind that immutable artifact's actual contract.
- Do not encode `MYSQL_*`, `REDIS_*`, `BASE_URL`, `ADMIN_*`, nginx paths,
  `requirepass`, or another image API in portable SDL.
- Do not classify database, Redis, administrator, or API credentials as fixture
  secrets solely to make a clean boot easy. Do not treat an image default as an
  operator input or an operator secret as a generated artifact.
- Do not infer shared-secret equality from repeated names, descriptions, empty
  redacted values, or provenance strings.
- Do not add a second application/database/datastore/certificate/readiness
  schema, generalized pack validator, runtime exception family, logger, secret
  store, or persistence layer.
- Do not preserve APTL's post-start mutation under a new name, weaken closed
  validation to admit it, or count the recreated container as the original
  realized component.
- Do not claim static pack validation proves live readiness, persisted behavior,
  file permissions, certificate identity, secret equality, or absence of
  runtime mutation.

No new ADR is required. ADR 0009, ADR 0036, and the public ownership-boundary
document already assign RAES semantics, TechVault authoring, and LilRAE
realization. This note narrows their application to issue #280.

## External component references

- [MISP Docker configuration and certificate layout](https://github.com/MISP/misp-docker)
- [MISP Docker environment reference](https://github.com/MISP/misp-docker/blob/master/template.env)
- [MISP Docker reference Compose file](https://github.com/MISP/misp-docker/blob/master/docker-compose.yml)
- [MISP Docker 2.5.44 package identity](https://github.com/MISP/misp-docker/pkgs/container/misp-docker%2Fmisp-core/)
- [MariaDB official image configuration](https://github.com/docker-library/docs/blob/master/mariadb/content.md)
- [Redis official image packaging](https://github.com/redis/docker-library-redis)
