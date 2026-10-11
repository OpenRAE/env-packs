# Golden readiness checklist

Copy this checklist into the release evidence for a specific immutable image.
Keep the source copy unchecked.

## Golden Definition Of Done

- [ ] Packer used an exact Ubuntu source image and completed through IAP on the dedicated image-build network.
- [ ] The image manifest records all eleven local container image IDs, upstream revision `fcb25ec9874b0676706b9aca650f22efc90f711e`, and the pinned Claude Code package identity.
- [ ] A Shifter mapping resolves `ai-escape-lab/gce` to the exact custom-image reference.
- [ ] `eval-sandbox` contains the baked Claude Code 2.1.289 binary and `claude --version` succeeds without a runtime download.
- [ ] CTFd imports seven challenges, seven distinct flags, and twenty-three progressive portal hints.
- [ ] One-seat canary passes `/opt/ai-escape-lab/readiness.sh --runtime`.
- [ ] Browser SSH lands the participant in `/app` inside `eval-sandbox`.
- [ ] The participant has no host shell, Docker socket, privileged container, host namespace, or direct metadata route.
- [ ] A real `claude -p` response succeeds through the intended Vertex identity and Private Google Access path.
- [ ] The range identity has only the exact prediction/telemetry permissions and no storage, secret, administration, or other project role.
- [ ] Project-level model quotas and budget alerts bound the twelve-seat direct-access exposure.
- [ ] The direct-path bearer-token replay window and expiry were measured and accepted for this event, or the tenant's optional gateway was qualified instead.
- [ ] Arbitrary Internet, tenant control-plane, and other-seat probes fail.
- [ ] Twelve simultaneous seats reach terminal and agent readiness within the event target.
- [ ] Twelve-seat CPU, memory, disk, container health, and model-call evidence is retained.
- [ ] Destroy/recreate reset produces a clean seat and its measured reset time is acceptable.
- [ ] Operator evidence records the pack digest, image reference, image manifest, CTFd import digest, and rehearsal date.

## Final Manual Participant Walkthrough Protocol

- [ ] Claim a fresh seat through the same CTF participant flow used at the event.
- [ ] Open only the browser terminal and confirm it lands in `/app` inside `eval-sandbox`.
- [ ] Start `claude` and verify the agent returns a real model response.
- [ ] Direct the agent through each escape while manually reviewing and executing its proposed commands.
- [ ] Recover and submit flags 1 through 7 in order; verify each CTFd challenge accepts exactly its intended flag.
- [ ] Confirm the participant never obtains the range-host shell, Docker socket, unscoped cloud metadata service, tenant control plane, or another seat.
- [ ] Confirm the scoped model metadata endpoint exposes only the direct-path project identity and token resources, and retain the token-expiry/replay risk decision.
- [ ] Destroy the used range, claim its replacement, and verify that no prior shell history, files, volumes, or solved state remain.
- [ ] Retain the sanitized walkthrough result, timings, immutable image reference, and pack/CTFd digests as release evidence.
