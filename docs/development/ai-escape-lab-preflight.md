# AI Escape Lab architecture preflight

Issue #422 calls for the full upstream campaign in a portable pack, with a GCP
reference deployment through Shifter. This note fixes ownership and safety
guardrails before implementation; it does not specify implementation steps.

## Authority and scope

The pack belongs under `packs/ai-escape-lab/`, following
[ADR 0036](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md).
Use `requirement: null`; issue #422 is the contract, not a new requirement UID.
The pinned `raes==6.0.1` in `pyproject.toml` owns SDL shapes and semantics.
Preserve the eleven challenge services, five network boundaries, seven flags,
twelve progressive hints, and intended participant path. The simulated
Kubernetes, mesh, source-control, and credential services are scenario content;
they do not require a real cluster, VPN, cloud identity, or external target.

| Concern | Authority and carrier |
| --- | --- |
| Scenario meaning | RAES SDL: nodes, services, infrastructure links/dependencies, participant behavior, objectives/conditions, content placement, runtime facts, and evidence requirements where needed. No local semantic schema or invented readiness/scoring/lifecycle field. |
| Pack identity and exposure | `pack.yaml`, provenance ledger, existing compatibility schema, and RAES associated-artifact identity. Compatibility runtime profiles index build/test/walkthrough files; delivery bundles select audience content only. |
| Reference deployment | Pack-local `build/` material may carry the pinned Compose source and minimal deployment adaptations. It is a reference implementation, not an alternate scenario authority or generic runtime engine. |
| Live seat lifecycle | Shifter owns tenant admission, GCP provisioning, terminal authorization, model credential issuance, isolation enforcement, readiness readback, reset, and runtime evidence storage. No Shifter controller, session database, credential store, or cloud DTO belongs in shared pack tooling. |

The repository has no Shifter/GCP deployment implementation to reuse. Its
compatibility schema already accepts a provider string and build/test/walkthrough
references; no new provider enum or deployment schema is needed. The normative
`resources/contract/pack-layout.md` still describes the reference triangle as
AWS-only, while compatibility profiles and golden checklists admit declared
infrastructure. The GCP reference requires that provider wording to be reconciled
explicitly, preserving the coupled triangle and participant-proof bar. Do not
silently label GCP as AWS or add an AWS deployment just to satisfy that prose.
The dedicated-network rule in `docs/public/golden-readiness.md` still applies:
use dedicated lab infrastructure, never assume a shared/default tenant network
is safe. Seat isolation needs additional enforcement within that boundary.

## Cross-cutting gates and reuse

