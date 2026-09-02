# TechVault Shuffle runtime-contract preflight

TechVault currently declares exact Shuffle backend and OpenSearch images, a
startup dependency, an OpenSearch inventory, and persistent volumes. It does
not declare the backend's effective datastore configuration, an application to
datastore binding, or a complete trust/readiness contract. A clean realization
therefore cannot be shown to satisfy the authored state. Replacing the backend
after realization only hides that gap.

Issue #281 is not a certificate-only defect. The issue author's component-level
clarification selects the narrow contract for this disposable research
environment: Shuffle connects to the exact OpenSearch DNS endpoint over TLS,
uses authored fixture credentials, and deliberately disables certificate
verification for that internal hop. This is encrypted, authenticated
application traffic with an explicitly observable verification exception; it
is not identity-verified TLS. The exception must not be described as trust
satisfaction or generalized to other consumers. This note records the existing
contract and the boundaries on that choice. It is not an implementation plan.

## Current contract inventory

| Concern | Authored state | Selected-component contract | Missing satisfaction evidence |
| --- | --- | --- | --- |
| Backend artifact | Exact `ghcr.io/shuffle/shuffle-backend@sha256:d4a5...` | The immutable image is the component identity. Mutable upstream `latest` documentation is not evidence of this digest's defaults. | Digest-bound image config/default-environment inspection and admitted artifact-satisfaction disclosure. |
| Datastore artifact | Exact `opensearchproject/opensearch:2.14.0@sha256:466a...` | OpenSearch 2.14 requires `OPENSEARCH_INITIAL_ADMIN_PASSWORD` when its demo security configuration is installed. Its demo HTTP certificate identities do not include `shuffle-opensearch`. | The selected security mode, endpoint identity, credential posture, and exact image-default facts. |
| Backend to datastore | `infrastructure.shuffle-backend.dependencies: [shuffle-opensearch]` and a shared `security-net` only | Shuffle expects a `SHUFFLE_OPENSEARCH_URL`; authenticated TLS also uses username/password, CA-file, and verification settings. | No backend environment, `RuntimePlatformApplication`, or `index_backend` upstream binding is authored. Dependency order is not connectivity. |
| Endpoint identity and trust | No OpenSearch certificate artifact, CA projection, network alias, or backend trust mount | Shuffle addresses `shuffle-opensearch:9200`; the selected demo certificate does not identify that hostname. The selected contract therefore requires TLS with client verification explicitly disabled. | The endpoint and verification posture are not yet authored together or asserted against the effective environment. |
| Authentication | OpenSearch contains the literal `StrongPassword123!`; backend contains no matching credential fact | OpenSearch bootstrap and Shuffle client credentials must agree. | Both values must be deliberately authored and classified as scenario fixture secrets; tests must lock their equality without emitting the value as evidence. |
| Logical datastore | `RuntimeDatastoreService` declares OpenSearch 2.14 and expected indices/mapping; `shuffle_opensearch_data` retains engine state | The backend creates and uses Shuffle indices after successful connection. | The datastore inventory omits its owning `service`, transport-security posture, endpoint, and authenticated operation readback. |
| SOAR application | `shuffle-api` is only a transport service | A listening backend is not necessarily initialized against its datastore or accepting authenticated application work. | No workflow-automation application capability, datastore upstream binding, authenticated readiness, or persistence evidence. |
| Persistence | `shuffle_data` and `shuffle_opensearch_data` are retained, single-writer volumes | OpenSearch state belongs under `/usr/share/opensearch/data`; Shuffle also uses its declared file/database location. | No clean-restart test proves application-visible state survives, and no evidence joins the observed state to the declared volumes. |

The current SDL has no `realization` designation. Under pinned RAES 3.3 that
means the legacy default is closed-world. The existing Shuffle image, network,
environment, and stateful-resource values classify as exact authored values;
an omitted backend environment is not permission for LilRAE to add arbitrary
entries. The author must explicitly designate any field where backend freedom
is intended. Backend freedom is never inferred from an empty list or a useful
image default.

