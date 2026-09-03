# TechVault Shuffle Orborus offline-runtime preflight

Issue #285 crosses the portable TechVault contract and LilRAE's Docker
realization boundary. The pack already declares the defining privilege: the
`shuffle-orborus` node holds a read-write Docker Unix socket and its
`RuntimeOrchestrationAuthority` is `host_root_equivalent`. Adding another
generic mount would duplicate that contract. The observed missing mount is a
downstream lowering defect unless the admitted plan has lost the authored
runtime fields before it reaches the backend.

The offline-image half is not already complete. The authority declares only a
mutable `ghcr.io/shuffle/shuffle-worker:latest` spawn template, and this
repository contains neither the seeded Shuffle workflow nor an inventory of
the app images that workflow launches. A clean range therefore has no exact,
reviewable image closure from which a backend can establish offline readiness.
This note fixes the design boundaries for both halves. It is not an
implementation plan.

## Current contract and ownership

| Concern | Canonical owner and incumbent | Current state | Guardrail |
| --- | --- | --- | --- |
| Orborus privilege | RAES `RuntimeOrchestrationAuthority` | `engine: docker`, `privilege_class: host_root_equivalent`, and `control_interface_ref: docker-sock` are authored. | Preserve this explicit root-equivalent classification; do not disguise the socket as an ordinary data mount. |
| Docker control interface | RAES `RuntimeControlInterface` | The same node declares `/var/run/docker.sock`, `kind: unix_socket`, and read-write access. RAES resolves the same-node reference and rejects a host-root-equivalent authority that does not point to a read-write Docker socket. | LilRAE lowers this interface to its trusted Docker adapter and verifies the effective endpoint. Do not add a parallel `runtime.mounts` entry or Compose fragment. |
| Child workload authority | RAES `RuntimeOrchestrationSpawnTemplate` | Only the Shuffle worker is listed, by mutable `latest`; no app-runtime images are listed. | The exact worker and app image closure must be derived from the authoritative seed and represented as digest-qualified authorized templates. Never infer it from whichever images happen to be cached. |
| Image acquisition | LilRAE artifact preparation and Docker backend | Node `Source.artifact_requirement` values have exact identities and preparation routes, but spawn-template image references do not. | Availability on the same daemon before isolation is a backend readiness postcondition. Do not reinterpret pack content copying or the component SBOM as image import. |
| Workflow execution | Shuffle and TheHive, observed by LilRAE | The webhook returns an execution id, but that alone does not prove a worker/app ran or a case was committed. | Readiness requires a terminal successful execution with result and TheHive case readback; bounded failure replaces indefinite `EXECUTING`. |
| Runtime state | Docker image store plus existing Shuffle/TheHive persistence | Daemon images are not pack bytes and are not a RAES `PersistentVolume`. | Keep image-cache preparation separate from application-data persistence and from pack content identity. |

TechVault, as a first-party pack, may author which child workloads the scenario
requires. RAES owns the meaning of orchestration authorities, control
interfaces, spawn templates, artifact requirements, workflows, evidence, and
realization explicitness. LilRAE owns trusted source acquisition, Docker API
access, image import/pull/cache behavior, startup, observation, and runtime
errors. The downstream seed name from the issue is evidence about the defect,
not canonical pack vocabulary.

The exact app-image list and immutable identities are not recoverable from this
repository. They are a required input to implementation, not a value to guess
from a live daemon, mutable registry tag, or moving upstream Compose file. If
the seed remains downstream-owned, its image dependency inventory and the pack
will have two authorities that can drift; acceptance must fail on that drift.
The durable outcome is one authored seed/dependency authority with a mechanical
projection into the child-workload closure, not two hand-maintained lists.

## Canonical incumbents to reuse

- `packs/techvault/sdl/techvault.sdl.yaml` already carries the same-node
  `local_control_interfaces` and `orchestration_authorities` join. Extend the
  existing authority's child-workload inventory only when exact image inputs
  are known; do not create a second Orborus node, mount schema, or runtime
  overlay.
- Pinned `raes==3.3.0` is the only SDL shape and semantic authority. Its base
  models reject unknown fields, its runtime model rejects duplicate control
  interface and mount targets, and its semantic pass resolves
  `control_interface_ref` and enforces the read-write Docker-socket profile.
