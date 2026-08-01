# TechVault exercise path

This document gives facilitators a scenario reading; it is not a second path
contract. The authoritative resources and relationships are in
[`../sdl/techvault.sdl.yaml`](../sdl/techvault.sdl.yaml).

## Authored starting state

The red participant enters through the ACES `kali` node, which links to the
red-team, DMZ, and internal networks. Enterprise targets include `webapp`, `ad`,
`db`, `workstation`, `fileshare`, `dns`, and `victim`. The ACES graph also
authors the defensive and observability services that support purple-team
comparison.

## Authored weakness and context

ACES explicitly declares `webapp-sqli-login`, a CWE-89 SQL injection weakness
in the customer portal login. It also declares a TechVault Active Directory
domain, its controller relationship, and representative weak,
Kerberoastable, over-privileged, and stale account conditions. Fileshare notice
and onboarding content are ACES content placements.

These facts create useful avenues for discovery and red/blue investigation, but
the SDL does not currently author a mandatory linear exploit chain, scored
objectives, flags, or completion oracle. Facilitators must not turn historical
APTL implementation details into a hidden pack-local sequence.

## Purple-team evidence

Participant actions should be compared with the Wazuh and Suricata surfaces and
then, where realized, with MISP, TheHive, Cortex, and Shuffle workflows. A
missing observation may indicate provider, configuration, dependency, or
detection-content work; it is not automatically participant failure.

## Proof boundary

The golden proof follows a representative human journey rather than inventing
a mandatory chain: Kali reachability, portal baseline, rejected login, the
authored SQL injection, dashboard/admin context, web and SMB state, bounded
telemetry-generating activity, and a red/blue comparison. #393 executed those
steps manually through `kali-ssh-proxy`, then proved reset/freshness, ran the
packaged rehearsal, and verified teardown.

Provider administration, direct data stores, generated credentials, and test
harnesses remain observer/lifecycle tools only. The Wazuh manager and Suricata
observed the run-specific failed-SSH activity; indexed Wazuh collection did
not, and that visibility gap is part of the exercise result rather than hidden
by the golden claim.
