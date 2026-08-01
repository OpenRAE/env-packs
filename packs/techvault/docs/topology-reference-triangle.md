# TechVault topology and reference-triangle status

`pack.yaml.contents.reference_triangle` is `true`.

## Scenario authority

The topology side of the future triangle is
[`../sdl/techvault.sdl.yaml`](../sdl/techvault.sdl.yaml). This document does not
repeat its node, network, service, dependency, content, identity, artifact, or
volume rows. Validators and provider integrations must parse ACES directly.

## Migration joins

| Triangle side | Current source | Pack status |
|---|---|---|
| Topology and scenario state | RAES SDL plus its pack-contained source files | Shipped as authored source |
| Provider realization | Pinned pack-local APTL Docker Compose runtime under `build/aptl-runtime/` plus lifecycle wrappers | Operational profile builds, reaches participant start state, resets, and cleans up in the #392 live rehearsal |
| Automated tests/rehearsal | Pack-native static build contract tests plus `build/rehearsal.py` live clean-build rehearsal | Harness packaged, unit-tested, and passing on the isolated-host operational-profile run |
| Manual participant walkthrough | Kali-entry command-by-command red path with blue observation | #393 passed through `kali-ssh-proxy`; the guide and value-sparse run report ship in `docs/walkthroughs/` and `docs/` |

Migration must adapt the battle-tested APTL consumer to this pack without
preserving pathologies. Scenario-name checks, local parity ledgers, copied
Compose truth, and appliance selection inferred from descriptive metadata are
not valid joins. Scenario-meaningful steady state belongs in ACES; generic
substrate mechanics remain provider-owned.

The reference triangle is complete. The packaged provider build, automated
rehearsal, and manual participant walkthrough all use the same `operational`
profile and stable ACES/rehearsal ids. The #393 run fixed the clean-host Wazuh
certificate-permission defect, relaunched from the fixed committed tree,
completed the human journey, reset, passed post-manual automation, and produced
zero Docker/AWS residuals.

Golden status does not imply a scored oracle or perfect telemetry. TechVault
does not declare objectives or flags, and the indexed Wazuh collection gap is
preserved in the manual report.