| Layer / canonical incumbent | Required outcome for this design |
| --- | --- |
| Pack input: `validation.validate_pack`, `PackValidationLimits`, `_pack_fs` | Reuse bounded strict YAML/JSON loading, duplicate-key rejection, descriptor-anchored containment, regular-file inventory, and symlink/hardlink/special-file rejection. Vendor only admitted source files, without `.git`, caches, links, runtime outputs, or image archives that exceed pack budgets. Consumer validation must never execute the lab or acquire dependencies. |
| Semantic/config shape: public RAES parser through shared validation and `content_ci.py` | Use closed RAES models and validate the actual source. Preserve unique ids/environment names, service/network references, dependencies, mount ownership, generated-output references, and container-security consistency. Compose membership, effective endpoints and SDL must agree; startup order alone proves neither connectivity nor readiness. Do not copy TechVault's pack-specific realization prohibitions into a universal rule. |
| Reference config: Docker Compose native config validation and runtime bindings | Validate the fully merged/interpolated mapping with the declared Compose version before deployment. Required inputs fail closed; no hidden working-directory `.env`, ambient credentials, unresolved substitution, unexpected host mount, public port, or extra network is acceptable. Keep effective config output secret-free and do not write or log credential-expanded YAML. Reuse Compose's parser rather than inventing another Compose schema. |
| Environment/secret shapes: RAES `RuntimeEnvironmentVariable` | Intentional fictional challenge credentials can use `secret_fixture`; real operator/model credentials cannot. `operator_secret`/`redacted` omit raw values. A generated `value_from` is exclusive with a literal value and cannot be classified `operator_secret` in the current pin. Use generated-output references only for actual RAES-generated material, never as an invented session-token carrier. |
| Content safety: `provenance.schema.yaml`, shared safety flags and review gates | Pin upstream to an immutable commit, retain the MIT notice and attribution, record adaptations, and review all copied files for real credentials/targets/sensitive data. Embedded fictional keys remain deliberate scenario fixtures, with no authority beyond one lab. Supply-chain updates must not accidentally patch away intentional challenge weaknesses. |
| Audience/release boundary: `pack-compatibility.schema.yaml`, `content_ci` visibility scan, `release.BOUNDARY_TIERS` | Separate deployable source, fixture values/keys, answers, and walkthroughs from participant handouts. Declare disjoint roots and reuse the canonical redacted token scan and release smoke checks. A clean token scan does not prove absence of answers or secrets. Participant shell access to planted flags after the intended exploit is distinct from release exposure of their source. |
| Artifact/distribution identity: `digest.py`, `component_boundary.py`, `publication.py`, `sbom.py`, `verify.py`, `distribution.py` | Derive the final associated-artifact manifest with `derive_pack_content_manifest`, validate it with `validate_pack_content_manifest`, and resolve selected bytes through `resolve_pack_artifact`. Reuse component inventories/publication supply and standard SBOM/provenance for release claims. Pack-local build recipes may pin exact external inputs, but must not introduce a second generic trust model or accept an unverified download. Credentials and signed URLs do not belong in publication availability or identity. Immutable source/image identity is distinct from a changeable registry location. |
| Terminal authentication/authorization: Shifter runtime boundary | Authorize each browser HTTP/WebSocket attachment to the active seat/session, including reconnects; check origins and use TLS. The browser reaches a shell inside `eval-sandbox`, with the coding agent in that same boundary. A trusted attach helper may select only that seat's declared target, not arbitrary containers or host commands. No Docker socket, privileged terminal, shared host namespace, or operator shell is participant-accessible. |
| Model authorization: existing Shifter keyless-direct boundary | Use the platform's default GCP Workload Identity path: no provider key is created or baked, and the range identity has only the exact Vertex prediction permission required by the lab. A root-equivalent participant can read and copy its short-lived OAuth token; it can remain usable off-seat until expiry. The direct path therefore requires project-level model allowlisting, quota/budget bounds, and explicit acceptance of that replay window. A deployment requiring immediate revocation or per-seat spend/rate enforcement must use Shifter's qualified optional gateway instead. Do not add a pack-specific relay or auth framework. |
| OS exposure and network policy: GCP, host firewall, Docker, proxy | Enforce isolation before starting vulnerable workloads, across every reachable challenge container and indirect SSRF/proxy path. Cover host gateways, metadata by IPv4/IPv6/DNS and HTTP/HTTPS, tenant services, other seats, published ports, Docker forwarding/NAT, and IPv6. Avoid host networking, broad capabilities, host/PID mounts, shared volumes, and daemon sockets. Never put real secrets in argv, healthcheck text, image layers/build args, shell tracing/history, container inspection output, crash dumps, or raw diagnostics. Environment injection is not a confidentiality boundary against a compromised container. |
| Error/observation envelope: `Diagnostic`/`ValidationResult`, `PackDigestError`, author-CI bounded process runner | Preserve stable codes and bounded field/pack-relative locations; no raw parser exceptions, input bodies, absolute paths, environment dumps, credentials, flags, or model requests/responses in shared errors. Unexpected programming defects still fail. Reuse runtime readiness/logging rather than adding a pack logging subsystem. Log value-free service/seat correlation and failure categories; keep restricted runtime evidence outside pack identity and participant exports. |
| Persistence/reset: RAES content/volume/generated-artifact declarations plus runtime lifecycle | Every mutable layer, volume, upload, database, C2 store, terminal history, and agent workspace is disposable per seat. Replace the seat or restore all state from an immutable golden baseline; restarting containers with old volumes is not reset. Golden images contain no session capabilities or tenant credentials. Reset closes old terminal attachments, prevents new token minting from the destroyed seat, rotates the range identity, and repeats readiness before readmission. A token already copied from the direct keyless path may remain usable until its bounded expiry. |
| Author/release workflow: `content_ci.py`, `release.py`, `.github/workflows/ci.yml`, `.ground-control.yaml`, `AGENTS.md` | Reuse the existing validator/test roots and hosted-pack gates, plus unittest patterns in `tests/test_techvault_pack.py`, `tests/test_release.py`, and `tests/test_distribution_contents.py`. Ordinary static CI must not start Docker, call models/clouds, retrieve public packages, or attempt exploits. Live rehearsal is explicit operator work; auto-discovered tests cannot silently launch it. Publishing a hosted pack also requires deliberate wheel/sdist inclusion in `pyproject.toml`, currently limited to two existing packs. Release-please owns project version and changelog. |

