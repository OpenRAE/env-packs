# TechVault Kali capture and shell-access preflight

APTL is being renamed to LilRAE. They are the same runtime project across that
rename, not separate products, layers, or experiences. TechVault is only a
scenario pack. Historical repository paths and compatibility identifiers such
as `aptl` and `APTL_CAPTURE_CAPABILITY` retain their exact names below.

Issue #282 is not a wrapper-only defect. The current pack installs an SSH
`ForceCommand` that requires `APTL_CAPTURE_CAPABILITY`, but no authored or
realization contract produces and delivers that value. A clean realization is
therefore unsatisfiable, and changing the wrapper to continue unrecorded would
choose a different research policy without an authority for that choice.

No implementation should change fail/degrade behavior until the TechVault pack
author has expressed the intended experiment policy through RAES and LilRAE can
realize that contract. Security requirements constrain capability handling; they
do not choose the experiment's evidence policy. This note records the current
contract, its gaps, and the boundaries that constrain that decision. It is not
an implementation plan.

## Current end-to-end contract

| Concern | Current producer | Current consumer | Lifecycle | Required observation | Current gap |
| --- | --- | --- | --- | --- | --- |
| Kali SSH authorization | RAES `generated_artifacts.techvault-ssh-keys`; the producer retains the operator private key and places only `kali-authorized-keys` on Kali | Kali `sshd` | Regenerated with the generated-artifact lifecycle and installed before access | Authenticated SSH admission through the declared Kali service | The effective `ForceCommand`, `AcceptEnv`, and `Match User kali` policy is installed by inline bootstrap text rather than declared through RAES `runtime.ssh_servers` typed facts. |
| Run and session identity | Intended LilRAE session/control plane | Wrapper, capture client, and sidecar | One admitted run/session; immutable once capture admission starts | The same identifiers on session request, `session_accepted`, transcript frames, `session_finalized`, and evidence metadata | No declared producer/delivery contract exists. The wrapper invents `anon-*` fallbacks, which can hide missing identity and cannot satisfy a capability bound to the original identifiers. |
| Capture authorization | Intended LilRAE control plane | Capture sidecar, via the wrapper and capture client | Opaque, least-privilege, run/session-bound, short-lived, single-use, then expired/revoked | Sidecar acceptance or a safe rejection class; never the capability value | No issuer, delivery mechanism, expiry/replay lifecycle, or readiness probe is declared. `AcceptEnv APTL_CAPTURE_CAPABILITY` names a transport but does not create a producer. |
| Capture transport | Pack-owned `kali-capture-client`; LilRAE-owned capture sidecar | Sidecar protocol v2 | One owning connection from `session_start` through `session_end` | Exact run/session acknowledgement and finalization | Reachability `ping` proves only that a socket speaks the protocol. It does not prove authorization can be issued or that a session can be finalized. |
| Transcript evidence | LilRAE capture sidecar writes the `kali_captures` volume | LilRAE evidence persistence and RAES evidence consumers | Created per session, finalized once, retained for the run/study policy | A captured-evidence record, or an explicit missing/partial/loss disclosure | The SDL declares the volume but no Kali shell capture `evidence_requirement`. Shell success is therefore not evidence that capture occurred. |
| Participant readiness | Intended admitted-plan realizer and participant execution service | Participant-access/control-plane adapter | Evaluated before accepting new work and after material changes | Typed health/readiness/evidence readback | Node presence, dependency ordering, an active SSH service, and a successful `ping` do not prove end-to-end session capture readiness. |

The only complete path today is SSH key generation and placement. The capture
path has consumers but no capability or identity producer, and the evidence path
has storage but no authored evidence requirement or honest absence record.

## Authority and binding outcomes

The repository's existing ownership boundary remains controlling:

- RAES owns portable participant behavior, SSH runtime facts, evidence intent,
  observation boundaries, participant execution readiness, and experiment
  evidence/loss meaning.
- This repository owns the TechVault authoring choice and the exact pack bytes.
  It may express the chosen policy through existing RAES fields; it must not add
  a pack-local capture, capability, session, readiness, or evidence schema.
- LilRAE owns admitted-plan realization, session creation, runtime credential or
  capability issuance, delivery to its trusted sink, backend observation, and
  local evidence persistence.
- The sidecar owns validation of the concrete capture authorization presented
  for one run/session and the atomic finalization result.

