# TechVault case management removal design

Issue #536 removes TheHive and Cortex from both TechVault packs and from the kit collection.
TheHive 5 needs a license after its trial, and its Community terms prohibit distribution.
The [preflight](techvault-case-management-removal-preflight.md) records the binding guardrails.
ADRs 0009, 0036, 0038, and 0041 govern the boundaries.

## Components and contracts

| Component | Change |
| --- | --- |
| TechVault SDL, both packs | Remove the `thehive`, `thehive-cassandra`, `thehive-es`, and `cortex` nodes and their `infrastructure` entries. Remove their accounts, principal, relationship, content, proposition, assertion, observation boundary, evidence requirement, and five volumes. |
| SOC certificate bundle | Remove the TheHive keystore outputs and the TheHive and Cortex consumers. The CA and the MISP and Shuffle selections do not change. |
| SOC workstation | Remove the `mcp-casemgmt` software component. |
| Pack content | Delete the two Cortex analyzer files. Remove the `casemgmt` and `thehive` forward records and the TheHive reverse record. Increment each zone serial. |
| MCP archive builder | Apply the reviewed rule-schema adaptation. Record its purpose for each archive. Remove `mcp-casemgmt` from `BLUE_PACKAGES`. |
| MCP archives | Rebuild both archives in `packs/techvault` and copy the same bytes to the study pack. The shipped red archive has GNU tar headers that the builder does not write. Its rebuild changes only the header format, not its members or contents. |
| Pack validator, both copies | Remove the Cortex contract check. |
| Artifact manifests | Remove the two analyzer entries. Derive checksums, sizes, set digests, SDL exact digests, and concept subject digests from the final bytes. |
| Pack documentation | Remove the TheHive and Cortex claims. |
| Kit collection | Delete `kits/infrastructure.thehive-case-management-service` and its three releases. |
| Composition walkthrough | Compose Wazuh and Suricata only. Keep the root relationship and the ownership refusal. |

`build_kit_catalog` derives offerings from release directories.
The checkout, sdist, wheel, and installed catalog therefore need no other change.

The MISP sync source archive and README are pinned upstream aptl bytes.
They mention TheHive, but they declare no TechVault service, so they do not change.
The generic `case-management` integration label in the Shuffle kit names no product.

## Failure behavior

| Condition | Result |
| --- | --- |
| A declaration refers to a removed node, account, or evidence requirement. | RAES parsing and `validate_pack` reject the pack. |
| An artifact digest, size, or set digest is stale. | Content-manifest validation and exact resolution reject the pack. |
| The reviewed upstream source hash changes. | The builder raises `RuntimeError` and writes no archive. |
| An adaptation does not apply exactly once. | The builder raises `RuntimeError` and writes no archive. |
| The walkthrough refers to an absent kit release. | `inspect` fails and the walkthrough exits nonzero. |

## Service graph

```text
Before, on security-net:
  thehive --cql_backend------> thehive-cassandra
  thehive --index_backend----> thehive-es
  thehive --backend_api------> cortex
  cortex  --index_backend----> thehive-es

After:
  No case-management or analyzer nodes.
  MISP, Suricata, Wazuh, Shuffle, and the SOC workstation do not change.
```

## Data flows and trust boundaries

```text
Local clone of the pinned aptl revision
  -- reviewed source bytes --> MCP archive builder
MCP archive builder
  -- deterministic USTAR bytes --> TechVault red and blue archives
Author
  -- identical blue archive bytes --> study pack
Final pack files
  -- bytes --> refresh tool --> artifact manifest and concept bindings
Pack files
  -- bounded reads --> validate_pack and RAES --> bounded diagnostics
Kit release directories
  -- release records --> build_kit_catalog --> checkout, sdist, and wheel catalogs
```

The upstream repository, the pack bytes, and the package distribution are separate trust boundaries.
The builder admits upstream bytes only when their SHA-256 values match the reviewed values.
The change adds no network destination, process, store, or deployment component.
The service graph and this data flow show all affected interfaces.

## Systems security engineering

| Asset | Protection need |
| --- | --- |
| Catalog and pack redistribution status | Compliance with the software license |
| Artifact identities | Integrity |
| SOC TLS material | Confidentiality and least privilege |
| Participant MCP telemetry | Confidentiality of tool payloads |

| Threat | Boundary | Control | Verification |
| --- | --- | --- | --- |
| The collection still offers the proprietary software. | Kit directories to distributions | Delete the complete kit tree. | Checkout and installed catalogs contain no TheHive kit. |
| A removed service keeps TLS or credential material. | SDL to backend | Remove the keystore outputs, consumers, and accounts. | The SOC consumer test checks each selection. |
| A rebuild drops the Wazuh rule-schema correction. | Upstream source to builder | Reviewed hash and exact replacements | Builder tests compare the adapted source and metadata with both archives. |
| A rebuild exports tool payloads in telemetry. | Upstream source to builder | The existing telemetry adaptation | Archive telemetry assertions |
| An artifact identity drifts. | Pack bytes to consumers | Derive identities from the final bytes. | `validate_pack` and the exact-resolution tests |
| A DNS name leads a participant to an absent host. | Pack content to scenario | Remove the three records. | The pack absence test scans both zone files. |

Earlier package versions and Git history still contain the kit and the services.
This change does not retract them.
The pinned upstream aptl bytes still mention TheHive.
The change grants no new execution authority, credential, or host access.

## Policy, architecture code, and decisions

The pack-local validator is the pack policy code.
The change removes its Cortex check and keeps the MISP, Suricata, Wazuh, Shuffle, and realization checks.
Repository tests assert that the retired declarations, files, archive members, and kit are absent.
CI workflows, scanners, and quality gates do not change.

The SDL `nodes` and `infrastructure` sections are the architecture code.
The change updates them, and no other infrastructure code exists.

No ADR changes.
ADR 0041 selects the kit collection by package version.
A new collection without the kit changes no released kit bytes.

## Reference basis

- [TheHive licenses](https://docs.strangebee.com/thehive/installation/licenses/about-licenses/), TheHive 5, "About licenses": TheHive is read-only after the trial without a license.
- [RFC 1035](https://www.rfc-editor.org/rfc/rfc1035), sections 3.3.13 and 5: zone file records and the SOA serial.
- [RFC 1912](https://www.rfc-editor.org/rfc/rfc1912), section 2.2: increment the serial when zone data changes.
- [Python tarfile](https://docs.python.org/3.14/library/tarfile.html), Python 3.14, `USTAR_FORMAT` and `TarInfo`: archive format and member metadata.
- [Reproducible archives](https://reproducible-builds.org/docs/archives/), current guide: fixed order, times, owners, and modes.
- [Official STE guidance](https://asd-ste100.org/about_STE.html), Issue 9: short sentences and one meaning per term.

The writing review checks brevity, active verbs, consistent terms, and document purpose.
Implementation tasks and verification results belong in the issue record.
