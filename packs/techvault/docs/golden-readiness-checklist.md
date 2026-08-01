# Golden Readiness Checklist

Use this checklist for the final golden-range review. Keep the boxes unchecked
in source; copy the checklist into the issue, PR, or rehearsal report and mark
the boxes only for the run that actually proved them.

## Milestone Structure

- [ ] Scenario contract and pack skeleton exist.
- [ ] Topology, assets, and reference-triangle design are complete.
- [ ] Hidden path, affordance ledger, objective oracle, and validation model are complete.
- [ ] Flag, challenge, and reference CTFd layer are complete, or explicitly out of scope.
- [ ] Delivery profile bundles are complete, or explicitly out of scope.
- [ ] Golden build implementation exists in the declared live infrastructure.
- [ ] Automated live rehearsal exists for the golden build.
- [ ] Final manual participant walkthrough is tracked as its own issue or checklist item.
- [ ] Final docs, status, evidence, and teardown reconciliation are tracked.

## Golden Definition Of Done

- [ ] The range applies from a clean checkout using committed pack content.
- [ ] No hidden repo-root `.env`, external file fetch, or undocumented manual setup is required, except approved cloud/operator credentials.
- [ ] The declared golden build profile creates the participant start state.
- [ ] The participant entry surface exists, is documented, and is reachable.
- [ ] The full happy path is executed manually from the participant surface, command by command.
- [ ] Operator channels such as SSM, Terraform, cloud consoles, generated passwords, root/SYSTEM shells, and database consoles are used only for provisioning, diagnostics, reset, observation, or teardown.
- [ ] Every required objective, oracle state, flag, and success condition is reached from the intended participant privilege context.
- [ ] Negative gates prove objectives/flags are not trivially reachable before the required action or privilege.
- [ ] Reset, persistence, survival, or cleanup behavior works where claimed.
- [ ] Automated rehearsal passes against the same golden build profile.
- [ ] The human walkthrough and automated rehearsal agree path-for-path.
- [ ] Durable evidence is committed as a rehearsal report.
- [ ] Teardown is run and verified; no live range resources remain.
- [ ] `pack.yaml.status: golden` is set only after the above proof exists.

## Final Manual Participant Walkthrough Protocol

- [ ] Stand up the golden range from the documented build entrypoint.
- [ ] Enter the range only through the participant execution surface.
- [ ] Work the intended happy path manually, command by command.
- [ ] Do not substitute scripts, SSM, Terraform output, generated passwords, or test harness internals for participant actions.
- [ ] When a defect is found, fix it on the branch as a bug.
- [ ] Use one commit per distinct problem when the walkthrough exposes multiple defects.
- [ ] Re-run the affected manual step after each fix.
- [ ] Complete the entire path after the last fix.
- [ ] Run automated rehearsal and relevant static/unit checks after the manual path works.
- [ ] Tear down the range and verify cleanup.
- [ ] Report exactly what was manually proven, what was automated, and what remains out of scope.

## Last-Pass Issue Handling

- [ ] Use an umbrella last-pass issue for broad final review work.
- [ ] Use slice PRs with `Refs #<issue>` rather than `Closes #<issue>` until the whole last pass is complete.
- [ ] Add newly discovered work to the umbrella issue instead of treating the first slice as the whole scope.
- [ ] Close the umbrella issue only after the final manual walkthrough checklist and evidence reconciliation are complete.
