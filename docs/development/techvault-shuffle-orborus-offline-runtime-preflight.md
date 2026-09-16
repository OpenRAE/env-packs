# TechVault Shuffle Orborus offline-runtime preflight

Issue [#285](https://github.com/OpenRAE/env-packs/issues/285) reports that
Orborus cannot reach its workload engine, Shuffle executions remain
`EXECUTING`, and the seeded automation never creates a TheHive case. The issue
was reopened after the released pack lost the RAES runtime-control declaration
that a backend needs in order to admit and realize that workload surface.

This note distinguishes the portable requirement from one backend's mechanism.
Runtime realization remains tracked in
[Brad-Edwards/aptl#974](https://github.com/Brad-Edwards/aptl/issues/974).

## Ownership decision

RAES owns the meaning of the SDL fields used here. This repository consumes
those existing semantics and authors the first-party TechVault content. It does
not extend RAES or change `OpenRAE/rae`.

The TechVault pack owns declarations of what the scenario requires:

- an in-world read-write Unix control endpoint at `/var/run/docker.sock`;
- the fact that holding that endpoint carries `host_root_equivalent`
  orchestration authority;
- the exact worker and seeded HTTP app workload identities Orborus is
  authorized to create; and
- the scenario-visible execution lifetime and cleanup behavior.

LilRAE owns how those declarations are realized:

- selection, admission, mounting, ownership, and permissions of a host-side
  engine endpoint;
- native holder identity and realization-only bootstrap values;
- operator policy for granting the declared authority;
- offline acquisition and loading of the exact images, including any
  product-required tag aliases;
- realization of delegated worker authority;
- observed child-workload records and runtime evidence; and
- end-to-end proof that the workflow terminates and creates the TheHive case.

The portable declaration grants no permission by itself. RAES describes the
required authority; a backend separately decides whether it can admit and
safely realize it.

## Portable Orborus contract

The TechVault SDL declares one RAES `local_control_interfaces` member on
`shuffle-orborus`:

- id `docker-sock`;
- path `/var/run/docker.sock`;
- kind `unix_socket`; and
- access `read_write`.

It deliberately omits `bind_source`, protocol overrides, mounts, node source,
container settings, product environment injection, and engine API details.
Those would select or describe a realization mechanism.

One RAES `orchestration_authorities` member references that same-node
interface, identifies the Docker workload family, classifies the authority as
`host_root_equivalent`, and closes the authorized scenario workload inventory
to these recovered immutable references:

| Purpose | Exact image reference |
| --- | --- |
| Workflow worker | `ghcr.io/shuffle/shuffle-worker@sha256:fd0d420a5e0cd41f3979335e51912e8dd423e7ce540d1dfa24efdc98fb6071bd` |
| Seeded HTTP 1.4.0 app | `frikky/shuffle:http_1.4.0@sha256:0f6f6a686205cdb1f589feb39b3ed7fb8ae715406ae4a626b2e7657e2551e00c` |

The HTTP reference retains the product-native tag used by the seeded workflow
while the digest supplies immutable identity. Creating any required local alias
or loading the image into an offline engine remains backend work.

The authority omits `realized_children`. That collection is observed runtime
state and cannot be predicted by an authored pack. RAES 5.0.0's compiler keeps
the interface, authority, lifecycle, and spawn templates as configuration
requirements while excluding observed children from authored desired state.

## Validation boundary

The TechVault validator permits these two runtime fields only on
`shuffle-orborus`, then validates their complete pack-owned shape. The global
realization-method guard still rejects the same fields on every other node.
The Orborus validator also rejects host bind sources, engine API selection,
predicted children, mutable or mismatched workloads, broken interface joins,
and privilege or lifecycle drift.

Repository checks can prove that the portable requirement is exact,
internally consistent, RAES-valid, and free of backend launch instructions.
They cannot prove that a host endpoint was mounted, permission was granted,
images were loaded, a worker launched, the workflow terminated, or a TheHive
case was created. Those require downstream admission and live evidence.

## Security and reliability guardrails

- Read-write Docker control is host-root-equivalent authority, not an ordinary
  file mount. A backend must admit it explicitly and fail closed before side
  effects when it cannot realize the contract.
- Image identity and offline availability are separate claims. A digest names
  an artifact; only backend preparation proves it is locally executable.
- No credential is added by this issue. Diagnostics and evidence must not dump
  Shuffle or TheHive secrets, full environment maps, or raw engine responses.
- A webhook response or execution id is not completion evidence. Acceptance
  requires terminal execution and the correlated TheHive case downstream.

## Non-goals

- No RAES model, schema, vocabulary, or semantic extension.
- No host path selection, Compose fragment, mount recipe, container name,
  runtime label, engine policy, or image preload implementation.
- No product environment-variable contract or native self-identity binding.
- No predicted child workloads or live workflow assertion.
- No version or changelog edit; Release Please owns both.

No new ADR is required. Existing RAES semantics and the repository ownership
boundary already provide the required declaration/realization split.
