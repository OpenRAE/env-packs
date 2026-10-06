# Shifter GCP operator runbook

This is the shortest supported route from the pack to a twelve-seat event. The
pack remains `draft` until the live evidence in the readiness checklist exists.

## 1. Build one immutable image

Select an exact Ubuntu 24.04 image name, the tenant's dedicated image-build VPC
and subnet, an IAP-reachable build zone, and the tenant image-builder service
account. The build VM needs outbound access during the bake because it resolves
the pinned container manifests and package dependencies. The resulting range
image needs no public registry at runtime.

```sh
build/gcp/build-image.sh \
  PROJECT_ID \
  ZONE \
  IMAGE_BUILD_NETWORK \
  IMAGE_BUILD_SUBNETWORK \
  projects/ubuntu-os-cloud/global/images/EXACT_UBUNTU_IMAGE \
  20261006-1 \
  IMAGE_BUILDER_SERVICE_ACCOUNT
```

Packer uses IAP and an internal address. It creates
`shifter-ai-escape-lab-v20261006-1` in the selected project, stages the pinned
upstream archive, pins every upstream container base, builds all service images,
starts the full stack, runs the bake readiness probe, removes mutable lab
volumes, and captures the resulting local image IDs in
`/opt/ai-escape-lab/image-manifest.json`.

The bake also downloads Claude Code 2.1.289 from the exact registry URL in
`build/gcp/claude-code.lock.json`, verifies its pinned SHA-512 integrity, and
copies the standalone Linux binary into the `eval-sandbox` image. No runtime
artifact delivery or custom Shifter adapter is required.

Do not map an image family into Shifter. Record the exact custom-image reference
returned by Packer.

The image accepted by the isolated 2026-10-06 qualification is recorded in
[`golden-image-qualification-2026-10-06.md`](golden-image-qualification-2026-10-06.md).
Use that exact reference for the deployment canary.

## 2. Register the Shifter image mapping

Create one GCE RAES image mapping with these values:

| Field | Value |
| --- | --- |
| Source name | `ai-escape-lab/gce` |
| Source version | blank |
| Image reference | exact `shifter-ai-escape-lab-v…` image |
| Bootstrap capability | `standard` |
| Machine type | `e2-standard-4` initially |
| Boot disk | 50 GB `pd-balanced` |
| Management SSH | Ubuntu default account on port 22 |

The SDL supplies the participant account (`participant`) and SSH access. The
image's SSH `ForceCommand` sends that account into `eval-sandbox`; it cannot use
the host shell or Docker directly.

Use the broker-free GCP range profile already used for direct Vertex scenarios.
It must attach a range-host service account whose only workload permission is
`aiplatform.endpoints.predict` (plus the tenant's ordinary telemetry writes). The
container reaches only a scoped host metadata responder and the Private Google
Access VIP; the host firewall rejects its direct metadata route and all other
forwarding from the model adapter subnet. No key is baked or written to disk.
The image defaults Claude Code to the tenant's existing `us-east5`
`claude-sonnet-4-6` and `claude-haiku-4-5` configuration. Override
`AI_ESCAPE_MODEL_REGION` only if both models are enabled in the replacement
region and the same path has been probed there.

This is Shifter's default keyless-direct trust model. A participant with root in
`eval-sandbox` can read and copy the short-lived OAuth token returned to Claude
Code, and that bearer token can be replayed away from the seat until it expires.
Destroying a seat prevents new minting but does not revoke a token already
minted. Before the event, verify the service account has no project role beyond
the exact prediction/telemetry permissions and set project-level model quotas
and budget alerts to bound the exposure. If the event requires immediate token
revocation or per-seat spend/rate enforcement, use Shifter's qualified optional
model gateway; this pack does not implement its own credential adapter.

## 3. Register the scenario and CTFd content

The current deployed Shifter contract is RAES 3.5. Build its deterministic
upload archive with the pinned Shifter environment, then register that archive
through the ordinary RAES pack ingestion path:

```sh
python build/shifter/export-pack.py \
  --pack-root . \
  --output /secure/operator-path/ai-escape-lab-0.1.0-shifter.tar.gz
```

Generate the private CTFd import file on an operator workstation:

```sh
python3 ctfd/export_shifter_challenge_pack.py \
  --output /secure/operator-path/ai-escape-lab-ctfd.json
```

Import that JSON through Shifter's CTFd challenge-pack control. It contains all
seven static flags and twelve free hints. Keep the generated file out of source
control and delete the operator copy after the import is verified.

## 4. One-seat canary

Launch one disposable range and wait for Shifter to report participant access
ready. From the management channel run:

```sh
sudo /opt/ai-escape-lab/readiness.sh --runtime
sudo /opt/ai-escape-lab/probe-agent.sh
```

Open the participant browser terminal. It must display the upstream briefing
from `/app`, `hint 1` must return one line, `claude` must start, and the
participant must have no host shell or Docker socket. Complete the operator
walkthrough from that terminal and submit every flag to CTFd.

Before accepting the image, also prove:

- `curl` to `169.254.169.254` from `eval-sandbox` fails;
- the scoped metadata responder refuses any path outside its identity allowlist;
- the range service account has no storage, secret, administration, or other
  project permissions;
- arbitrary public DNS and HTTPS fail;
- `us-east5-aiplatform.googleapis.com` resolves to `199.36.153.8` and a real
  Claude response succeeds;
- no route reaches another range or its management plane.

Also copy a canary token, confirm it cannot perform anything except allowed
model prediction, record its expiry, and verify it fails after expiry. Record
the direct-path replay window as an accepted event risk, or switch the tenant to
its qualified optional gateway before proceeding.

## 5. Twelve-seat rehearsal

Prepare twelve ranges from the same exact image. Claim all twelve, open all
twelve browser terminals, start one bounded `claude -p` probe per seat, and run
the bake readiness command on every host. Record boot-to-terminal and
boot-to-agent-ready times, peak CPU/memory/disk use, model errors, and any
container restart.

Perform explicit cross-seat probes from at least two seats against the other
eleven range addresses. Every probe must fail. Submit one early flag from each
seat to prove its CTFd association. Complete all seven flags on at least one
seat.

## 6. Reset

Reset means replacement: destroy the used range and create a new range from the
same exact image. Do not use `docker compose restart` as an attendee reset; it
can retain a modified writable layer. Verify the replacement has a fresh
`hf-repos` volume, no previous shell history, no prior CTF state, and a new
range identity. Record the time from reset request to usable browser terminal.