The exact image digests are authoritative. The upstream Shuffle compose file
and documentation identify the relevant variable names and expected joins, but
their moving `main`/`latest` state must not be copied as the selected images'
contract. Those are image-artifact facts, not runtime-effective requirements.

The exact registry manifests were inspected on 2026-09-02 without executing or
pulling their filesystem layers:

- `shuffle-backend` resolves to linux/amd64 manifest
  `sha256:fa02b57c35f44cbf0beea742dc4c7c45953f28f94a2e831c4e665584c1710131`.
  Its image config declares only `PATH`, working directory `/app`, command
  `./shufflebackend`, and port `5001/tcp`; it declares no datastore or default
  administrator environment, entrypoint, user, labels, or healthcheck. The
  backend connection and bootstrap values therefore cannot be attributed to
  this image's default environment.
- `shuffle-opensearch` resolves to linux/amd64 manifest
  `sha256:c66e142a7753fff4a55009b88f013ce8649f8fe8b37d7d714d3c30b08846d419`.
  Its image config declares user `1000`, working directory
  `/usr/share/opensearch`, entrypoint `./opensearch-docker-entrypoint.sh`,
  command `opensearch`, ports `9200`, `9300`, `9600`, and `9650`, and version
  label `2.14.0`. Its default environment contains only process/runtime path
  facts (`PATH`, `JAVA_HOME`, and `LD_LIBRARY_PATH`), not an administrator
  credential or a Shuffle client contract; no image healthcheck is declared.

These inspections close the image-config inventory item. The issue clarification
supplies the missing authored component choice: the recovered fixture
configuration is runtime-effective state, not an image default or a backend
choice. LilRAE's implementation is outside this repository, so downstream
issues #913, #915, and #916 still own removal and rejection of the
post-realization replacement and the clean-realization observations. They do
not block authoring the complete portable contract here.

## Authority and classification

Keep these facts separate through authoring, realization, and evidence:

| Class | Owner and carrier | Rule |
| --- | --- | --- |
| Authored scenario requirement | TechVault through existing RAES SDL fields | Declares the required application capability, upstream service, endpoint scheme/name, verification posture, effective non-secret environment, stateful resources, and readiness/evidence intent. |
| Generated trust material | RAES `generated_artifacts` declaration, produced by the selected realizer | Not selected for this hop. If a future verified-TLS design generates certificates, declare output sensitivity, consumers, read-only mounts, lifecycle, and dependencies rather than embedding material in the pack. |
| Operator input | LilRAE's operator-secret authority; represented in SDL only by an existing redacted classification when RAES permits it | Not selected for these scenario credentials. Future operator secrets must carry no raw value in SDL, plan/result DTOs, argv, logs, diagnostics, or evidence. |
| Fixture secret | Authored `secret_fixture` because these exact disposable-lab bootstrap and default credentials are intentional scenario content | Keep the values in the effective environment only; evidence asserts classification, equality, and behavior without reproducing secret values. |
| Image default | `Source.build.config.default_environment` and other digest-bound image-provenance facts | Describes what the selected artifact contains. It does not silently become required runtime-effective state. |
| Backend choice | RAES realization designation/envelope plus selected backend configuration | Allowed only on an explicitly open or constrained surface. Provider IDs, storage implementation, secret-store coordinates, and probe implementation stay backend-local. |
| Observed satisfaction | RAES runtime snapshot, realization provenance/observation disclosure, and evidence records | Distinguishes `author-declared`, `processor-derived`, and `backend-realized`; records value-free corroboration without rewriting authored SDL. |

## Canonical RAES contracts to reuse

Pinned `raes==3.3.0` already supplies the applicable surfaces:

- `RuntimeEnvironmentVariable` is the effective environment contract. It
  rejects duplicate names and requires redacted/operator-secret entries to omit
  their values. Its `provenance` distinguishes image, operator, container, and
  runtime origins.
