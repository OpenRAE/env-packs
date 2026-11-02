# Lineage

The full TechVault SDL and its tracked content came from the APTL-era
`origin/dev` at commit `3db5171f3e4add842efd1d81fa0d4fe078511b7e`.
That project remains only a historical source and possible backend consumer.
TechVault is a portable scenario pack. This repository is the editable
authority for its distributable content.

This study variant began as a byte-preserving copy of the TechVault pack. Its intentional semantic additions include the `study-control` entity and
controller, plus Claude Code realization metadata for the red and blue agents.
They include four instruction content items, four inject/event occurrences,
one ordered script and story, and one logical clock with four exact windows.
They also include two mixed-control behavior specifications, two participant
tool action contracts, and four delivery evidence requirements. Existing TechVault
content artifacts remain byte-identical.

The Suricata local corpus is the byte-identical 16-rule file from that pinned
migration source. Its configuration preserves the source's variables,
rule-file selection, outputs, application parsers, and command channel. The realizing backend selects packet capture and interfaces. The initial
zero-indicator MISP rule file and three hash-list sidecars also come from
the pinned source. They then become mutable runtime state under the declared
sync agent.

The Wazuh Suricata correlation rules carry the rule-chain repair from APTL
commit `ba418763a87eb250f7631de09afdc5f708cdf451`. The migrated file declared a
rival `decoded_as` JSON parent, `303000`, that never won against the Wazuh
built-in parent, so web-attack rule `303020` never fired. Each custom rule now
chains off the built-in rule for its event type: `86601` for alerts, `86603`
for DNS, and `86600` for flow. Unlike that commit, the pack removes `303000`
and chains DNS off `86603`, so that no level-0 rule hides an alert or shadows
the DNS refinement.

Deterministic uncompressed tar artifacts capture directory-valued sources.
The migration did not copy generated SSH keys or SOC certificates from runtime
state. RAES generated-artifact declarations retain that lifecycle and keep
producer-private material outside consumer projections.

The APTL-era tracked workstation fixture omitted
`projects/techvault-portal/.env` even though its SDL, archived TechVault
specification, and live smoke test all require it. The deterministic workstation
archive restores the specification's two synthetic loot values
(`DB_PASSWORD=techvault_db_pass` and `JWT_SECRET=techvault-jwt-weak`) rather than
copying an ignored local environment file. Runtime filesystem inventory retains
the final `dev-user` ownership and restrictive modes that make `.pgpass` and
the other planted credentials usable without shipping a corrective launch
unit.

The MISP synchronization source remains exact content. Typed runtime state
declares its API principal, TLS-verification posture, and public CA trust. Credential bytes remain outside the pack.

The participant MCP source bundles come from APTL commit
`7c673a19f9fb6a3eb1d17305104196b600bd59cc`. The bundles preserve the package
source and build manifests required by the Kali and SOC workstations while
excluding backend configuration, dependencies, tests, and generated output.
The adapted shared telemetry source exports only tool identity and status
metadata, never participant request, response, or error content.
