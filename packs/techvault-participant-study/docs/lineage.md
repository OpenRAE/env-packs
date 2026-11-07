# Lineage

This historical reference identifies the study pack's sources and intentional adaptations.
The full TechVault SDL and tracked content came from the APTL-era `origin/dev` at commit `3db5171f3e4add842efd1d81fa0d4fe078511b7e`.
That project remains a historical source and possible backend consumer.
This repository is the editable authority for the portable pack.

## Study additions

The study variant began as a byte-preserving copy of TechVault.
It adds the `study-control` entity and controller.
It adds Claude Code realization metadata for the red and blue agents.
It also adds four instruction items, four inject/event occurrences, one ordered script and story, and one logical clock.
The clock has four exact windows.

The variant adds two mixed-control behavior specifications and two participant tool action contracts.
It also adds four delivery evidence requirements.
Existing TechVault content artifacts remain byte-identical.

## Suricata content

The local Suricata corpus is the byte-identical 16-rule file from the pinned migration source.
Its configuration retains the source variables, rule-file selection, outputs, application parsers, and command channel.
The backend selects packet capture and network interfaces.

The migration also copied the empty MISP rule file and three hash-list sidecars.
These clean-start files become mutable runtime state under the declared synchronization agent.

## Wazuh correlation repair

The Wazuh correlation rules include the repair from APTL commit `ba418763a87eb250f7631de09afdc5f708cdf451`.
The migrated file declared a competing `decoded_as` JSON parent, rule `303000`.
The Wazuh built-in parent won the decode, so web-attack rule `303020` did not fire.

The pack chains each custom rule to the built-in rule for its event type.
Alerts use `86601`, DNS events use `86603`, and flows use `86600`.
The pack removes `303000` and uses `86603` for DNS.
Thus, no level-0 rule hides an alert or shadows the DNS refinement.

## Captured directories and generated material

Directory-valued sources use deterministic uncompressed tar artifacts.
The migration did not copy generated SSH keys or SOC certificates from runtime state.
RAES generated-artifact declarations retain that lifecycle and keep producer-private material outside consumer projections.

The tracked workstation fixture omitted `projects/techvault-portal/.env`.
The SDL, archived TechVault specification, and live smoke test require that file.
The deterministic workstation archive restores two synthetic values from the specification: `DB_PASSWORD=techvault_db_pass` and `JWT_SECRET=techvault-jwt-weak`.
It does not copy an ignored local environment file.
The runtime inventory retains final `dev-user` ownership and restrictive modes for `.pgpass` and the other planted credentials.
The pack therefore needs no corrective launch unit for those files.

## MISP and participant tools

The MISP synchronization source remains exact content.
Typed runtime state declares its API principal, TLS-verification posture, and public CA trust.
The original migration kept credential bytes outside the pack.
The current SDL later added public synthetic fixture material under the account binding; the [pack reference](../README.md#soc-credential-fixtures) describes that current state.

The participant MCP source bundles came from APTL commit `7c673a19f9fb6a3eb1d17305104196b600bd59cc`.
They retain package source and build manifests for the Kali and SOC workstations.
They exclude backend configuration, dependencies, tests, and generated output.
The adapted telemetry source exports only tool identity and status metadata.
It never exports participant request, response, or error content.