- `Source.artifact_requirement` and its exact identity, permitted acquisition,
  and timing fields remain the artifact authority where RAES exposes a
  `Source`. Do not copy those fields onto a spawn template in this repository.
- `validate_pack()` and the retained author-CI scenarios are the shared pack
  parsing/validation path. `tests/test_techvault_pack.py` is the incumbent for
  exact TechVault contract regressions; its present string-only socket check is
  not proof of the structured join or image closure.
- `validate_pack_content_manifest()` and
  `tools/refresh_pack_sdl_binding.py` remain the byte-identity authorities for
  an SDL-only change. Checksums, sizes, and the associated-artifact set digest
  are derived from final bytes, never patched independently.
- `component_boundary.py` and `publication-supply.yaml` are inventory/SBOM
  surfaces only. Automatic component discovery follows RAES `Source` artifact
  requirements and therefore does not currently discover spawn-template image
  strings. An authored component row may disclose that limitation, but it
  cannot authorize acquisition or establish offline availability.
- `kits/infrastructure.shuffle-automation-service` is a generic static kit that
  explicitly disclaims launch and readiness. It is not the TechVault Orborus
  runtime contract and must not acquire Docker-socket privilege as a shortcut.
- LilRAE's admitted-plan Docker lowering, artifact preparation, readiness,
  bounded runtime diagnostics, and observation records are the runtime
  incumbents. The fix belongs in those shared paths rather than a
  Shuffle-specific host script or post-realization container replacement.

RAES 3.3 has an expressivity limit here:
`RuntimeOrchestrationSpawnTemplate.image_ref` is a string and cannot carry or
reference a `Source.artifact_requirement`. Digest-qualifying every authorized
image avoids mutable selection and gives LilRAE a closed preload set, but it
does not create a typed permitted acquisition route, trust join, publication
claim, or automatically derived SBOM component. If the portable contract must
author those claims, evolve the RAES spawn-template surface upstream by reusing
the existing `Source`/`ArtifactRequirement` authority and then advance this
repository's exact RAES pin. Do not add a TechVault-only field, schema, parser,
or magic image-reference convention.

## Cross-cutting gates

| Layer | Required guardrail |
| --- | --- |
| RAES shape and semantic validation | Parse through the exact pin. Preserve closed models, stable-id uniqueness, same-node reference resolution, and the `host_root_equivalent` Docker-socket profile. A generic mount does not substitute for a `RuntimeControlInterface`. |
| Realization and config shape | Carry the authored runtime fields through the admitted plan without dropping them. The Docker adapter maps the declared in-container control endpoint to its trusted host endpoint; pack data must not select an arbitrary host path, daemon URL, Compose service, group id, or socket permission policy. |
| Host authorization | Read-write Docker access is host-root-equivalent and has no useful read-only mode for spawning. Admit it explicitly only for Orborus, never expose the daemon over unauthenticated TCP, never pass it to spawned apps, and never widen host socket ownership or mode to make access succeed. |
| Host endpoint validation | Before starting Orborus, verify through the trusted adapter that the selected endpoint is the expected Unix socket and that an authorized Docker API operation succeeds. Reject missing, wrong-type, replaced, or inaccessible endpoints before accepting workflows. Do not follow an untrusted pack-provided link or mount an arbitrary path. |
| Image identity and trust | Obtain the exact worker/app dependency closure from the authoritative seed. Every selected image is immutable and platform-compatible; mutable tags, local tag aliases, and daemon-cache presence alone are not identity evidence. Existing registry trust/admission policy remains in force. |
| Offline preparation | Pull, import, or locate every admitted digest before network isolation using the backend's artifact preparation path, on the same daemon Orborus will command. After isolation, verify all images by immutable identity and prove no registry request is required during one workflow run. Preparation success is distinct from workflow readiness. |
| Registry authentication and secrets | Registry credentials, entitlement, proxy credentials, and signed locations stay in LilRAE's secret boundary. They do not enter SDL, pack assets, process arguments, environment dumps, Docker errors, receipts, or evidence. This issue adds no pack credential or environment-variable schema. |
| Process and OS exposure | Treat socket possession as full host compromise capability. Constrain who can start or reconfigure Orborus, do not use privileged mode as a socket substitute, and account for container inspection, `/proc`, inherited environment, shell tracing, and crash dumps when handling existing Shuffle/TheHive fixture secrets. |
| Readiness and failure lifecycle | Bound daemon connection, image preparation, child startup, and workflow execution independently. A webhook `202`/execution id, running Orborus container, open API port, or created worker container is not success. Missing control/image prerequisites fail before workflow acceptance; an accepted execution must reach a terminal success or safe terminal failure, never remain `EXECUTING` indefinitely. |
| Persistence and idempotency | Image-cache state is replaceable backend state, not a persistent-volume contract. Application proof reads the created TheHive case through the declared service and ensures retry/reconciliation does not create duplicate cases. Existing Shuffle/OpenSearch and TheHive volumes retain their separate data ownership. |
| Errors, logs, and evidence | Pack validation continues to emit bounded, payload-free `ValidationResult` diagnostics and `PackDigestError` for identity failures. Runtime failures use LilRAE's stable error/correlation envelope; do not expose raw Docker exceptions, registry responses, credentials, full environment, image-config secrets, or host paths in portable evidence. Record value-free image identities and readiness observations. |