Relevant existing kits include the inference API gateway, reverse-proxy gateway,
lab portal, and isolated analysis sandbox. They are declarative authoring content,
not deployed terminal/relay/isolation services. Reuse their RAES patterns when
applicable; importing them is not a substitute for preserving upstream topology
or proving the runtime boundary. If materialized, use `raes-pack-kit`, its
transactional writer/ownership ledger, and RAES's module lock. Do not fork those
workflows or compose kit parameters containing secrets or runtime endpoints.

## Containment, campaign fidelity, and proof

Treat every challenge service, including the rooted launch point and dataset
worker, as compromised. Use one disposable VM per seat as the GCP reference
isolation unit; Compose project names or bridges on a shared daemon do not
establish that boundary. The realizer must enforce denial outside the guest as
well as Docker/host policy, so guest compromise cannot disable cross-seat and
tenant protection. Challenge VMs carry no tenant/control-plane, storage, secret,
registry, or management authority. The one deliberate exception is the range
host's predict-only Vertex identity used by the coding agent. Any provisioning
identity remains outside the participant boundary.

Do not trust `internal: true` or a guest firewall label as acceptance evidence.
Docker's port publishing can bypass UFW filtering, and metadata is locally
reachable rather than ordinary Internet egress. Verify the effective firewall
backend and policies after startup/restart. The model exception must not attach
`eval-sandbox` to challenge networks that skip the first exploit, or grant
general egress to its shell. Terminal/proxy management must not become a second
route through the campaign. Allow only the exact authenticated model path and
needed terminal transport outside the isolated challenge graph.

Upstream's displayed topology uses `172.32` and `172.33` ranges, outside private
`172.16.0.0/12`. Inspect the pinned Compose and all hard-coded endpoints for
overlap with GCP, Docker, and operator networks. Reuse addresses only inside a
proven isolated namespace; if remapping is required, keep every endpoint,
embedded fixture, hint, test, and walkthrough consistent and record the minimal
adaptation. The simulated `internet-net` must never become public Internet.

Prebuild the complete image closure, including database, terminal, agent and any
support service, with exact platform/image digests and pinned build inputs.
Retain image/license provenance and component scope; source pinning alone does
not pin base images or downloaded dependencies. Preload verified images into a
credential-free golden VM. Startup must neither build nor pull; a missing or
mismatched image fails readiness instead of falling back to the network.
The local package mirror and exploit toolchain must work with outbound access
denied. Image scanning must distinguish intentional in-world vulnerabilities
from unnecessary vulnerabilities in the host, terminal, relay, and build chain.

