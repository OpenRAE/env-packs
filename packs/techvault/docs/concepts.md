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
