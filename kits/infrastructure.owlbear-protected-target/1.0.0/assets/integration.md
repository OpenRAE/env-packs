# Integrate the Owlbear protected target

## Exported RAES declarations

`target` is an ARM64 Ubuntu 24.04 compute node with two cores and 4 GiB RAM.
The kit leaves the compute substrate open.
Kernel access still requires explicit backend admission.
No host privilege, host mount, or network listener is granted.

`kernel_module`, `daemon_binary`, `game_binary`, and `signature_database` export input files for `target`.
`seed_inventory` exports benign reference defaults.
The source selectors and component paths appear in [provenance](provenance.md).

`daemon_active_state` changes the typed service-manager unit state.
The default is `active`; the alternative is `inactive`.
The portable unit ID is `owlbear_protection`.
No native manager, unit name, command, or unit file is supplied.
The backend must provide a supported binding from this unit ID to the actual daemon.
Its process target and native arguments must agree with the selected Owlbear build.
Upstream `owlbeard` requires a target PID; its `--enforce` flag selects enforcement mode.
Neither PID selection nor enforcement mode is a kit parameter.
Active state does not prove enforcement; inactive state does not prove an unprotected kernel.

## Composition notes

1. Inspect this exact kit release through the existing kit CLI or library.
2. Admit the staged source revision and review the unresolved artifact inputs.
3. Select `daemon_active_state` through the existing JSON parameter input on stdin.
4. Preview the proposal before applying it to a pack.
5. Connect independent networks, storage, or observation services at the pack root.
6. Validate the resulting ordinary pack and its artifact bindings.

The `deployment_profile` values are planning labels; both use the same declared resources.
Copied seed assets describe defaults and remain unchanged when parameters vary.
One materialization owns the fixed `assets/kits/owlbear-protected-target/` paths.
Additional namespaces can conflict at those paths.

## Realization limits

Backend preparation must admit the kernel module, embedded BPF programs, runtime libraries, and workload binary.
It must verify ARM64 kernel compatibility, module loading policy, BTF, and BPF LSM support.
The reference kernel is 6.17; other builds have no compatibility claim here.
A container that cannot satisfy those requirements must not be treated as an equivalent target.
The open substrate declaration grants no privilege and proves no backend capability.

The backend supplies the service binding, process identity, enforcement arguments, and any local log destination.
External telemetry delivery requires separate authorization and pack declarations.
The kit enables no upstream cloud platform or egress destination.
Composition tests do not start a daemon, load a kernel module, or produce protection evidence.