The flag layer is coupled: seven placement rows with real SDL host ids, matching
challenge rows, and the reference `ctfd/` loader. This does not require deploying
a scoreboard for walk-up seats. Keep upstream `hint` and numbered hints 1–12
available in the sandbox without Internet. Avoid independent rewritten hint
copies that drift. Optional on-demand hints do not make this an `unguided` or
`agent-benchmark` bundle, whose exposure rules forbid next-step hints; use an
honest participant bundle only if a profile layer is needed. Do not add audience
variants merely because the agent is present.

Readiness requires the expected complete Compose graph, functional challenge
dependencies/fixtures, a browser attachment to the intended sandbox, and a
bounded authorized agent/model operation. Separate failed/partial startup and
unavailable model access from ready; set finite timeouts and retry transient
startup failures only. Probes must not retrieve flags, consume hints, execute
exploits, or mutate the baseline. Full campaign rehearsal is separate proof.

Static pack/release success proves committed contracts and export boundaries,
not live containment or playability. Golden status and issue acceptance require
participant-equivalent manual and automated proof of all seven flags and twelve
hints from fresh seats, negative checks against shortcut access, twelve
concurrent independent seats, offline challenge operation, rejected cross-seat/
control-plane access (including indirect pivots), bounded metadata exposure,
expired model-token rejection, and pristine reset with stale-session rejection.
For keyless-direct delivery, record that a copied unexpired token is replayable
and verify the exact predict-only IAM role plus project quota/budget controls; if
that risk is unacceptable, qualify the optional gateway before release. Record
actual VM CPU/RAM/disk, architecture, startup/resource observations, tenant quota
and relay capacity from that validation; do not invent sizing from container
count. Keep proof tied to the exact pack/image/reference-profile identity.

## Extensibility and non-goals

Stable RAES node/service ids are the join between portable content and the
reference mapping. The provider profile is the seam for another realizer.
Seat count (12 for acceptance), machine sizing, tenant coordinates, external
terminal endpoint, model selection/session limits, and image transport location
are validated runtime/profile inputs, not duplicated SDLs or hard-coded tenant
values. Image contents, topology, and campaign fixtures remain immutable for a
release. Do not invent a generic adapter registry to achieve this separation.

No campaign redesign, real Kubernetes deployment, real stolen credentials,
public target access, mandatory CTFd service, new kit library, local SDL parser,
exception hierarchy, scoring/oracle/telemetry schema, lifecycle manifest,
session persistence service, or generic Shifter orchestration belongs in this
change. Express missing portable semantics upstream in RAES and qualify missing
deployment capabilities in Shifter; never hide either gap in metadata, comments,
environment-name conventions, or a successful static check. Keep tenant-specific
identifiers and credentials out of canonical docs and pack artifacts.

## Evidence limits and references

This preflight initially inspected the current repository, its installed pinned
RAES models, and the public upstream overview. Implementation subsequently
admitted upstream commit `fcb25ec9874b0676706b9aca650f22efc90f711e`, retained
its license, and checked the exported SDL against the deployed Shifter RAES 3.5
contract. No live tenant capacity, sizing, isolation, model call, reset, or
deployment behavior is claimed here. Those claims require the separate golden
image and participant-equivalent qualification described above.
The overview and linked
timeline describe July 2026, while the issue says April; preserve source facts
in provenance without changing the issue's campaign requirements.

- [Upstream overview](https://github.com/an4kronism/ai-escape-room) — campaign,
  simulated services, hint entrypoint, and displayed topology; mutable reference,
  not an admitted source pin.
- [Intrusion timeline](https://huggingface.co/blog/agent-intrusion-technical-timeline)
  — background only, never a live target or runtime dependency.
- [GCP metadata security](https://docs.cloud.google.com/compute/docs/metadata/overview#metadata_security_considerations)
  — local metadata access and sensitive-value exposure.
- [Docker firewall behavior](https://docs.docker.com/engine/network/packet-filtering-firewalls/)
  — forwarding, firewall backend, and port-publication/UFW interaction.
