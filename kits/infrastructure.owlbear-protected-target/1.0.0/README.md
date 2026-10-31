# Owlbear protected target 1.0.0

This kit is static authoring content for an ARM64 Linux target with Owlbear inputs.
It exports the target, four artifact-input declarations, and a benign seed inventory.
The `daemon_active_state` parameter selects `active` or `inactive` service state.
Backend preparation must supply the service binding and compatible artifacts.
Service state does not establish enforcement or protection effectiveness.

Read [integration material](assets/integration.md) before composition.
Read [provenance](assets/provenance.md) for the reference revision and artifact limits.
The release includes no executable, cloud deployment, attacker behavior, or credential.
