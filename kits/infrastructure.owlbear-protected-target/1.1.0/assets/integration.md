# Integrate the Owlbear protected target

## Exported RAES declarations

`target` is an ARM64 Ubuntu 24.04 compute node with two cores and 4 GiB RAM.
The kit leaves the compute substrate open.
Kernel access still requires explicit backend admission.
The kit grants no host privilege, host mount, or network listener.

`kernel_module`, `daemon_binary`, `game_binary`, and `signature_database` export input files for `target`.
`seed_inventory` exports benign reference defaults.
The source selectors and component paths appear in [provenance](provenance.md).

`daemon_active_state` changes the typed service-manager unit state.
The default is `active`; the alternative is `inactive`.
The portable unit ID is `owlbear_protection`.
The kit supplies no native manager, unit name, command, or unit file.

The backend must provide a supported binding from this unit ID to the actual daemon.
Its process target and native arguments must agree with the selected Owlbear build.
Upstream `owlbeard` requires a target PID; its `--enforce` flag selects enforcement mode.
Neither PID selection nor enforcement mode is a kit parameter.
Active state does not prove enforcement; inactive state does not prove an unprotected kernel.

## Experiment interfaces

The reference revision adds version 1 of the Owlbear experiment interfaces.
`--sensors` selects BPF sensor groups.
`--control` binds a local Unix socket that uses the `owlbear.control.v1` schema.
`--events` writes local JSON Lines evidence that uses the `owlbear.event.v1` schema.
The upstream guide requires new socket and event paths for each run.

These arguments and paths are not kit parameters or declarations.
The backend or experiment controller selects them for each run.
The control socket is not a network listener.
The event file is local output, not an external telemetry destination.
The upstream control client `scripts/owlbearctl.py` is not part of the research-artifact payload.
This kit does not declare it.

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
The unsigned module requires the exact kernel release that its build manifest records.
The upstream README names kernel 6.17 as its reference; this kit fixes no kernel release.
Do not treat a container that cannot satisfy those requirements as an equivalent target.
The open substrate declaration grants no privilege and proves no backend capability.

Verify the upstream `SHA256SUMS` and build manifest before extraction.
Admit only outputs whose reported `source_commit` equals the reference revision.
The upstream guide tells operators to keep the manifest, archive checksum, and reported daemon identity with each run's evidence.
Checksums detect changed bytes; they do not authenticate a publisher.

The backend supplies the service binding, process identity, enforcement arguments, and any local log destination.
External telemetry delivery requires separate authorization and pack declarations.
The kit enables no upstream cloud platform or egress destination.
The kit bundles and declares no backend-specific runtime adapter.
Composition tests do not start a daemon, load a kernel module, or produce protection evidence.
