# AI Escape Lab architecture preflight

Issue #422 established the full upstream campaign in a portable pack, with a
GCP reference deployment through Shifter. Issue #426 qualifies its golden image
without deploying through Shifter. This note fixes ownership and safety
guardrails; it does not specify implementation steps.

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

The pack now supplies the GCP Packer recipe, installer, offline Compose runtime,
participant-entry helpers, readiness probes, and Shifter upload projection.
These are the reference implementation to reuse. The compatibility schema
already accepts a provider string and build/test/walkthrough references; no new
provider enum or deployment schema is needed. The normative
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
| Author/release workflow: `content_ci.py`, `release.py`, `.github/workflows/ci.yml`, `.ground-control.yaml`, `AGENTS.md` | Reuse the existing validator/test roots and hosted-pack gates, plus unittest patterns in `tests/test_ai_escape_lab_pack.py`, `tests/test_release.py`, and `tests/test_distribution_contents.py`. Ordinary static CI must not start Docker, call models/clouds, retrieve public packages, or attempt exploits. Live rehearsal is explicit operator work; auto-discovered tests cannot silently launch it. `pyproject.toml` already includes this pack in wheel/sdist, so every added pack file is publicly distributed regardless of its runtime audience. Release-please owns project version and changelog. |

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
not live containment or playability. Full event qualification under #422 requires
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
environment-name conventions, or a successful static check. Keep credentials
and unrelated tenant identifiers out of canonical docs and pack artifacts.

## Issue #426: isolated golden-image qualification

The issue is the authoritative contract; retain `requirement: null`. Its project
and dedicated image-build network/subnet are operation inputs, not portable SDL
or shared-tool defaults. Builds must resolve and verify those exact resources,
including subnet ownership and region/zone agreement, before creating anything.
Keep the internal-address/IAP Packer path. No fallback to a default network,
external address, ambient project, or default service account is acceptable.
Dedicated build infrastructure alone does not prove QA workload isolation:
confirm the QA VM's approved network and external containment before startup.

Allowed implementation effects are pack-local fixes, isolated build/QA resources,
the final custom image, bounded evidence, and a PR. Tenant inspection is read-only.
The runbook's image registration, pack upload/install, CTFd import, range launch,
twelve-seat rehearsal, tenant IAM/quota changes, and optional-gateway selection
are **later manual canary work**, not executable steps for #426. If an existing
cloud prerequisite is missing, report it; do not alter the live tenant to pass QA.
Cleanup targets only resources created for this qualification, with ownership
recorded explicitly; never delete by a broad tenant prefix.

### Proof boundaries

