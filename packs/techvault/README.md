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

APTL is being renamed to LilRAE. They are the same backend project across that
rename, not separate layers around TechVault. The `aptl` repository, CLI/package
names, and `APTL_*` environment variables in this pack are current compatibility
identifiers; they do not make TechVault anything other than a scenario pack.

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

## Suricata content contract

The Suricata configuration and 16-rule TechVault local corpus are exact pack
artifacts. The image-owned built-in rules remain a separate source. The four
empty MISP files are clean-start seeds in an ephemeral shared volume; the
declared MISP forwarding agent may replace them and reload the engine through
the private Unix socket. A consumer must not source or copy replacement files
from an APTL/LilRAE checkout.

Static validation joins the artifact identities, content placements, selected
rule files, variables, engine inventory, generated-output path, SID namespace,
shared volumes, reload target, and evidence requirements. Live readiness still
requires Suricata's native configuration test and realized evidence showing the
selected sources and 16 active local SIDs. The declared behavioral probe sends
a participant-equivalent SQL-injection request to `/login` and requires
Suricata SID `1000010` plus the existing Wazuh correlation rule `303020`.
Passing static validation does not by itself establish that live result.

When Docker is available, run the native exact-image gate from the repository
root with:

```sh
TECHVAULT_NATIVE_SURICATA=1 .venv/bin/python -m unittest \
  tests.test_techvault_suricata_native.NativeSuricataContractTests.test_exact_image_accepts_all_declared_rule_sources
```

The gate derives the image digest, built-in path, and content mounts from the
pack, verifies that the built-in file is non-empty inside that exact image, and
requires Suricata's native configuration test to load all three selected source
files with zero rule failures.

## Capture consumer contract

The Kali capture client uses protocol version 2 and fails closed. Before an SSH
session, the consuming control plane must pre-authorize an opaque, single-use
capability bound to the run and session identifiers, then supply it as
`APTL_CAPTURE_CAPABILITY`. The sidecar must reject absent, invalid, expired,
replayed, or identifier-mismatched capabilities and return matching
`session_accepted` and `session_finalized` acknowledgements. The client never
treats an unacknowledged or partial stream as valid evidence, and it removes the
capability from the participant command environment after starting capture.