- `Source.build.config.default_environment` is the separate image-default
  inventory. Do not duplicate image defaults into effective environment unless
  TechVault requires that exact outcome.
- `RuntimeNetworkRealization` owns hostname, per-network aliases/DNS names, and
  host publication. `Node.services` owns transport identity. Do not encode a
  Compose container name or infer a certificate identity from either one.
- `GeneratedArtifact` and `PersistentVolume` own generated-output selection,
  producer-private disposition, read-only projections, persistent consumers,
  lifecycle, and ordering/refresh dependencies. Reuse their reference and
  mount-collision validation.
- `RuntimeDatastoreService`, its `nodes[].endpoints`,
  `transport_security`, settings, partitions, mappings, and owning `service`
  are the canonical datastore inventory. Do not add an OpenSearch-specific
  pack schema or place raw API responses in evidence.
- `RuntimePlatformApplication` with a `workflow_automation` capability and an
  `index_backend` `upstream_binding` is the canonical application/datastore
  relation. `Node.services` remains the transport layer; dependency ordering
  remains a separate topology fact.
- `RuntimeServiceListener.readiness` can attach bounded probe evidence to a
  listener, but listener reachability alone cannot prove authenticated Shuffle
  readiness. Use existing propositions, postcondition assertions, evidence
  requirements, and observation boundaries for authored satisfaction intent
  where their published semantics fit.
- SEM-218 explicitness and realization designation/envelope contracts own
  author/backend freedom. `RuntimeSnapshot.realization_provenance` and
  `realization_observations` own value-free evidence of the selected and
  observed outcome.

Two RAES 3.3 limitations are relevant to future strengthening but do not block
the selected fixture-plus-explicit-verification-exception contract:

1. `GeneratedArtifact(generator=certificate_bundle)` names outputs, consumers,
   sensitivity, lifecycle, and dependencies, but has no typed certificate
   subject, SAN, issuer, key-usage, or trust-profile fields. An opaque
   `provenance` string must not be reinterpreted as those semantics.
2. Two `operator_secret` environment entries have no typed shared-secret
   reference or equality join. Giving OpenSearch and Shuffle empty redacted
   values does not say that LilRAE must supply the same credential.

If a future authored outcome needs either typed join, use an existing governed
RAES contract if one is confirmed; otherwise fix the expressivity and
validation in RAES and advance the exact pin. Do not create TechVault-only
fields or teach LilRAE that a magic provenance string/environment-name pair has
new semantics. Issue #281 instead uses existing `secret_fixture` environment,
datastore transport-security, endpoint, application binding, and readiness
semantics, all of which validate in the pinned release.

RAES model construction validates closed shapes, secret redaction, unique ids,
datastore profiles, and local service ownership. One present limitation also
needs upstream attention: the current platform-application semantic pass does
not resolve `upstream_bindings.target_node_ref`/`target_service_ref` the way the
forwarding-agent pass does. Do not add a second production validator here. A
TechVault regression test may assert its exact authored join, but reusable
referential validation belongs in RAES.

## Cross-cutting gates

