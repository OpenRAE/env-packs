# `techvault` scenario pack

TechVault is the purple-team enterprise range already developed and consumed in
APTL, now migrating into a self-contained ACES scenario pack under the same
`techvault` identity. It combines a vulnerable business environment, a Kali
red-team surface, and an integrated defensive stack including Wazuh, Suricata,
MISP, TheHive, Cortex, and Shuffle.

[`sdl/techvault.sdl.yaml`](sdl/techvault.sdl.yaml) is the only authored scenario
authority. It is adapted from APTL's operational RAES SDL and uses standard ACES
resources for nodes, networks, services, dependencies, generated artifacts,
persistent volumes, content placement, vulnerabilities, domains, relationships,
and accounts. The pack does not define an `x-techvault` scenario contract or a
second topology ledger.

The pack is `golden`. The `operational` profile launched from committed source
on an isolated cloud Docker host, the manual participant journey ran through
the loopback Kali SSH surface, the packaged rehearsal passed afterward, reset
restored authored state, and independent Docker and AWS teardown checks found
no live range resources. The indexed Wazuh path remains a documented
purple-team visibility gap; manager and Suricata evidence do not conceal it.

## Delivery

The guided, unguided, purple-team, and demo bundles all project documentation
onto the same `operational` ACES scenario. Bundle selection changes exposure,
not runtime facts. No flag layer or agent benchmark ships: the current APTL
scenario does not author scored ACES objectives, evidence, or scoring semantics.

## Source map

| Path | Purpose |
|---|---|
| [`sdl/techvault.sdl.yaml`](sdl/techvault.sdl.yaml) | Canonical ACES scenario definition. |
| [`assets/runtime/wazuh/`](assets/runtime/wazuh/) | Pack-contained source inputs referenced by ACES generated artifacts. |
| [`assets/content/onboarding/`](assets/content/onboarding/) | Pack-contained directory referenced by ACES content placement. |
| [`assets/briefing/mission-brief.md`](assets/briefing/mission-brief.md) | Participant-safe purple-team mission framing. |
| [`build/`](build/) | Pack-local APTL runtime source plus launch, health, reset, cleanup, generated-state rendering, and build validation. |
| [`profiles/`](profiles/) | Audience projections and their ACES-aware validator. |
| [`docs/provenance-ledger.yaml`](docs/provenance-ledger.yaml) | Exact APTL source pin, licensing, and adaptation record. |
| [`docs/rehearsal-report-392.md`](docs/rehearsal-report-392.md) | Durable automated live rehearsal report from the isolated-host operational-profile run. |
| [`docs/walkthroughs/manual-participant-walkthrough.md`](docs/walkthroughs/manual-participant-walkthrough.md) | Reusable command-by-command Kali participant and red/blue comparison procedure. |
| [`docs/manual-participant-walkthrough-report-393.md`](docs/manual-participant-walkthrough-report-393.md) | Final manual proof, defect/rerun record, automated follow-up, and verified teardown evidence. |
| [`docs/topology-reference-triangle.md`](docs/topology-reference-triangle.md) | Migration and proof status without a duplicate resource inventory. |

The source capture is pinned to APTL commit
`43f137450268f25615c07b9a24144540dfac3c34`. The upstream repository is MIT
licensed; copied/adapted artifacts and their usage are recorded in the
provenance ledger.

## Validation

```bash
python3 scenarios/techvault/build/validate_build.py validate
python3 -m unittest discover -s scenarios/techvault/build/tests
python3 scenarios/techvault/profiles/validate_profiles.py validate
python3 scripts/ci/scenario_content_ci.py
```

The live rehearsal command is deliberately separate from CI and must run only
on a disposable isolated Docker host:

```bash
python3 scenarios/techvault/build/rehearsal.py run --isolated-docker-host
```

The golden evidence boundary is the pair of immutable run reports plus the
manual walkthrough: #392 records the packaged automated rehearsal in detail;
#393 records the human Kali path, post-manual automation, reset, visibility
gap, and zero-residual teardown.