Candidate QA must use a fresh VM and the forced browser-SSH `participant` account
through `participant-shell.sh` and `ai-escape-enter`, including PTY/reconnect
behavior. Management `docker exec` may diagnose failures but cannot count as
participant proof. The installer configures that account's SSH/sudo policy but
does not create the account or provision its key. QA must document the supported
account/bootstrap convention and its effective username, groups, key source,
and policy; do not bake a reusable QA key or give the participant admin IAM.
[GCE browser SSH](https://docs.cloud.google.com/compute/docs/connect/ssh-in-browser)
chooses usernames according to metadata-key or OS Login configuration, so a
default console login is not evidence that `Match User participant` was applied.
If the exact Shifter browser transport cannot be exercised without a forbidden
tenant operation, record that acceptance gap explicitly. An isolated browser
attachment can prove the image-side entry contract, not Shifter session authz.

The documented seven-challenge happy path is human-supervised participant work.
Compare each recovered flag with the existing CTFd export locally, in private,
using `ctfd/export_shifter_challenge_pack.py`; record challenge id and match
result, not flag values. Export agreement is not a claim of live CTFd acceptance.
Preserve the existing placements, challenges, hints, and walkthrough as the
coupled content authority; no second answer list or automated exploit runner.

The final image comes from clean committed build inputs after fixes, never from
the exercised QA disk or a patched live container. A second fresh VM must pass
runtime readiness and participant smoke against the exact final image. Candidate
campaign proof transfers only when the effective build/runtime/fixture inputs
agree with the final bake; a functional change invalidates that proof. No image
family or tag is an acceptance identity. An accepted golden *image* does not
justify `pack.yaml.status: golden`, a supported Shifter profile, or checked
tenant/rehearsal items while those broader claims remain unproven. Keep the source
golden checklist unchecked and document completed and deferred proof separately.

### Existing seams and unresolved gates

| Layer / incumbent | Required guardrail and current gotcha |
| --- | --- |
| Build config: `build/gcp/build-image.sh`, `ai-escape-lab.pkr.hcl` | Reuse the entrypoint and native Packer validation. Its current shape checks do not prove project/VPC/subnet policy, and its service account is optional. Keep deployment coordinates, image version and sizing in the Packer/profile inputs, not SDL copies or new recipes. Separate caller build authority, build-VM identity, and predict-only QA identity; neither broad builder privileges nor the build VM's `userinfo.email` OAuth scope establishes runtime Vertex authorization. |
| Supply chain: source/base/Claude locks, `prepare-source.py`, `install.sh` | Verify exact source checksum, safe archive admission, architecture, pinned base digests and Claude integrity. Bound download bytes and archive members/expanded bytes as well as time; post-download checksums alone do not limit resource use. The base-image lock and script constants currently duplicate pins; reconcile them rather than maintain another lock. Record actual Ubuntu image, Packer/plugin, Docker/Compose and OS/language dependency versions: plugin ranges and apt/pip resolution mean existing pins do not establish bit-reproducible rebuilds. Preserve deliberate challenge weaknesses; host/build/auth dependencies still need ordinary security review. |
| Effective runtime config: `start-lab.sh`, Compose and RAES parser | Use Compose's native merged/interpolated config gate and pinned RAES validation, not a local schema. Isolate interpolation from ambient `.env`/environment and validate bindings before writing root-only `/run/ai-escape-lab/agent.env`. Model region must drive the env file and endpoint hosts together; Compose's fallback is currently `us-central1` while startup uses `us-east5`. If SDL env bindings change, reuse RAES credential classifications and literal/`value_from` exclusivity described above. |
| SSH/privilege policy: installer, entry helpers, OpenSSH/sudo | Check effective per-user SSH config as well as `sshd -t` and `visudo`. The helper's exact argument/target allowlist is the safety gate behind the wildcard sudo rule: keep it root-owned and reject arbitrary commands/targets. Exclude host groups, extra sudo grants, writable host startup files, injected environment, noninteractive subsystems and all forwarding forms. `ForceCommand` alone does not disable agent or Unix-socket forwarding; see [OpenSSH](https://man.openbsd.org/sshd_config#ForceCommand). Root inside the sandbox is intentional, not host root. |
| Network/metadata policy: `firewall.sh`, systemd ordering, scoped responder and GCP rules | Enforce before workloads and after reboot/Docker restart, with external containment if the guest is compromised. Cover every challenge subnet, Docker INPUT/FORWARD/NAT paths, host gateway, IPv6/DNS, peers and control plane. The responder binds `0.0.0.0:988`; its header/path allowlist is not caller authentication. Prove it is unreachable from the VPC/management interface and unintended containers. Preserve exact resource/query denial, bounded upstream reads/timeouts and body-free failures; constrain connection concurrency so a stalled client cannot exhaust the host. Private Google VIP access is not a model or API permission allowlist. |
| Model path: scoped responder, `agent.env`, `probe-agent.sh` | Require an actual Vertex `claude-sonnet-4-6` operation from the participant surface; no API-key, different provider/model, or cached response fallback. The [official model contract](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/partner-models/claude/sonnet-4-6) lists that id; deployment enablement and quota still need live proof. Keep `AI_ESCAPE_MODEL_REGION` as the existing seam; any model seam belongs alongside the existing runtime env writer, with #426 fixed to Sonnet 4.6. The configured Haiku auxiliary path is a separate dependency, not Sonnet evidence. Check effective IAM, OAuth scopes, model permissions and spend bounds; [alerts-only budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets) do not cap spending. Retain the direct token replay risk without adding a pack credential gateway. |
| Readiness/observability: `readiness.sh/json`, `probe-agent.sh`, systemd and `/run/.../ready` | Bake mode skips model calls; running containers and a non-empty model response alone do not prove campaign playability or the selected model. Preserve separate bake/runtime gates, finite deadlines, failure exit status and marker ordering. Report bounded service/phase/status/timing, not raw Claude JSON, token responses, env dumps, flags, container inspect dumps or parser tracebacks. Use existing `Diagnostic`/`ValidationResult` and `PackDigestError` for shared-tool failures; do not invent another exception/logging framework. |
| Persistence/image capture: `install.sh`, `stop-lab.sh`, image manifest and GCE guest lifecycle | Keep all eleven local images and fixture inputs, with runtime build/pull disabled. Reject missing or mismatched local image identities rather than repair from a registry. Removal of volumes is only part of pristine capture: exclude writable containers, anonymous database state, uploaded data, agent sessions, shell histories, logs, credentials, build/QA authorized keys and stale readiness. Confirm fresh machine/SSH host identity and normal guest bootstrap on the next VM. Quiesce writes before capture ([GCE guidance](https://docs.cloud.google.com/compute/docs/images/create-custom#prepare_your_vm_for_an_image)); replacement, not restart, proves a fresh baseline. |

### Evidence, packaging and workflow

Reuse `/opt/ai-escape-lab/image-manifest.json` for image component facts and
`derive_pack_content_manifest` / `validate_pack_content_manifest` for pack byte
identity. The existing image manifest records local image ids, upstream revision
and Claude lock, not the full build provenance. The bounded report must bind the
build source revision/input checksums, actual resolved dependencies, exact GCE
image name and resource id/creation time, candidate and final QA VM identities,
readiness/participant/model outcomes, seven private comparisons, residual risks,
and cleanup. A uniquely named image must not be replaced behind the recorded
reference. Link final smoke to the final image, not candidate evidence alone.
Do not introduce a generic QA manifest, session repository, controller or cloud
DTO service; the existing component manifest and operator report suffice.

Keep sanitized image/build/QA results and later manual canary guidance in the
pack's operator docs. Raw evidence, private exports and credentials stay outside
the pack. Audience boundaries and provenance classification are not secrecy:
`pyproject.toml` and `tests/test_distribution_contents.py` ship every pack file
in wheel/sdist. Apply the existing scrub policy to tenant identifiers; retain
the exact final image reference required by the issue only in its pack-specific
operator record, not canonical docs, schemas or defaults. Reconcile provenance
and compatibility boundaries for new report files and regenerate associated
artifacts after all pack edits. Avoid embedding the final set digest in a report
that is itself included in that set; report build-input identity there and bind
the final pack digest in external release evidence using existing tooling.

Reuse `tests/test_ai_escape_lab_pack.py`, `build/tests/test_build.py`,
`validation/tests/test_pack.py` and `ctfd/tests/test_export.py` for meaningful
failure/shape/identity checks. `content_ci.TEST_DIRS` already discovers the
pack-local suites under its bounded process runner. Native Packer/Compose/SSH
checks and explicit live QA complement those tests; source-text assertions alone
do not prove policy enforcement. Keep cloud/model/browser work out of automatic
test discovery and ordinary CI. Run all `AGENTS.md` verification commands with
the editable package and existing `.ground-control.yaml` policy gates. Submit
fixes/evidence through the existing Conventional Commit PR path; no hand-edited
project version/changelog, alternate publish workflow or automatic merge.

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