| Layer | Required guardrail |
| --- | --- |
| RAES source, shape, and semantics | Parse through the pinned `raes.parse_sdl_file` path. Preserve `extra="forbid"`, unique environment/stable ids, service/ref checks, datastore profile guards, stateful-resource references, and explicit realization closure. No parallel schema or validator. |
| Pack validation | Reuse `validate_pack()` and author CI's retained RAES scenarios. Diagnostics stay stable, bounded, pack-relative, and value-free; unexpected defects still raise rather than being mislabeled as input failures. |
| Artifact and provenance | Keep exact image identity distinct from inspected defaults and realized satisfaction. SDL-only edits use the canonical SDL-binding refresh; changed pack bytes use associated-artifact derivation and `PackDigestError`, never hand-patched independent hashes. |
| Secret handling | The selected exact credentials are authored `secret_fixture` values. Future operator secrets omit values and are resolved by LilRAE's secret boundary. Secret values never enter command arguments, environment dumps, container-inspect evidence, errors, or portable receipts. |
| TLS and endpoint identity | Author the exact HTTPS URL and datastore endpoint together, set datastore client verification false, and require the corresponding Shuffle skip-verification value. Tests reject any mismatch. This makes the exception observable; it does not treat the demo certificate as satisfying hostname or chain verification. |
| OS/container exposure | Read-only trust mounts must use declared contained destinations. Account for file ownership/mode, UID access, `/proc`, inherited environment, shell tracing, crash dumps, and container-inspect visibility. Credentials must not appear in argv or healthcheck command text. |
| Readiness | Gate on an authenticated application operation that exercises the selected datastore, after certificate and datastore health. A running container, open port, TLS handshake alone, dependency order, or unauthenticated `/health` is insufficient. Use bounded timeouts and retry only transient startup states. |
| Persistence | Prove a created application object is read back after backend and datastore restart using the declared retained volumes. Readiness and persistence are separate observations. |
| Evidence and errors | Preserve authored requirement, admitted backend choice, and observed satisfaction as separate records. Emit stable failure classes/correlation ids; never raw OpenSearch responses, exception text, credentials, certificates, host paths, or environment dumps. |

The extensibility seam is the provider-neutral application-to-datastore binding
plus explicit endpoint/trust/authentication policy. A later OpenSearch cluster,
different DNS alias, rotated issuer, API-key authentication, or alternate
backend must vary through that seam and the realization envelope, not through
new Shuffle-specific pack fields or another post-start replacement hook.

## Proof boundary

Pack tests can prove typed declarations, exact image identities, fixture-secret
classification, endpoint/transport/environment consistency, application and
datastore cross-references, volume ownership, readiness intent, and closed
runtime shape. They cannot prove that LilRAE reaches application readiness or
persists a live application object.

LilRAE integration evidence must begin from a clean admitted pack and cover
datastore connection, authenticated application read/write, the authored
disabled-verification posture, negative trust/configuration cases, restart
persistence, bounded readiness failure, and an exact before/after
container/configuration inventory. The final inventory must show no replacement
container and no missing, substituted, or excess closed configuration.

## Non-goals and rejected shortcuts

- Do not copy current `main`/`latest` compose defaults into an immutable image
  contract; inspect the exact selected digests.
- Do not preserve or rename LilRAE's post-realization backend replacement.
- Do not treat dependency order, a service port, container health, or a TLS
  handshake as authenticated application readiness.
- Do not generalize the deliberately authored fixture credentials into an
  operator-secret pattern or log them to prove equality.
- Do not describe `SHUFFLE_OPENSEARCH_SKIPSSL_VERIFY=true` as hostname, chain,
  or trust satisfaction. It is the selected, observable exception for this
  internal disposable datastore only; other clients remain unaffected.
- Do not embed certificates/private keys as pack bytes, copy a CA out of a live
  container after start, or give consumers a CA private key.
- Do not conflate image defaults, authored effective environment, generated
  material, admitted backend choices, and observations in one environment map.
- Do not duplicate RAES environment, datastore, platform-application,
  realization, readiness/evidence, diagnostic, or exception contracts here.
- Do not encode downstream catalog or deployment vocabulary into the canonical
  pack contract.

No new ADR is required. ADR 0009, ADR 0036, and the public
[ownership boundary](../public/ownership-boundary.md) already decide the
repository boundary. The selected contract is expressible with RAES 3.3 and
does not require a semantic extension. A later verified-TLS/shared-operator-
secret design would require revisiting the two limitations above upstream.

## External component references

- [Shuffle configuration](https://github.com/Shuffle/shuffle-docs/blob/master/docs/configuration.md)
- [Shuffle environment reference](https://github.com/Shuffle/shuffle-docs/blob/master/docs/getting_started.md)
- [Shuffle reference Compose file](https://github.com/Shuffle/Shuffle/blob/main/docker-compose.yml)
- [OpenSearch container security modes](https://github.com/opensearch-project/opensearch-build/blob/main/docker/release/README.md)
