# TechVault Suricata packet-processing preflight

Issue #284 is not a command-flag defect. TechVault declares a passive Suricata
sensor, HTTP inspection, detection output, and a Suricata-to-Wazuh hand-off, but
the current process posture and Docker network attachment do not establish that
the sensor can observe and inspect the traffic the scenario depends on. The
reported live finding adds a second, independent failure mode: packets observed
on the Docker/veth path can carry checksum-offload artifacts that Suricata
rejects before HTTP flow and transaction inspection.

Changing checksum validation altered the observed behavior, but prior live
testing did not establish complete packet visibility. This note records the
existing contract, the evidence gap, and the authority boundaries that constrain
the eventual solution. It is not an implementation plan and does not select a
capture mechanism or Suricata flag.

## Current path and contract inventory

The participant-equivalent representative HTTP path is Kali on `dmz-net`
(`172.20.1.30`) to the web application on the same network
(`172.20.1.20:8080`). Host traffic through `webapp-proxy` is a different path and
cannot stand in for that participant path. The intended defensive chain is:

`Kali -> dmz-net observation point -> Suricata packet/stream/HTTP inspection ->
Suricata alert/EVE -> suricata_logs -> wazuh-sidecar-suricata -> Wazuh`

| Concern | Authored state | What it proves | Gap exposed by live evidence |
| --- | --- | --- | --- |
| Traffic path | Kali and webapp share `dmz-net`; the webapp serves HTTP on 8080 | The endpoints can exchange participant traffic | It does not identify a sensor observation point or mirror traffic to the sensor |
| Sensor placement | Suricata is attached to `security-net`, `dmz-net`, and `internal-net` | The container has interfaces on those networks | Ordinary network membership does not prove visibility of unicast traffic between other endpoints; `redteam-net` is declared monitored but is not attached to this node |
| Sensor intent | `RuntimeNetworkSensor` declares passive IDS, `capture_mode: af_packet`, `capture_interfaces: [any]`, and four monitored networks | The portable requirement names intended capture mode and network scope | `any` names interfaces in the selected namespace; it does not mean every host bridge or peer veth is observable |
| Effective process | The exact container entrypoint executes `suricata ... --pcap`; the mounted config contains both `af-packet` and `pcap` sections | The process starts with an authored command and configuration | The selected pcap command conflicts with the sensor's authored `af_packet` mode; no `RuntimeProcessIdentity` or sensor/engine `process_ref` binds the inventory to the effective process |
| Checksum handling | No authored checksum policy or backend observation disclosure exists | Nothing beyond Suricata/image defaults | The issue's live evidence reports veth/offload packets classified invalid and missing HTTP inspection; changing checksum handling alone did not prove visibility |
| Detection engine | The engine declares HTTP support, rule sources, and an enabled EVE stream containing alert/http/flow/stats events | The intended parser, rule, and output inventory | Enabled output and loaded-rule declarations are desired state, not observations that packets, HTTP transactions, or an expected alert were produced |
| Detection content | `techvault-local` claims 16 loaded rules, but the inline `suricata-local-rules` file currently contains only comments | Nothing executable for a stable TechVault-local alert | Issue #283 owns the content correction. Issue #284 must consume one stable expected detection from that authority rather than inventing a second rule here |
| SIEM hand-off | `suricata_logs` gives Suricata read/write access and the Wazuh sidecar read-only access; the sidecar tails `eve.json` | A declared file-based delivery route | File existence, sidecar health, or a Wazuh alert from the webapp's separate rsyslog path does not prove the Suricata path |
| Readiness/evidence | The sensor and engine have no evidence refs; the SDL has no proposition, assertion, observation boundary, or evidence requirement for this path | Process-level readiness may still be reported elsewhere by the backend | No portable gate distinguishes running, packet-visible, HTTP-inspecting, alerting, and SIEM-delivered states |

The repository contains no durable live report with packet counters, EVE samples,
or before/after topology observations for this finding. The issue evidence is
therefore enough to reject the current readiness claim and one-flag shortcut,
but not enough to select the final mechanism. The implementation evidence must
record, for the same clean realization and marked test flow, the endpoint path,
actual observation point, selected capture mechanism, checksum-invalid counters,
bidirectional packet/flow visibility, HTTP transaction output, the exact
TechVault detection, and its downstream delivery outcome. Raw payloads are not
required to prove those facts.

## Authority and classification

Keep these facts separate through authoring, realization, and evidence:

