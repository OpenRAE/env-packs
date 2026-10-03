# Concepts

TechVault models a small enterprise whose internet-facing customer portal is a
route into internal identity, database, workstation, and file-share services.
The attacker begins from the Kali participant surface and follows the RAES
participant behavior declared in the SDL. Wazuh, Suricata, MISP, TheHive,
Cortex, and Shuffle form the defensive environment around that path. Cortex
executes the pack's exact offline scenario-context analyzer for observables
submitted through TheHive; the connector uses a dedicated `read`/`analyze`
service identity. Both API keys are backend-generated secret outputs joined to
their consumers with RAES generated-artifact `value_from` references instead
of authored values.

The SDL is the semantic authority. Files in `assets/content/` are immutable
materializations of its exact content requirements, while generated SSH and
certificate bundles remain backend-produced desired state. Pack metadata and
validation code do not redefine scenario behavior.

## Participant control and delivery

The study controller addresses separate red and blue Claude Code participants.
Four content items carry the participant instructions, while
`participant_inject_deliveries` bind those items to orchestration occurrences.
Mixed-control transitions make the controller's start and stop directions
explicit. A logical runtime clock orders the occurrences at ticks 1, 3, 5, and
7 with event-driven barrier progression.

The realization profile selects provider mechanics without moving instruction
content into a backend adapter. Observation boundaries limit each participant
to its addressed instructions. Delivery evidence records the crossing and the
provider result while leaving observation and compliance as distinct claims.

## Wazuh endpoint readiness

The six endpoint hosts (webapp, ad, dns, fileshare, victim and workstation),
PostgreSQL and Suricata each require Wazuh agent 4.12.0 and a stable
`techvault-<node>-agent` enrollment. Each identity has its own retained client
state and a matching active manager member. DB logs and Suricata EVE remain
owned by their respective scenario nodes; process placement and software
acquisition belong to the backend.

The `wazuh-agents-ready` precondition requires observed readiness for all eight
hosts. Its `wazuh-agent-readiness` evidence contract requires unique active
enrollment, readable sources and fresh telemetry attributable to the correct
host, including after restart or recreation. Missing, duplicate, stale or
disconnected required agents fail readiness. Generic syslog, manager health
and network alerts cannot substitute for another host's endpoint agent.

The observable `urn:techvault:observable:wazuh-agent-ready` names this scenario
requirement using RAE's existing Boolean predicate contract. A backend must
admit support and supply evidence; the pack supplies no evaluator or collection
method. Static validation proves the declarations and joins, not live readiness.
