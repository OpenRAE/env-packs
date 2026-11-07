# Attack Path

This explanation summarizes the scenario path without supplying a walkthrough or oracle.
The SDL owns objectives, conditions, identities, evidence, participant behavior, and relationships.
The participant exploits the vulnerable portal and obtains internal credentials and data.
The path continues through the workstation and victim hosts toward the declared TechVault objectives.
SOC services observe the activity.

The pack ships the scenario and its content.
It does not claim a completed golden participant walkthrough.
The [readiness checklist](golden-readiness-checklist.md) records the remaining operator checks.

The SDL requires one specific defensive observation.
A participant-equivalent SQL-injection request from Kali to `POST /login` must produce Suricata SID `1000010` in EVE.
It must also produce Wazuh web-attack rule `303020`.
File presence or aggregate alert counts do not prove that result.
