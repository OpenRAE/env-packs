# TechVault participant study

TechVault is the first-party RAES environment pack for the complete enterprise
intrusion scenario authored in `sdl/techvault-participant-study.sdl.yaml`. It includes the
scenario's vulnerable customer portal, enterprise services, attacker host,
defensive SOC, seeded data, and exact content artifacts. It declares the
in-world state a conforming realization must provide without selecting how a
backend constructs or exposes that state.

The pack is named `techvault-participant-study`; backend and deployment product names are not part
of its identity. A consumer validates the pack and its associated-artifact
manifest, then resolves each SDL `content.source` by opaque artifact id. No
consumer is expected to recover content from this repository's checkout paths
or from the former APTL source tree.

Historical source attribution is recorded in `docs/lineage.md` and
`docs/provenance-ledger.yaml`; no originating backend is part of TechVault's
portable identity.

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

## Portable realization boundary

TechVault uses an open realization designation and carries no substrate
constraints, machine images, build recipes, host-port publications, launch
commands, environment-variable delivery, capability grants, backend mounts, or
restart policy. Product and protocol versions are declared through typed RAES
runtime state when they are known. A backend remains free to choose its own
implementation while preserving those in-world facts and exact content bytes.
That state includes service credential posture, certificate trust, and the
final ownership and modes of scenario-significant files; it does not prescribe
how a backend supplies a secret, installs trust, or reaches that final state.

TechVault likewise does not select where realization evidence is collected.
The backend must authoritatively corroborate the declared state at the RAES
verification scope, but may use native control-plane readback, daemon
observation, guest observation, or another admitted method. It selects the
least intrusive complete method allowed by realization scope; omission of a
collection-method floor does not make evidence optional.

## Flag values

Each of `victim`, `workstation`, `webapp`, `fileshare`, and `ad` declares a user
flag and a root flag in the SDL. The backend supplies fresh values for all ten
required string variables (`flag_<host>_user` and `flag_<host>_root`) when it
instantiates a run. These variables have no defaults. Sensitive `content` files
place the values; each host's `filesystem_inventory` declares their ownership
and permissions. User flags retain mode `0644`, with `labadmin` ownership on
`victim`, `dev-user` on `workstation`, and `root` on the other hosts. Root flags
are owned by `root:root` with mode `0600` at `/root/root.txt`.

Generation, signing, and verification belong to the backend. The pack supplies
no flag generator, signing keys, token format, or flag-generation service.
Required variables express the backend-supplied values while RAES's native
per-run generated-value declaration is tracked in
[rae#1276](https://github.com/OpenRAE/rae/issues/1276). The SDL owns these file
declarations; TechVault does not duplicate them in a flag placement map.

## Participant MCP sources

TechVault ships immutable source bundles for the participant tools based on APTL
commit `7c673a19f9fb6a3eb1d17305104196b600bd59cc`. The Kali workstation receives
`aptl-mcp-common` and `mcp-red`; the separate SOC workstation receives the
common package plus the seven defensive MCP packages. Each host declares a
Node.js 22 runtime. The archives contain only source, package/build manifests,
the upstream MIT license, and source metadata—no dependencies, generated build
output, tests, backend configuration, or launch wrapper. The shared telemetry
wrapper is adapted to emit only tool identity and status metadata; it never
exports request, response, or error content. The SDL selects no installation or
process-management method.

## Cortex enrichment contract

TechVault ships one exact, dependency-free offline analyzer for scenario IP
context. Typed application state declares Cortex's analysis capability, the
least-privilege TheHive service identity, and TheHive's Cortex connector. The
backend realizes that state without an initializer node or credential-delivery
recipe. Cortex owns its internal index schema; the portable scenario does not
reproduce vendor-internal state.

## Suricata content contract

The Suricata configuration and 16-rule TechVault local corpus are exact pack
artifacts. Product-provided built-in rules remain a separate source. The four
empty MISP files are clean-start seeds in an ephemeral shared volume; the
declared MISP forwarding agent may replace them and reload the engine through
the private Unix socket. A consumer must not source or copy replacement files
from an APTL/LilRAE checkout.

Static validation joins the artifact identities, content placements, selected
rule files, variables, engine inventory, generated-output path, SID namespace,
shared volumes, reload target, and evidence requirements. Live readiness still
requires realized evidence showing a successful Suricata configuration and the
selected sources and 16 active local SIDs. The declared behavioral probe sends
a participant-equivalent SQL-injection request to `/login` and requires
Suricata SID `1000010` plus the existing Wazuh correlation rule `303020`.
Passing static validation does not by itself establish that live result.

## Red-team session evidence

TechVault requires a transcript of every interactive session on the red-team
workstation, covering the commands issued and responses returned. The SDL's
`redteam-session-transcript` evidence requirement defines its scope, lifetime,
redaction, integrity, and loss-disclosure posture without selecting a capture
mechanism. A realizing backend decides how to satisfy that requirement and must
report evidence loss rather than silently treating an uncaptured session as
captured.

## Participant study use

This pack copies TechVault assets and scenario state with a separate pack and SDL identity.
The participant uses the installed Claude CLI in their own host account and
a red MCP grant to reach the Kali tools. Start and stop the lab through the
normal APTL lab commands with this acquired pack selected. The existing red-team
session transcript requirement covers commands and responses; the operator
retains run identity, topology, outcomes, evaluator evidence, and limitations
with the experiment record. No provider credential is declared by this pack.
