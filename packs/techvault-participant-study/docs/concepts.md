# Concepts

TechVault models a small enterprise with an Internet-facing customer portal.
The portal provides a route to internal identity, database, workstation, and file-share services.
The attacker starts from Kali and follows the participant behavior in the SDL.
Wazuh, Suricata, MISP, and Shuffle form the defensive environment.

The SDL is the semantic authority.
Files in `assets/content/` supply exact content requirements.
The backend produces generated SSH and certificate bundles as desired state.
Pack metadata and validation code do not define scenario behavior.

## Participant control and delivery

The study controller addresses separate red and blue Claude Code participants.
Four content items contain participant instructions.
The `participant_inject_deliveries` declarations bind those items to orchestration occurrences.
Mixed-control transitions state the controller's start and stop directions.
A logical runtime clock orders occurrences at ticks 1, 3, 5, and 7 through event-driven barriers.

The realization profile selects provider mechanics.
Instruction content stays in the SDL rather than a backend adapter.
Observation boundaries limit each participant to its addressed instructions.
Delivery evidence records the boundary crossing and provider result.
Observation and compliance remain separate claims.

## Wazuh endpoint readiness

Eight hosts require Wazuh agent 4.12.0 and a stable `techvault-<node>-agent` enrollment.
They are webapp, ad, dns, fileshare, victim, workstation, PostgreSQL, and Suricata.
Each identity retains its own client state and needs a matching active manager member.
The database and Suricata nodes retain ownership of their respective logs and EVE output.
The backend selects process placement and software acquisition.

The `wazuh-agents-ready` precondition requires observed readiness for all eight hosts.
The `wazuh-agent-readiness` evidence requirement covers unique active enrollment, readable sources, and fresh telemetry from the correct host.
It also applies after restart or recreation.
Missing, duplicate, stale, or disconnected required agents fail readiness.
Generic syslog, manager health, and network alerts cannot replace a host's endpoint agent.

The observable `urn:techvault:observable:wazuh-agent-ready` uses RAE's existing Boolean predicate contract for this scenario requirement.
The backend must admit support and supply evidence.
The pack supplies no evaluator or collection method.
Static validation checks declarations and their references; it does not prove live readiness.
See the [pack reference](../README.md) for content and validation details.
