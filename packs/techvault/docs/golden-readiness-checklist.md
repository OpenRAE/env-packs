# Golden Readiness Checklist

TechVault is intentionally `built`, not `golden`. The work below is tracked by
OpenRAE/env-packs#237 and is not part of issue #234.

## Golden Definition Of Done

- [ ] A clean deployment consumes this released pack by exact artifact identity.
- [ ] The declared participant entry surface is reachable without hidden setup.
- [ ] The complete RAES participant behavior succeeds end to end.
- [ ] Negative gates demonstrate objectives are not reachable prematurely.
- [ ] Automated rehearsal passes and produces durable evidence.
- [ ] Teardown is verified and leaves no range resources behind.
- [ ] `pack.yaml.status` is changed to `golden` only after the evidence exists.

## Final Manual Participant Walkthrough Protocol

- [ ] Stand up the range from the released TechVault pack.
- [ ] Enter only through the participant execution surface.
- [ ] Execute the intended path manually, command by command.
- [ ] Record each reached objective and any defect found.
- [ ] Re-run affected steps after fixes, then complete the entire path.
- [ ] Run the automated rehearsal against the same build.
- [ ] Tear down the range and verify cleanup.
