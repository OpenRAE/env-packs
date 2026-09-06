# TechVault Shuffle Orborus pack-content preflight

Issue [#285](https://github.com/OpenRAE/env-packs/issues/285) was reported
from a failed APTL deployment, but the failure crosses two ownership layers.
This note limits the env-pack change to portable, in-world content and content
configuration. Runtime realization is tracked separately in
[Brad-Edwards/aptl#974](https://github.com/Brad-Edwards/aptl/issues/974).

## Ownership decision

RAES owns the meaning of the SDL fields used here. This repository consumes
those existing semantics and authors the first-party TechVault content. It does
not extend RAES or change `OpenRAE/rae`.

The TechVault pack owns:

- the effective Orborus application configuration;
- immutable identities for the worker and seeded HTTP app images that comprise
  this scenario's runtime image inventory;
- the in-world Docker control endpoint that Orborus expects at
  `/var/run/docker.sock`;
- the statement that the holder of that read-write endpoint has
  `host_root_equivalent` orchestration authority; and
- static regression tests that keep these content declarations consistent.

APTL owns:

- selection, admission, mounting, ownership, and permissions of a host-side
  Docker endpoint;
- operator policy for granting that endpoint;
- offline acquisition and loading of the exact images, including any
  product-required tag aliases;
- realization of Docker authority for spawned workers;
- observed child-workload records, correlation, and runtime evidence; and
- end-to-end proof that the workflow completes and creates the TheHive case.

The pack therefore must not author a host `bind_source`, container-engine
installation details, Compose fragments, APTL labels, or predicted
`realized_children`. Those are facts or choices of one runtime realization.

## Existing content and pack-owned gaps

TechVault already declares a pinned Orborus node, an in-world read-write Unix
socket at `/var/run/docker.sock`, and an orchestration authority that references
that control interface. The authority is correctly classified using RAES's
existing `host_root_equivalent` vocabulary.

The current content is incomplete in three pack-owned ways:

1. the worker template uses a mutable `latest` tag;
2. the seeded HTTP 1.4.0 app is absent from the authorized runtime image
   inventory; and
3. Orborus's effective environment is not declared, so its backend URL,
   worker selection, app-image namespace, offline behavior, and timeouts are
   implicit.

The recovered immutable inventory is:

| Purpose | Exact image reference |
| --- | --- |
| Workflow worker | `ghcr.io/shuffle/shuffle-worker@sha256:fd0d420a5e0cd41f3979335e51912e8dd423e7ce540d1dfa24efdc98fb6071bd` |
| Seeded HTTP 1.4.0 app | `frikky/shuffle:http_1.4.0@sha256:0f6f6a686205cdb1f589feb39b3ed7fb8ae715406ae4a626b2e7657e2551e00c` |

Both references retain exact digest identity. The HTTP reference also retains
the product-native tag used by the seeded workflow; materializing that alias in
an offline engine is APTL's responsibility.

## Implementation guardrails

The SDL change will:

- replace the mutable worker reference and add the exact HTTP app template;
- declare the required plain Orborus environment values, including
  `SHUFFLE_WORKER_IMAGE`, `SHUFFLE_BASE_IMAGE_NAME`,
  `SHUFFLE_AUTO_IMAGE_DOWNLOAD`, and the lifecycle timeout values;
- make environment values agree with the typed worker template, application
  namespace, and lifecycle policy;
- retain the in-world control-interface path, access mode, reference, and
  privilege classification while removing the host-side `bind_source`; and
- omit observed children because a pack cannot predict runtime observations.

Regression tests will parse the SDL and assert these relationships. Existing
RAES parsing, `validate_pack()`, the TechVault content validator, and
`validate_pack_content_manifest()` remain the validation authorities; no local
SDL schema or new semantic layer is introduced. After editing the SDL, the
associated-artifact binding is refreshed with the repository's canonical
`tools/refresh_pack_sdl_binding.py` helper.

## Proof boundary

Repository tests can prove that the portable content is exact, internally
consistent, RAES-valid, and free of backend realization fields. They cannot
prove that a host socket was mounted, an operator grant was admitted, images
were loaded into a particular daemon, a worker received delegated control, or
the live Shuffle-to-TheHive workflow completed. Those runtime proofs belong to
APTL #974.

No RAES expressivity change is part of this work. If implementation discovers
that the intended portable content cannot be represented by the currently
pinned RAES models without changing their meaning, work stops for maintainer
consultation rather than adding a local extension or changing `OpenRAE/rae`.

## Non-goals

- No changes to RAES models, validators, or vocabulary.
- No APTL implementation in this repository.
- No host security policy, socket-permission policy, or backend admission
  policy.
- No runtime image pull/load implementation or live workflow assertion.
- No version or changelog edit; Release Please owns both.