Several outcomes are already binding regardless of the eventual fail/degrade
choice:

1. SSH authentication and capture authorization are different decisions. A
   capture capability must never become a general shell credential, and shell
   success must never be interpreted as capture authorization or evidence.
2. A capture record is complete only after the sidecar returns a matching
   `session_finalized`. Missing, rejected, interrupted, or partial capture must
   remain a distinct observed outcome with loss disclosure.
3. Capability material is runtime-private. Its value must not enter SDL,
   generated pack content, argv, logs, diagnostics, control-plane receipts, or
   portable evidence. A portable carrier may contain only a redacted secret
   reference or presence/absence posture when an existing RAES contract calls
   for one.
4. A clean admitted realization must be sufficient. LilRAE must not patch the
   wrapper, inject an undeclared component, or relax policy after realization.
5. Once a participant command has started, recovery must not execute it a
   second time. Command result and capture result remain separate terminal
   facts even if the selected policy later treats one as invalidating the run.

The fail/degrade outcome is **not yet binding in portable authoring**. The README
and wrapper currently say fail closed, but the RAES SDL has no Kali shell
capture evidence requirement and RAES 3.3 has no capture-to-shell admission
policy field. Conversely, `loss_disclosure: best_effort` or `required` describes
evidence-loss reporting; it does not authorize or deny participant access. The
implementation must not infer admission policy from either wording. If the
needed policy cannot be expressed by an existing RAES contract, it is a RAES
gap, not a reason to add a TechVault-only field. This is an SDL authoring and
runtime-realizability boundary; security review constrains only the concrete
capability mechanism once an evidence policy has been authored.

## Canonical contracts to reuse

The pinned `raes==3.3.0` corpus already supplies the relevant cross-cutting
surfaces:

- `RuntimeSshServer`, `SshMatchRule`, and `SshForcedCommand` are the canonical
  typed, participant-observable SSH policy. They carry `AcceptEnv` names only,
  never per-session values, raw `sshd_config`, or transcripts. A forced command
  containing secret/session arguments must use the redacted form.
- SDL `EvidenceRequirement` is the authored capture-intent carrier. It keeps
  source, scope, window/boundary, channel, sensitivity, redaction, integrity,
  retention, and loss disclosure together. It is not proof that capture ran.
- `ExperimentCaptureSpecModel`, `ExperimentEvidenceRecordModel`, and
  `ExperimentRawEvidenceContentModel` separate executable capture requirements
  from captured evidence and require disclosure for redacted, withheld, or
  lossy output.
- `ParticipantExecutionServiceStateModel` is the readiness/health/evidence
  readback. `accepting_new_work=true` requires `readiness=ready`; a healthy
  container is not an equivalent signal.
- The runtime-fact contracts already define secret-reference values, protected
  sinks, authority references, absence dispositions, and value-free redacted
  projections. They may be used only if RAES designates the session input as a
  portable runtime fact; otherwise LilRAE's existing credential/session boundary
  remains the owner.
- The existing protocol-v2 client already provides bounded JSON-line responses,
  exact version/type/run/session acknowledgement checks, connection/send
  timeouts, single-connection ordering, FIFO draining after failure, and
  removal of the capability from its Python environment. Extend this contract
  rather than creating another capture protocol or exception hierarchy.

Within this repository, changes continue through `raes.parse_sdl_file` via the
shared `validate_pack()`/author-CI authority, the TechVault contract tests,
`validate_pack_content_manifest()`, and `resolve_pack_artifact()`. Static
diagnostics remain bounded, payload-free `ValidationResult` diagnostics;
content identity failures remain `PackDigestError`. Associated-artifact bytes,
sizes, exact-artifact digests, and set identity are derived from the final bytes,
not hand-edited independently. `refresh_pack_sdl_binding.py` covers an SDL-only
change; a wrapper/client change requires the full manifest-derivation authority,
not a partial checksum patch.

## Security and observation gates

Any intended design crosses all of these layers:

