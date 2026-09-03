# Attack Path

The authoritative objectives, conditions, identities, evidence, participant
behavior, and relationships are in `sdl/techvault.sdl.yaml`. In summary, the
participant exploits the vulnerable portal, obtains internal credentials and
data, pivots through the workstation and victim hosts, and reaches the declared
TechVault objectives while the SOC services observe the activity.

This document intentionally does not reproduce an oracle or walkthrough. The
current pack ships the scenario and its realizable content; golden participant
proof is deferred to issue #237.

One defensive observation is nevertheless explicit in the SDL contract: a
participant-equivalent SQL-injection request from Kali to the portal's
`POST /login` path must produce Suricata local signature `1000010` in EVE and
the corresponding Wazuh web-attack alert `303020`. This is an evidence
requirement for a clean realization, not a claim inferred from file presence or
aggregate alert counts.