| Class | Owner and carrier | Rule |
| --- | --- | --- |
| Authored detection requirement | TechVault through existing RAES SDL sensor, detection-engine, proposition/assertion, observation-boundary, and evidence-requirement fields | State the networks/path, protocol inspection, selected detection content, expected outcome, and loss posture without naming Docker bridges, veth peers, mirroring commands, or host interfaces |
| Authored process posture | TechVault through `RuntimeContainerConfiguration`, `RuntimeProcessIdentity`, and sensor/engine `process_ref` when the posture is invariant across conforming backends | The command, declared capture mode, and referenced config must agree. A Docker-only checksum workaround is not automatically portable author intent |
| Backend realization choice | LilRAE/APTL through the RAES realization envelope, admitted plan, and backend configuration | Select and validate the concrete observation mechanism, namespace/interface attachment, offload/checksum treatment, privileges, and probe implementation. A clean realization must contain the choice before start |
| Observed satisfaction | RAES runtime snapshot realization provenance/observations, proposition truth, and evidence records | Record the selected mechanism and observed outcome as realization facts; never rewrite them into the authored SDL or infer them from process health |
| Detection content | Issue #283 and the RAES detection/rule-source declarations | Reuse one stable, exact TechVault rule and expected alert. Do not make #284 a parallel content authority or use mutable built-in rules as the acceptance oracle |
| Generic kit guidance | The first-party Suricata kit under `kits/` | The kit explicitly makes no launch, readiness, traffic-attachment, or evidence claim. Do not place TechVault topology or Docker-specific mechanics in that generic release |

The current SDL has no `realization` designation, so pinned RAES 3.3 applies its
legacy closed-world default. LilRAE cannot silently append a process flag or
replace the command after realization. If the accepted mechanism requires
backend variation in an authored field, the author must open or constrain only
that exact field through the existing RAES realization designation/envelope and
the backend must disclose the selected value. An omitted field or broad
scenario-level opening is not permission for arbitrary mutation.

## Canonical contracts to reuse

Pinned `raes==3.3.0` already supplies the applicable cross-cutting surfaces:

- `RuntimeNetworkSensor` owns sensor identity, posture, capture mode/interfaces,
  monitored network refs, process/config/log refs, and evidence refs.
- `RuntimeNetworkDetectionEngine` owns the sensor join, application protocols,
  exact rule sources, output streams, control channels, process/config/log refs,
  and evidence refs. Its `sensor_ref` is the canonical sensor-to-engine join.
- `RuntimeProcessIdentity` and `RuntimeContainerConfiguration` own the effective
  process/command inventory. Do not add a Suricata command schema, checksum
  field, or pack-local process model.
- Existing propositions, postcondition assertions, observation boundaries, and
  `EvidenceRequirement` own portable detection-effectiveness intent. The
  `packet_capture`, `log`, and `api_response` channels describe evidence classes;
  they do not prescribe Docker capture commands.
- `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`,
  `ExperimentRawEvidenceContentModel`, and `PropositionTruthResultModel` keep
  executable capture, observed evidence, loss disclosure, and truth outcomes
  distinct.
- `RuntimeSnapshotEnvelopeModel.realization_provenance` and
  `realization_observations`, plus the realization envelope, own the selected
  backend mechanism and corroboration. Authored, processor-derived, and
  backend-realized facts must remain distinguishable.
- Backend readiness must use its existing typed health/readiness state and
  evidence references. A running process may be healthy while the detection
  proposition is false or indeterminate; such a realization must not be
  reported ready for the declared defensive capability.

Within this repository, all SDL changes continue through `raes.parse_sdl_file`
via the shared `validate_pack()`/author-CI authority and the TechVault contract
tests. `validate_pack_content_manifest()` and `resolve_pack_artifact()` remain
the only content-byte authority; diagnostics remain bounded, payload-free
`ValidationResult` records and content identity failures remain
`PackDigestError`. An SDL-only edit uses
`tools/refresh_pack_sdl_binding.py`; changed pack payload bytes require the full
associated-artifact derivation authority, never independent checksum edits.

## Cross-cutting gates

