# TechVault

TechVault is the first-party RAES environment pack for the complete enterprise
intrusion scenario authored in `sdl/techvault.sdl.yaml`. It includes the
scenario's vulnerable customer portal, enterprise services, attacker host,
defensive SOC, seeded data, and exact content artifacts needed by a consuming
RAES backend.

The pack is named `techvault`; backend and deployment product names are not part
of its identity. A consumer validates the pack and its associated-artifact
manifest, then resolves each SDL `content.source` by opaque artifact id. No
consumer is expected to recover content from this repository's checkout paths
or from the former APTL source tree.

## Maturity

The pack is `built`: the complete scenario definition and byte-bound content
are present, but this repository does not yet claim golden-range proof. Golden
build, rehearsal, and participant walkthrough work is tracked separately in
[issue #237](https://github.com/OpenRAE/env-packs/issues/237).

## Validation

From the repository root:

```sh
raes-pack-validate --packs-root packs
raes-pack-release check --packs-root packs
python -m unittest tests.test_techvault_pack
```

The pack-local satisfaction profile in
`profiles/exact-artifact-copy-v1.json` defines the digest-bound copy route used
by every exact content requirement. Tar assets are deterministic POSIX tar
carriers whose members are materialized at the declared directory destination.

## Capture consumer contract

The Kali capture client uses protocol version 2 and capture is best-effort:
SSH authentication is the only access boundary, and a session is never denied
for a capture-availability reason. Before an SSH session, the consuming
control plane may pre-authorize an opaque, single-use capability bound to the
run and session identifiers and supply it as `APTL_CAPTURE_CAPABILITY`;
capture activates only when that capability, the sidecar, and `script(1)` are
all available, and any missing prerequisite degrades the session to
unrecorded instead of denying it. The sidecar must reject absent, invalid,
expired, replayed, or identifier-mismatched capabilities and return matching
`session_accepted` and `session_finalized` acknowledgements. The client never
treats an unacknowledged or partial stream as valid evidence, and the
capability is removed from the participant command environment on every
path, whether or not capture starts.
