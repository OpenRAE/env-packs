# Golden readiness checklist

Use this operator how-to guide to collect release evidence for one exact image.
Copy the checklist into that evidence and leave this source copy unchecked.
The [dated qualification record](golden-image-qualification-2026-10-06.md) covers its historical image only.
It does not complete the current deployment checks.

## Golden Definition Of Done

- [ ] Record the exact Ubuntu source image and successful IAP build on the dedicated image-build network.
- [ ] Retain all eleven local container image IDs in the image manifest.
- [ ] Verify upstream revision `fcb25ec9874b0676706b9aca650f22efc90f711e` and the pinned Claude Code package identity in that manifest.
- [ ] Map `ai-escape-lab/gce` to the exact custom-image reference in Shifter.
- [ ] Verify the baked Claude Code 2.1.289 binary with `claude --version` without a runtime download.
- [ ] Import seven challenges, seven distinct flags, and twenty-three progressive portal hints into CTFd.
- [ ] Pass `/opt/ai-escape-lab/readiness.sh --runtime` on the one-seat canary.
- [ ] Verify that browser SSH opens `/app` inside `eval-sandbox`.
- [ ] Verify the absence of a host shell, Docker socket, privileged container, host namespace, and direct metadata route.
- [ ] Obtain a real `claude -p` response through the intended Vertex identity and Private Google Access path.
- [ ] Verify only the exact prediction/telemetry permissions on the range identity.
- [ ] Verify the absence of storage, secret, administration, and other project roles.
- [ ] Set project-level model quotas and budget alerts for the twelve-seat direct-access exposure.
- [ ] Measure and accept the direct-path token replay window and expiry, or qualify the tenant's optional gateway.
- [ ] Verify that arbitrary Internet, tenant control-plane, and other-seat probes fail.
- [ ] Verify terminal and agent readiness for twelve simultaneous seats within the event target.
- [ ] Retain twelve-seat CPU, memory, disk, container-health, and model-call evidence.
- [ ] Measure destroy/recreate reset and accept its duration for the event.
- [ ] Verify that reset produces a clean seat.
- [ ] Record the pack digest, image reference, image manifest, CTFd import digest, and rehearsal date.

## Final Manual Participant Walkthrough Protocol

- [ ] Claim a fresh seat through the event's participant flow.
- [ ] Open only the browser terminal and verify `/app` inside `eval-sandbox`.
- [ ] Start `claude` from the login shell without permission prompts.
- [ ] Ask Claude to show the lab briefing and verify the returned participant instructions.
- [ ] Verify a real model response.
- [ ] Direct the agent through each escape while you review and execute its proposed commands.
- [ ] Recover and submit flags 1 through 7 in order.
- [ ] Verify that each CTFd challenge accepts exactly its intended flag.
- [ ] Verify the absence of range-host shell and Docker socket access.
- [ ] Verify the absence of unscoped cloud metadata, tenant control-plane, and other-seat access.
- [ ] Verify only direct-path project identity and token resources at the scoped metadata endpoint.
- [ ] Retain the token-expiry and replay-risk decision without retaining the token.
- [ ] Destroy the used range and claim its replacement.
- [ ] Verify that no prior shell history, files, volumes, or solved state remain.
- [ ] Retain sanitized walkthrough results, timings, exact image reference, and pack/CTFd digests.

Use the [runbook](operator-runbook.md) for build, canary, rehearsal, and reset steps.
Use the [private proof procedure](walkthroughs/operator-solution.md) for the seven-stage walkthrough.
