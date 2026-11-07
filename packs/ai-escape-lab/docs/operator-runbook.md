# Shifter GCP operator runbook

Use this how-to guide to prepare a twelve-seat event from one exact image.
Obtain the tenant's deployment approval before you run cloud commands or import content.
The pack remains `draft` until the [readiness checks](golden-readiness-checklist.md) have live evidence.
Static repository checks do not authorize deployment or qualify an event.

## 1. Build one immutable image

Work from `packs/ai-escape-lab/` for the relative commands below.
Select an exact Ubuntu 24.04 image name, a dedicated image-build VPC and subnet, and an IAP-reachable zone.
Select the tenant's image-builder service account.
The build VM needs outbound access to resolve pinned container manifests and package dependencies.
The resulting range image needs no public registry at runtime.

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

Replace the uppercase arguments with the selected project, zone, network, subnet, exact Ubuntu image, and service account.
The `20261006-1` argument is an example image-version label.
Packer uses IAP and an internal address.
For that label, it creates `shifter-ai-escape-lab-v20261006-1` in the selected project.
It stages the pinned archive, pins container bases, builds service images, starts the stack, and runs the bake probe.
It removes mutable lab volumes and records local image IDs in `/opt/ai-escape-lab/image-manifest.json`.

The bake downloads Claude Code 2.1.289 from the exact URL in `build/gcp/claude-code.lock.json`.
It verifies SHA-512 integrity and copies the standalone Linux binary into `eval-sandbox`.
The image needs no runtime artifact delivery or custom Shifter adapter.
Record the exact image reference from Packer.
Do not map an image family into Shifter.

The [2026-10-06 qualification record](golden-image-qualification-2026-10-06.md) identifies the accepted historical image.
That record applies only to its exact image and functional input hashes.
Use its exact reference for the deployment canary when you select that accepted build.
Later source edits do not change or requalify the accepted image.

## 2. Register the Shifter image mapping

Create a GCE RAES image mapping with these values:

| Field | Value |
| --- | --- |
| Source name | `ai-escape-lab/gce` |
| Source version | blank |
| Image reference | exact `shifter-ai-escape-lab-v…` image |
| Bootstrap capability | `standard` |
| Machine type | `e2-standard-4` initially |
| Boot disk | 50 GB `pd-balanced` |
| Management SSH | Ubuntu default account on port 22 |

The SDL declares the `participant` account and SSH access.
The image's SSH `ForceCommand` sends that account into `eval-sandbox`.
It provides no direct host shell or Docker access.

Use the broker-free GCP range profile for direct Vertex scenarios.
Attach a range-host service account with only `aiplatform.endpoints.predict` and the tenant's ordinary telemetry-write permissions.
The container reaches only a scoped host metadata responder and the Private Google Access VIP.
The host firewall rejects direct metadata access and other forwarding from the model adapter subnet.
The image contains no baked key and writes no key to disk.

The image defaults to region `us-east5`, with `claude-sonnet-4-6` and `claude-haiku-4-5`.
Override `AI_ESCAPE_MODEL_REGION` only after you enable both models and probe the same path in the replacement region.

A participant with root in `eval-sandbox` can copy the short-lived OAuth bearer token from Claude Code.
That token can permit off-seat prediction until expiry.
Destroying a seat prevents new minting but does not revoke an existing token.
Before the event, verify the exact prediction and telemetry permissions.
Set project-level model quotas and budget alerts to bound exposure.

Use the tenant's qualified optional gateway if the event requires immediate revocation or per-seat spend and rate enforcement.
This pack implements no credential adapter.
Retain the event's decision about the direct-path replay window.

## 3. Register the scenario and CTFd content

The supplied exporter targets the historical Shifter profile with `raes==3.5.0` and `raes-env-packs==5.2.0`.
This is a deployment projection, not the canonical pack's current RAES interface.
Confirm the receiving deployment's contract before selecting this route.
Use the matching pinned environment described in the [upload guide](../build/shifter/README.md).

```sh
python build/shifter/export-pack.py \
  --pack-root . \
  --output /secure/operator-path/ai-escape-lab-0.1.0-shifter.tar.gz
```

Register the archive through the deployment's ordinary RAES pack ingestion path.
The example output filename does not select or change a pack version.
Generate the private CTFd import file on an operator workstation:

```sh
python3 ctfd/export_shifter_challenge_pack.py \
  --output /secure/operator-path/ai-escape-lab-ctfd.json
```

Import the JSON through Shifter's CTFd challenge-pack control.
It contains seven static flags and twenty-three progressive portal hints.
Keep the file out of source control.
Delete the operator copy after you verify the import.

## 4. One-seat canary

Launch one disposable range and wait for Shifter to report participant access ready.
Run these commands through the management channel:

```sh
sudo /opt/ai-escape-lab/readiness.sh --runtime
sudo /opt/ai-escape-lab/probe-agent.sh
```

Open the participant browser terminal.
Verify that it displays the briefing from `/app`.
Run `claude` and verify startup without permission prompts.
Ask Claude to show the lab briefing.
Verify that it displays the participant instructions.

Check that the participant has no host shell, Docker socket, or local shell-hint command or file.
Complete the [operator walkthrough](walkthroughs/operator-solution.md) from that terminal.
Submit every flag to CTFd.

Before accepting the image, verify these results:

- Requests to `169.254.169.254` from `eval-sandbox` fail.
- The metadata responder rejects paths outside its identity allowlist.
- The range account has no storage, secret, administration, or other project permission.
- Arbitrary public DNS and HTTPS fail.
- `us-east5-aiplatform.googleapis.com` resolves to `199.36.153.8` and a real Claude response succeeds.
- No route reaches another range or its management plane.

Copy a canary token through the approved operator procedure.
Verify that it permits only allowed model prediction.
Record its expiry and verify failure after expiry.
Accept the measured replay window for the event, or qualify the optional gateway before proceeding.
Keep tokens out of retained evidence.

## 5. Twelve-seat rehearsal

Prepare twelve ranges from the same exact image.
Claim all twelve seats and open their browser terminals.
Start one bounded `claude -p` probe per seat.
Run the bake readiness command on every host.
Record boot-to-terminal and boot-to-agent-ready times, peak CPU/memory/disk use, model errors, and container restarts.

From at least two seats, probe the other eleven range addresses.
Every probe must fail.
Submit one early flag from each seat to prove its CTFd association.
Complete all seven flags on at least one seat.

## 6. Reset

Destroy the used range and create a replacement from the same exact image.
Do not use `docker compose restart` as an attendee reset; it can retain modified writable layers.
Verify a fresh `hf-repos` volume, no previous shell history, no prior CTF state, and a new range identity.
Record the time from reset request to usable browser terminal.
