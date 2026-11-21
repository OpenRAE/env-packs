# Owlbear protected target 1.1.0

This kit is static authoring content for an ARM64 Linux target with Owlbear inputs.
It exports the target, four artifact-input declarations, and a benign seed inventory.
The `daemon_active_state` parameter selects `active` or `inactive` service state.
Backend preparation must supply the service binding and compatible artifacts.
Service state does not establish enforcement or protection effectiveness.

This release pins Owlbear source revision `652df5d6883809664917e6c734eec32a14fa40c4`.
That revision adds versioned research-artifact builds and local experiment interfaces.
Release 1.0.0 stays available and pins an earlier revision.

Read [integration material](assets/integration.md) before composition.
Read [provenance](assets/provenance.md) for the reference revision and artifact limits.
The release includes no executable, cloud deployment, attacker behavior, or credential.
