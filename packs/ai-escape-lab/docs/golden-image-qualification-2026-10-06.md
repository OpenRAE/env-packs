# Golden image qualification — 2026-10-06

This record covers an isolated one-seat image build and participant-path
qualification. It did not install the pack, change a Shifter tenant, import the
CTFd challenges, or launch a range through Shifter.

## Accepted image

| Field | Value |
| --- | --- |
| Exact reference | `projects/prod-lk3ssb/global/images/shifter-ai-escape-lab-v20261006-4` |
| GCE image ID | `2764881020823601269` |
| Status | `READY` |
| Created | `2026-10-06T02:25:46.342-07:00` |
| Size | 50 GB |
| Source image | `projects/ubuntu-os-cloud/global/images/ubuntu-2404-noble-amd64-v20260918` |
| Build zone | `us-central1-a` |
| Build network and subnet | `shifter-orthanc-image-build` |
| Packer | 1.11.2, internal-address IAP build |

The image was built from the vendored upstream revision
`fcb25ec9874b0676706b9aca650f22efc90f711e`. The environment-pack checkout was
based on `56da2a3083950674a0d6bcda6ead6cc585de6b5a`; the issue 426 changes were
uncommitted when the image was baked. Delivery commit
`420dea5058dc03571a8020ce1a3f8903ee3bd20b` contains matching functional input
bytes. The complete hashes below bind those bytes to the accepted image. The
absence of a contemporaneous bake-time commit is an accepted provenance gap for
this event build.

| Functional input | SHA-256 |
| --- | --- |
| Upstream archive | `138c611ec9520d99723389133e4e989ef5b2c536cae0ccb41f8f0e422c4a16a2` |
| Packer template | `46874e093390bc8303950961b24d2a8934e0edb7fcdb55b133686de7837e5c3a` |
| Base-image lock | `a3de827c3f65e759bd05a3fa86a2fc3733e9b6ed67e3ab9f4753ff35448df064` |
| Build entry point | `2d93e1bd08d2fce18748c3d29a5dfa39ba3456f029b34d7c977f095ec456223e` |
| Build-image override | `130fac49a29ffa575fcf9f6559e6abb396ed6a45114f5599754b93ca2cda0af0` |
| Claude Code lock | `2be64f5f6b3faac4c707d03324beb36d4107e30d7c3391fcd2571cc518c4a16a` |
| Installer | `e7be4d062d2e53414afee3171279871caf9bc6c16854062afa5de34a017d065e` |
| Firewall | `e2375f7f6536052147db0243859d3ea9b89eabc639b0a0088ab845c9eb81974f` |
| Metadata responder | `e4d932d6b7e208905d1ed5cd9d40a7ef538be70fe3cd754eeea41954dddd0a78` |
| Source preparation | `1dd0ebd18e756c2a5b538c8d3871f79a400ed74e3c800ab0451453c4f2c942f8` |
| Participant entry helper | `3c9bdd650b185d4f871c8f0abd7729f31f9f12b1ebb5e881548a9702625b3ae1` |
| Runtime Compose file | `20aa69996337c38dc1ae19df56cfd2d7c7be2443f5f24c088167eb7d28b2c425` |
| Participant briefing | `c6a5cee2ea059890c02e936fa5eb83938bc4a21ce116f9f8e37761a533573958` |
| Participant shell | `f8c0fb010a873c7e1709a58c1cab9b58a72674a4d8153f34b230847dbc23e97d` |
| Agent probe | `398fe66c68f8175f4bed973b9335c12eb4a9bff5cdf9459020d228cf449803da` |
| Readiness contract | `f2307b60a0ef4d8d7e5caccc5fbacb722ef0b612edec937c975eb3d96d411167` |
| Readiness script | `9e572c4c395806dc9076236f86dee96f9394f5aec968c8c51a03395e65cc88aa` |
| Runtime start script | `cd830d39201ed6f008f657d4b32f5b3395b911039b426e2e230db8162d73f154` |
| Runtime stop script | `1821e7b8edb7fddea938b9b69c877d8b0d19b1689c1cad4d80c1ea6e66f9ee4b` |

The bake resolved Packer's Google Compute plugin to 1.2.1. Host packages
included Docker 29.1.3, Compose 2.40.3, containerd 2.2.1, and runc 1.3.4. The
container bases were the exact `python:3.11-slim`, `debian:bookworm-slim`, and
MongoDB digests in `base-images.lock.yaml`; Claude Code was 2.1.289. The baked
`/opt/ai-escape-lab/image-manifest.json` had SHA-256
`9f4d954afb5affc8073d7d2b53f1cdfc5781ba5e7fa6c8da1c905e896c4008e2`
and recorded all eleven local image IDs.

The build did not retain a complete apt/pip dependency SBOM. Observed Python
packages included FastAPI 0.142.2, Uvicorn 0.54.0, h5py 3.16.0, NumPy 2.4.6,
PyMongo 4.18.2, and cryptography 50.0.2. Unpinned package resolution remains a
rebuild reproducibility gap; deployment must use the exact accepted image.

## Fresh-instance qualification

The final QA VM `ai-escape-lab-final-qa-20261006-4`, GCE instance ID
`6954761273228197911`, was created directly from the exact accepted image as an
`e2-standard-4` with a 50 GB `pd-balanced` disk. It had no external address and
used the dedicated image-build VPC. Cloud-init completed in 33.86 seconds after
guest boot. The QA VM and its disk were deleted after the run.

The range-host service account had only these project roles:

- the custom model role containing only `aiplatform.endpoints.predict`;
- `roles/logging.logWriter`; and
- `roles/monitoring.metricWriter`.

All five required host services were active. Runtime readiness and a live
Claude Code request both passed. The observed client was Claude Code 2.1.289,
and the response came from `claude-sonnet-4-6` through Vertex.

An ephemeral `participant` account and key exercised the image's exact SSH
`ForceCommand`. The terminal opened in `/app` as root inside `eval-sandbox`.
It had no Docker client or socket and no range-host shell. The participant
checks produced these bounded results:

| Check | Result |
| --- | --- |
| Internal challenge service discovery | Pass |
| Raw GCE metadata route | Blocked |
| Unapproved metadata token scope | HTTP 404 |
| Arbitrary public DNS | Blocked |
| Arbitrary public HTTPS | Blocked |
| Vertex hostname | Pinned to `199.36.153.8` |
| Hint command | Pass |
| Live Sonnet 4.6 request | Pass |

From that participant terminal, Claude Code read the human-facing authorized
CTF briefing and ran the known happy path. All seven stages matched their
expected private hashes and the campaign passed. No flag or credential values
were retained in this record. After the campaign, all eleven containers were
running, every container with a health check was healthy, host memory use was
1.2 GiB of 15 GiB, and the root disk was 17 percent used.

Three superseded candidate images were deleted after the accepted run. No
Packer or QA VM remains. The accepted v4 image is the only image left in the
`shifter-ai-escape-lab` family.

The superseded images were `shifter-ai-escape-lab-v20261006-1` through `-3`.
Their disposable QA instance IDs were not retained before deletion; those runs
served only to find and fix candidate defects and do not support acceptance.
This is an evidence-retention gap for the discarded candidates, not for the
final v4 QA identity above.

## Deployment handoff

Map the exact image reference above; do not map the family. Shifter pack
registration, CTFd import and acceptance, Shifter browser-session authorization,
and event reset/rehearsal remain deployment checks for the tenant operator.
The isolated qualification establishes the image-side participant shell,
containment, model path, and complete seven-stage campaign.