The extensibility seam is the existing provider-neutral orchestration authority:
an engine, an authorized child-workload set, lifecycle policy, and a reference
to one local control interface. LilRAE's backend adapter supplies endpoint and
image-preparation policy for Docker. A later worker version, additional Shuffle
app, rootless engine, containerd backend, or OCI archive source varies through
those seams rather than another Orborus special case. If acquisition itself
must become authored and portable, the seam advances upstream to the existing
RAES artifact-requirement model.

## Proof boundary

Pack tests can prove the exact structured control-interface join, explicit
root-equivalent classification, closed digest-qualified child image inventory,
absence of mutable tags, and successful RAES/pack/content-identity validation.
They cannot prove the host socket was mounted, the Docker daemon accepted an
operation, images exist in its store, registry egress is absent, or a live
Shuffle execution creates a TheHive case.

LilRAE integration proof must start from a clean admitted pack and an empty
relevant daemon cache, prepare the exact image closure, isolate registry
network access, and execute the seeded alert-to-case behavior to terminal
success with non-empty results and one read-back TheHive case. Negative proof
must cover missing/inaccessible/wrong socket, absent or digest-mismatched worker
and app images, unsupported image platform, denied registry credentials during
preparation, child timeout, restart/reconciliation, and lack of duplicate case
creation. Each case must terminate within its bound and leave a safe diagnostic
rather than a permanently executing record.

## Non-goals and rejected shortcuts

- Do not add another `/var/run/docker.sock` entry under `runtime.mounts`, a
  Compose volume, bootstrap shell command, or post-realization container patch.
- Do not expose Docker on TCP, use `privileged: true` as a substitute, mount the
  socket into worker/app containers, or weaken the host socket's owner/mode.
- Do not treat the Docker socket as a secret, ordinary persistent volume, or
  low-privilege dependency. It is an explicitly declared root-equivalent
  control authority.
- Do not use `latest`, pull on first workflow execution, accept a cached tag as
  digest proof, or discover the required app set by observing one successful
  live run.
- Do not package OCI image archives as ordinary TechVault `content`, create
  dummy RAES nodes to gain a `Source`, or claim that an SBOM/component row makes
  an image available.
- Do not duplicate RAES control-interface, orchestration, artifact,
  realization, workflow, readiness/evidence, diagnostic, or exception models.
- Do not change the existing Shuffle/OpenSearch trust and fixture-secret
  contract from issue #281, and do not redefine the seeded workflow's behavior
  as part of this infrastructure repair.
- Do not encode APTL/LilRAE container names, Compose paths, cache locations, or
  downstream workflow naming into the canonical pack terminology.

No new ADR is required. ADR 0009, ADR 0036, and the public ownership boundary
already place portable declarations in RAES/TechVault and host realization in
LilRAE. The remaining RAES spawn-template artifact-authority limitation is an
upstream contract gap, not authority for a local extension.
