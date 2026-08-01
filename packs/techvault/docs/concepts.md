# TechVault concepts

TechVault is a purple-team enterprise range, not a standalone vault product.
The same environment supports participant attack activity, defensive
observation, threat-intelligence enrichment, case handling, analysis, and SOAR
discussion.

## Scenario domains

- **Enterprise targets:** a customer web application, PostgreSQL database,
  Active Directory domain, workstation, file share, DNS, and a victim host.
- **Red-team surface:** Kali and its capture companion, connected to the DMZ
  and internal range networks.
- **Security operations:** Wazuh, Suricata, MISP, TheHive, Cortex, Shuffle, and
  their stateful dependencies.
- **Platform observability:** OTEL collector, Tempo, and Grafana resources,
  kept conceptually separate from security-event evidence.

## ACES-first ownership

The RAES SDL owns scenario-meaningful state. Provider code may supply generic
substrate mechanics, but it must not select an appliance or inject TechVault
state merely because a filename, scenario id, or metadata value says
`techvault`. Every realized steady-state object should trace to an ACES resource.

Delivery bundles own only audience exposure and facilitation prose. They do not
own nodes, routes, identities, vulnerabilities, objectives, or scoring.

## Maturity boundary

The current pack is a source migration. APTL has existing consumers, but this
pack has not yet packaged and proven their provider realization. That work must
preserve consumer semantics while removing scenario-name-driven or
Compose-authoritative behavior where ACES now expresses the fact.
