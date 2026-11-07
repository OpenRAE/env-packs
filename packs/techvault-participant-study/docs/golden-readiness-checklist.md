# Golden Readiness Checklist

Use this operator how-to guide to collect evidence for one exact pack build.
The current pack status is `built`; no golden qualification follows from static checks.
Copy the checklist into the build's evidence and leave this source copy unchecked.
[Qualification work](https://github.com/OpenRAE/env-packs/issues/237) remains separate from the original migration.

## Golden Definition Of Done

- [ ] Deploy the released pack by exact artifact identity into a clean environment.
- [ ] Verify participant access through the declared entry surface without hidden setup.
- [ ] Complete the declared RAES participant behavior from start to finish.
- [ ] Demonstrate that negative gates prevent early objective access.
- [ ] Run the automated rehearsal and retain durable evidence.
- [ ] Send a fresh SQL-injection probe from Kali to webapp at `POST /login`.
- [ ] Retain Suricata SID `1000010` and Wazuh rule `303020` from that probe and the pack-owned inputs.
- [ ] Verify teardown and confirm that no range resources remain.
- [ ] Change `pack.yaml.status` to `golden` only after the evidence exists.

## Final Manual Participant Walkthrough Protocol

- [ ] Start the range from the exact released pack.
- [ ] Enter only through the participant execution surface.
- [ ] Complete the intended path manually, command by command.
- [ ] Record each objective and each defect.
- [ ] Repeat affected steps after fixes, then complete the entire path.
- [ ] Run the automated rehearsal against the same build.
- [ ] Tear down the range and verify cleanup.

The [attack-path explanation](attack-path.md) describes the required defensive observation.
A completed checklist needs runtime evidence; the checklist itself is not proof.
