# TechVault

TechVault is the first-party RAES environment pack for this enterprise intrusion scenario.
It contains a vulnerable customer portal, enterprise services, an attacker host, and defensive SOC services.
The pack includes seeded data and exact content artifacts.
The SDL in `sdl/techvault.sdl.yaml` declares the required in-world state.
The backend chooses how to realize it.
The pack identity is `techvault`; backend and deployment product names are not part of its identity.

This reference describes pack content and its limits.
Read [concepts](docs/concepts.md) for the scenario explanation.
The [lineage record](docs/lineage.md) and [provenance ledger](docs/provenance-ledger.yaml) retain historical source attribution.
Their revisions describe the original sources, not new runtime qualification.

## Preserved source material

`assets/content/misp-sync-readme.md` preserves upstream APTL documentation used by the synchronization package.
Its installation commands describe that upstream project.
Use this pack's validation commands for the current source.
The fileshare and workstation archives also contain fictional documents that form exact scenario content.
Their text is scenario evidence, not authoring instructions.

The lineage record describes earlier source choices.
Its statement about credentials outside the pack does not describe the current synthetic account fixtures below.
Current fixture declarations remain in the SDL.

## Maturity

The pack status is `built`.
The scenario definition and byte-bound content are present, but this repository claims no golden-range proof.
[Golden qualification work](https://github.com/OpenRAE/env-packs/issues/237) remains separate.

## Validation

The following trusted-author commands run from the repository root in a virtual environment:

```sh
python -m pip install -e ".[test]"
raes-pack-validate --packs-root packs
raes-pack-release check --packs-root packs
python -m unittest tests.test_techvault_pack
```

These checks verify static declarations, content bindings, and release structure.
They do not deploy the environment or demonstrate live readiness.
The [exact-copy profile](profiles/exact-artifact-copy-v1.json) defines the digest-bound route for exact content requirements.
Tar assets carry deterministic POSIX tar members for the declared directory destination.
Consumers resolve each SDL `content.source` by opaque artifact ID.
Checkout paths and the former APTL source tree are not content-resolution interfaces.

## Portable realization boundary

TechVault leaves realization open.
It supplies no substrate constraints, machine images, build recipes, host-port publications, launch commands, capability grants, backend mounts, or restart policy.
It does not select environment-variable delivery.
Typed RAES runtime state declares product and protocol versions where available.
The backend must preserve those in-world facts and the exact content bytes.

That state includes service credential posture, certificate trust, and final file ownership and modes.
It does not prescribe secret delivery, trust installation, or the method that establishes the final state.
The backend must corroborate declared state at the RAES verification scope.
It can use native control-plane readback, daemon observation, guest observation, or another admitted method.
It selects the least intrusive complete method that the realization scope permits.
The absence of a collection-method floor does not make evidence optional.

## SOC credential fixtures

SOC logins are in-world accounts.
Their RAES `accounts.<account-id>.credential_bindings` contain synthetic `secret_fixture` values.
Each primary binding has the name `<account-id>-primary`.
No backend environment variable or secret-store lookup supplies these fixture values.

| Surface | Account reference | Username |
| --- | --- | --- |
| Wazuh indexer / dashboard interactive login / Filebeat | `accounts.wazuh-indexer-admin` | `admin` |
| Wazuh dashboard service login to the indexer | `accounts.wazuh-indexer-kibanaserver` | `kibanaserver` |
| Wazuh manager API | `accounts.wazuh-manager-api` | `wazuh-wui` |
| Shuffle console | `accounts.shuffle-administrator` | `admin@techvault.local` |
| MISP console | `accounts.misp-administrator` | `admin@admin.test` |
| MISP synchronization API | `accounts.misp-suricata-sync-api-key` | `techvault-suricata-sync` |

The MISP runtime principal and API setting have `redacted` posture because those RAES surfaces omit raw material.
Their account bindings contain the public synthetic fixtures.
Neither identity is an operator credential.
The synchronization key contains exactly 40 ASCII alphanumeric characters.
[MISP's provisioning source](https://github.com/MISP/MISP/blob/2.5/app/Console/Command/UserShell.php) defines that format.
The pack-local author validator rejects other lengths or characters without printing the rejected value.

Filebeat and dashboard configurations contain passwords that match the bindings.
The indexer hashes match those values.
Tests check correct-password matches and incorrect-password rejection.
Credential files declare restricted ownership and modes.
The Filebeat configuration follows the [Wazuh 4.12.0 source](https://github.com/wazuh/wazuh/blob/v4.12.0/extensions/filebeat/7.x/filebeat.yml).
It retains the Wazuh module, index-template behavior, and certificate-verified HTTPS to the declared indexer.

The internal-users file supplies initialization content.
A retained security index can contain earlier state.
The backend must corroborate credentials during realization and handle retained state through its migration policy.
Static validation neither proves live authentication nor migrates retained data.

## Flag values

Each of `victim`, `workstation`, `webapp`, `fileshare`, and `ad` declares one user flag and one root flag.
The backend supplies fresh values for all ten required string variables when it instantiates a run.
The variable names are `flag_<host>_user` and `flag_<host>_root`; they have no defaults.
Sensitive `content` files place the values.
Each host's `filesystem_inventory` declares ownership and permissions.

User flags have mode `0644`.
Their owners are `labadmin` on `victim`, `dev-user` on `workstation`, and `root` on the other hosts.
Root flags have owner `root:root`, mode `0600`, and path `/root/root.txt`.
The SDL owns these declarations; the pack has no duplicate flag-placement map.

Flag generation, signing, and verification belong to the backend.
The pack provides no flag generator, signing key, token format, or flag-generation service.
Required variables express backend-supplied values.
[RAE's generated-value work](https://github.com/OpenRAE/rae/issues/1276) remains a separate upstream concern.

## Participant MCP sources

The participant tool bundles derive from APTL commit `7c673a19f9fb6a3eb1d17305104196b600bd59cc`.
Kali receives `aptl-mcp-common` and `mcp-red`.
The separate SOC workstation receives the common package and six defensive MCP packages.
Both hosts declare Node.js 22.
The archives contain source, package/build manifests, the upstream MIT license, and source metadata.
They contain no dependencies, generated builds, tests, backend configuration, or launch wrapper.

Runtime Wazuh MCP configuration must send custom-rule writes to `PUT /rules/files/{filename}`.
Those requests require Wazuh JWT authentication and `overwrite=true`.
Runtime configuration supplies service URLs and credentials.
The adapted telemetry wrapper exports only tool identity and status metadata.
It never exports request, response, or error content.
The SDL selects no installation or process-management method.

## Suricata content contract

The Suricata configuration and 16-rule TechVault local corpus are exact artifacts.
Product-provided built-in rules have a separate source.
The four empty MISP files seed an ephemeral shared volume.
The declared forwarding agent can replace them and reload Suricata through its private Unix socket.
A consumer must not obtain replacement files from an APTL or LilRAE checkout.

Static validation checks artifact identities, placements, selected rule files, variables, engine inventory, output paths, SID namespace, shared volumes, reload target, and evidence requirements.
Live readiness requires evidence of successful configuration, selected sources, and 16 active local SIDs.
The declared SQL-injection probe sends a participant-equivalent request to `/login`.
It requires Suricata SID `1000010` and Wazuh correlation rule `303020`.
Static validation alone does not establish that result.

## Red-team session evidence

TechVault requires a transcript of every interactive red-team workstation session, including commands and responses.
The SDL's `redteam-session-transcript` requirement defines scope, lifetime, redaction, integrity, and loss disclosure.
It does not select a capture mechanism.
The backend must satisfy the requirement and report evidence loss.
It must not describe an uncaptured session as captured.
