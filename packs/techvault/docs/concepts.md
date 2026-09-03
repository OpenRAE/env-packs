# Concepts

TechVault models a small enterprise whose internet-facing customer portal is a
route into internal identity, database, workstation, and file-share services.
The attacker begins from the Kali participant surface and follows the RAES
participant behavior declared in the SDL. Wazuh, Suricata, MISP, TheHive,
Cortex, and Shuffle form the defensive environment around that path. Cortex is
an independently reachable status/API surface only: the pack declares neither
enabled analyzers nor a TheHive connector, so it provides no enrichment
capability.

The SDL is the semantic authority. Files in `assets/content/` are immutable
materializations of its exact content requirements, while generated SSH and
certificate bundles remain backend-produced desired state. Pack metadata and
validation code do not redefine scenario behavior.