| Layer | Required guardrail |
| --- | --- |
| RAES shape and semantic validation | Use the pinned typed SSH/evidence/readiness carriers. Do not introduce `APTL_*` compatibility identifiers as semantic fields, a duplicate schema, or backend container/process detail in SDL. |
| Pack validation and author CI | Preserve the shared static snapshot, anti-extension boundary, visibility/leak scan, and bounded deterministic diagnostics. No raw upstream exception or authored value belongs in an error. |
| Pack artifact identity | Resolve wrapper/client bytes through the existing exact associated-artifact authority. The SDL digest, artifact checksums/sizes, exact source digest, and set digest must all describe the same final bytes. |
| Control-plane authentication and authorization | LilRAE authenticates the session creator, authorizes capture issuance for the exact run/session/audience, and records safe allow/deny audit metadata. Possession of the SSH key alone must not mint broader capture authority. |
| Capability shape and lifecycle | The issuer and sidecar agree on scope, expiry, single use, replay rejection, and identifier binding. Invalid, missing, expired, replayed, and mismatched inputs remain distinct safe outcome codes. |
| SSH and OS exposure | `AcceptEnv` is client-supplied transport, not a trusted issuer. Capability material must not be placed in command arguments or inherited by the participant command. The selected delivery mechanism must account for `/proc`, same-UID/sudo inspection, child inheritance, crash dumps, and shell tracing before treating an environment handoff as confidential. |
| Sidecar protocol and parser | Keep protocol versioning, bounded frames, strict acknowledgement shape, timeouts, one owning connection, and fail-closed authorization. Never log the capability or echo it in an error frame. |
| Readiness | Probe issuance plus delivery plus sidecar authorization/finalization capability before admitting work when the authored policy requires it. A socket `ping`, container health, or SSH login alone is insufficient. |
| Evidence boundary | Emit finalized evidence only after matching finalization. Emit an explicit absent/rejected/partial/lost record when required; do not infer evidence from command exit, readiness, file presence, or shell success. Portable records carry references/checksums and safe loss descriptions, not transcripts, tokens, private paths, or backend exceptions. |
| Logging and error envelopes | Reuse LilRAE's bounded error and audit vocabulary. Current client warnings interpolate raw exception text and therefore are not suitable as portable or participant-facing evidence. Log stable classes and correlation identifiers only. |

The extensibility seam is one backend-neutral, RAES-owned capture-admission
posture joined to an authored evidence requirement and participant execution
scope. Reasonable future variations—another shell transport, another capture
collector, or best-effort versus admission-required capture—must change that
policy/binding, not fork the wrapper or add another environment variable. LilRAE's
concrete token, socket, credential broker, or file-descriptor handoff stays
behind its participant-access adapter.

## Proof boundary

Pack-local tests may prove typed authoring, exact artifact resolution, wrapper
and client behavior, identifier/acknowledgement validation, capability
non-inheritance, command execution exactly once, and bounded diagnostics. They
cannot prove that LilRAE issues a capability or persists evidence.

LilRAE integration tests must start from a clean admitted pack and cover an
authorized captured command, missing/invalid/expired/replayed/mismatched
authorization, readiness before participant admission, interactive and
non-interactive command execution and exit status, mid-stream failure, matching
finalization, and explicit absent/partial evidence. The test must also assert no
post-realization wrapper mutation and no capability value in argv, logs,
receipts, inspectable participant environment, or portable evidence.

## Non-goals and rejected shortcuts

- Do not decide that access always fails or always degrades inside the wrapper.
- Do not treat capture authorization as shell authorization, or shell success as
  evidence success.
- Do not add `APTL_CAPTURE_CAPABILITY` as an SDL runtime environment value or a
  generated artifact; that would move a runtime credential into portable
  content without creating a safe issuer.
- Do not use the operator SSH key, a long-lived shared secret, or a predictable
  run/session value as the capture capability.
- Do not duplicate RAES SSH, evidence, runtime-fact, readiness, observation, or
  error models in this repository.
- Do not make the Kali workload a writer of `kali_captures`, weaken sidecar
  ownership, or expose capture storage to the sudo-capable participant.
- Do not accept `ping`, container health, file existence, shell exit, or a
  warning line as evidence of authorized finalized capture.
- Do not preserve LilRAE's post-realization wrapper patch as a compatibility path.
- Do not encode downstream catalog or deployment vocabulary into the canonical
  pack contract.

No new ADR is required. ADR 0009, ADR 0036, and the public
[ownership boundary](../public/ownership-boundary.md) already decide repository
authority. This issue needs a TechVault contract decision coordinated with the
RAES participant/capture authority and LilRAE's session, SSH-environment, capture,
and evidence-boundary records before implementation begins.