| Layer | Required guardrail |
| --- | --- |
| RAES shape and semantic validation | Use the pinned closed models and existing reference validation for sensor, engine, process, network, proposition, assertion, boundary, and evidence fields. Raise reusable semantic gaps in RAES; do not add a local schema or validator with new SDL meaning |
| Pack validation and author CI | Preserve the descriptor-anchored static snapshot, anti-extension guard, visibility/leak scan, bounded subprocess execution, and deterministic diagnostics. Pack-local tests may assert TechVault's exact joins but must not become a reusable network-sensor validator |
| Pack artifact identity | Keep the SDL parent digest, exact artifact checksums/sizes, and RAES set digest synchronized through the derivation tools. A documentation-only preflight outside `packs/` does not change pack identity |
| Backend admission/config shape | Before launch, validate that the selected mechanism can observe every required path/network and can realize the declared process posture. Reject the plan or report the detection proposition unsatisfied when that capability is absent; never degrade silently |
| Network and OS security | Grant only the capture capabilities and namespace/interface access the selected mechanism requires. Do not default to privileged mode, host networking, host PID namespace, broad device access, or mutable host offload state. Account for cross-range traffic exposure when observing a host bridge |
| Process and argv exposure | Process argv and container configuration are host/operator-visible. They may carry non-secret Suricata options but no tokens, credentials, payloads, host-private paths, or participant data. If a command is sensitive, use the existing redacted command contract rather than hiding it in an environment variable |
| Checksum and packet parsing | Treat packet visibility and checksum acceptance as separate observations. Prove both directions of the same flow, invalid-checksum counters/posture, TCP stream construction, and HTTP transaction output before evaluating the rule |
| Readiness | Model staged observations: process alive; capture attached; representative packets visible; stream/application parsing effective; expected alert emitted; required downstream delivery complete. The declared readiness threshold is the last stage the scenario depends on, not merely the first |
| Evidence and persistence | Keep raw capture/log artifacts under the RAES sensitivity, redaction, integrity, retention, and loss contracts. `suricata_logs` is a delivery/persistence route, not proof. Record stable summaries, checksums/references, correlation ids, and explicit absent/partial/lost outcomes instead of embedding packet bodies |
| Logging and error envelopes | Reuse RAES/LilRAE stable diagnostic and evidence vocabularies. Do not expose raw packets, HTTP bodies, environment dumps, container inspect output, host interface names, absolute paths, or exception text in portable or participant-facing errors. This repository must not add another exception hierarchy |

This change introduces no authentication or secret input. The relevant security
surface is elevated packet observation: its least-privilege scope, namespace and
host-network exposure, evidence sensitivity, and safe error/log projection must
be reviewed even though the eventual checksum option itself is non-secret.

## Extensibility seam and proof boundary

The extensibility seam is one backend-neutral authored observation/detection
requirement joined to one admitted backend capture-mechanism disclosure. A
future non-Docker backend, inline sensor, mirrored bridge, namespace-sharing
adapter, or offload-safe capture implementation must vary behind that seam. It
must not require another TechVault SDL field, fork the expected detection, or
reintroduce post-start fixups. If process arguments legitimately vary, use a
narrow field-level realization scope rather than opening the whole node or
scenario.

Pack tests can prove closed typed authoring, sensor/engine/process/config
consistency, exact rule-source binding, evidence-reference joins, and pack byte
identity. They cannot prove Linux bridge visibility, veth checksum behavior,
HTTP parsing, alert emission, or Wazuh ingestion.

LilRAE integration evidence must start from a clean admitted realization and
exercise a marked participant-equivalent Kali-to-webapp HTTP flow. It must cover
checksum-offload conditions, bidirectional packet visibility, HTTP flow and
transaction output, one stable TechVault detection supplied by #283, and the
required downstream outcome. Negative cases must include a healthy Suricata
process with an ineffective observation point and an observation point with
checksum rejection; both must be rejected at admission when knowable or reported
not ready/unsatisfied, never passed as effective detection. The evidence must
also prove that no entrypoint, namespace, interface, offload setting, rule, or
container was mutated after start.

## Non-goals and rejected shortcuts

- Do not preselect `checksum-validation=no`, `--pcap`, AF_PACKET, host networking,
  namespace sharing, bridge mirroring, or another backend mechanism without the
  complete live path evidence.
- Do not treat Docker network membership, `capture_interfaces: [any]`, packet
  count, EVE file existence, stats output, container health, or process uptime as
  packet-path or detection proof.
- Do not conflate the webapp's direct rsyslog/Wazuh detections (302010/302011)
  with the Suricata-to-Wazuh path. They are independent defensive signals and
  the direct path can mask this defect.
- Do not claim `af_packet` while launching pcap mode, or declare a monitored
  network that the admitted mechanism cannot observe.
- Do not use host-to-proxy traffic as a substitute for the participant-equivalent
  Kali-to-webapp path.
- Do not add Docker/veth/offload mechanics to portable SDL, pack metadata,
  compatibility schemas, the generic Suricata kit, or detection content.
- Do not duplicate RAES network-sensor, detection-engine, process, realization,
  readiness, evidence, diagnostic, or exception contracts in this repository.
- Do not preserve an undeclared post-start command, container, interface,
  offload, or rule mutation as a compatibility path.
- Do not mark TechVault `golden`; issue #237 still owns complete participant
  proof and the golden-readiness evidence.
- Do not encode downstream catalog or deployment vocabulary into canonical pack
  terminology.

No new ADR is required. ADR 0009, ADR 0036, and the public
[ownership boundary](../public/ownership-boundary.md) already decide the
repository boundary. Issue #284 needs a TechVault contract correction coordinated
with #283's detection content and LilRAE/APTL's admitted-plan, Docker-network,
capture, readiness, and realization-evidence authorities.
