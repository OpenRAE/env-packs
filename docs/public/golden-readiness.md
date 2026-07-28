# Golden Readiness

Golden readiness is a participant-equivalent claim. A golden pack must be
playable and provable from the intended participant role, not merely observable
from Terraform, SSM, cloud console, root, SYSTEM, or a test harness shortcut.

## Network Isolation

Live golden builds and rehearsals stand up real cloud infrastructure. That
infrastructure MUST be isolated from any shared or long-lived environment so a
range can never disrupt another workload.

- Deploy each range into a **dedicated VPC and subnet**. Never build or test in
  the account's **default VPC** — it is shared with other long-lived
  infrastructure (for example, CI runners), and range resources can interfere
  with it.
- Never set `private_dns_enabled = true` on an interface VPC endpoint in a VPC
  shared with anything else. Private DNS overrides the service hostname for the
  **entire VPC**, so a range's `ssm` / `sts` / `ec2` (etc.) endpoint hijacks
  that AWS API for every other host in the VPC and black-holes their traffic.
  Range service endpoints belong only in the range's own VPC.
- If isolation cannot be guaranteed in the default region, **build and test in a
  separate region** whose default VPC is empty of shared infrastructure.

These are not optional. A full-build range that created private-DNS `ssm`
interface endpoints in a shared default VPC once silently wedged unrelated CI for
over an hour, until the range was torn down.

## Milestone Structure

Structure new scenario milestones so the final proof is planned:

- [ ] Scenario contract and pack skeleton.
- [ ] Topology, assets, and reference-triangle design.
- [ ] Attacker behavior is specified in RAES participant semantics.
- [ ] Flag, challenge, and reference CTFd layer, when the scenario has flags.
- [ ] Delivery profile bundles, when the scenario has multiple audiences.
- [ ] Golden build implementation in the declared live infrastructure.
- [ ] Automated live rehearsal for the golden build.
- [ ] Final manual participant walkthrough.
- [ ] Final docs, status, evidence, and teardown reconciliation.

The final manual participant walkthrough is its own slice. It is not implied by
passing tests or a successful Terraform apply.

## Definition Of Done

Every pack carries this checklist at
`environments/<name>/docs/golden-readiness-checklist.md`.

- [ ] The range applies from a clean checkout using committed pack content.
- [ ] No hidden repo-root `.env`, external file fetch, or undocumented manual
      setup is required, except approved cloud/operator credentials.
- [ ] The declared golden build profile creates the participant start state.
- [ ] The participant entry surface exists, is documented, and is reachable.
- [ ] The full happy path is executed manually from the participant surface,
      command by command.
- [ ] Operator channels such as SSM, Terraform, cloud consoles, generated
      passwords, root/SYSTEM shells, and database consoles are used only for
      provisioning, diagnostics, reset, observation, or teardown.
- [ ] Every required RAES objective, flag, and success condition is reached
      from the intended participant privilege context.
- [ ] Negative gates prove objectives/flags are not trivially reachable before
      the required action or privilege.
- [ ] Reset, persistence, survival, or cleanup behavior works where claimed.
- [ ] Automated rehearsal passes against the same golden build profile.
- [ ] The human walkthrough and automated rehearsal exercise the same declared
      RAES behavior and objectives.
- [ ] Durable evidence is committed as a rehearsal report.
- [ ] Teardown is run and verified; no live range resources remain.
- [ ] `pack.yaml.status: golden` is set only after the above proof exists.

## Manual Participant Walkthrough Protocol

- [ ] Stand up the golden range from the documented build entrypoint.
- [ ] Enter the range only through the participant execution surface.
- [ ] Work the intended happy path manually, command by command.
- [ ] Do not substitute scripts, SSM, Terraform output, generated passwords, or
      test harness internals for participant actions.
- [ ] When a defect is found, fix it on the branch as a bug.
- [ ] Use one commit per distinct problem when the walkthrough exposes multiple
      defects.
- [ ] Re-run the affected manual step after each fix.
- [ ] Complete the entire path after the last fix.
- [ ] Run automated rehearsal and relevant static/unit checks after the manual
      path works.
- [ ] Tear down the range and verify cleanup.
- [ ] Report exactly what was manually proven, what was automated, and what
      remains out of scope.

## Last-Pass Issues

Use umbrella last-pass issues for broad final review work. Slice PRs should use
`Refs #<issue>` until the whole last pass is complete. Close the umbrella issue
only after the final manual walkthrough checklist and evidence reconciliation
are complete.
