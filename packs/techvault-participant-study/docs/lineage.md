# Lineage

The full TechVault SDL and its tracked content were migrated from the APTL-era
`origin/dev` at commit `3db5171f3e4add842efd1d81fa0d4fe078511b7e`.
That project remains only a historical source and possible backend consumer;
TechVault is a portable scenario pack, and this repository is the editable
authority for its distributable content.

This study variant began as a byte-preserving copy of the TechVault pack. Its
intentional semantic additions are the `study-control` entity and controller,
Claude Code realization metadata for the red and blue agents, four instruction
content items, four inject/event occurrences, one ordered script and story, one
logical clock with four exact windows, two mixed-control behavior
specifications, and four delivery evidence requirements. Existing TechVault
content artifacts remain byte-identical.

The Suricata local corpus is the byte-identical 16-rule file from that pinned
migration source. Its configuration preserves the source's variables,
rule-file selection, outputs, application parsers, and command channel. Packet
capture and interface selection are left to the realizing backend. The initial
zero-indicator MISP rule file and three hash-list sidecars are also copied from
the pinned source, then become mutable runtime state under the declared sync
agent.

Directory-valued sources were captured as deterministic uncompressed tar
artifacts. Generated SSH keys and SOC certificates were deliberately not copied
from runtime state: RAES generated-artifact declarations retain that lifecycle
and keep producer-private material outside consumer projections.

The APTL-era tracked workstation fixture omitted
`projects/techvault-portal/.env` even though its SDL, archived TechVault
specification, and live smoke test all require it. The deterministic workstation
archive restores the specification's two synthetic loot values
(`DB_PASSWORD=techvault_db_pass` and `JWT_SECRET=techvault-jwt-weak`) rather than
copying an ignored local environment file. Runtime filesystem inventory retains
the final `dev-user` ownership and restrictive modes that make `.pgpass` and
the other planted credentials usable without shipping a corrective launch
unit.

The MISP synchronization source remains exact content, while its API principal,
TLS-verification posture, and public CA trust are declared as typed runtime
state. Credential bytes remain outside the pack.

The participant MCP source bundles were copied from APTL commit
`7c673a19f9fb6a3eb1d17305104196b600bd59cc`. The bundles preserve the package
source and build manifests required by the Kali and SOC workstations while
excluding backend configuration, dependencies, tests, and generated output.
The shared telemetry source is adapted to export only tool identity and status
metadata, never participant request, response, or error content.
