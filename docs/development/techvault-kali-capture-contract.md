# TechVault Kali capture and access contract preflight

- Status: Preflight boundary record for issue 282
- Scope: architecture and acceptance guardrails, not an implementation plan

## Decision boundary

TechVault is a first-party RAES environment pack. It may author RAES scenario
intent and ship exact content bytes, but it does not own a second participant,
capture, credential, readiness, or evidence model. RAES owns those meanings; a
runtime consumer owns admission, realization, secret resolution, observation,
and evidence persistence.

The current pack is internally incomplete. Its SSH `ForceCommand` requires a
per-session capture authorization value, while no declared producer or delivery
path exists. The wrapper also starts the participant command without a
synchronous proof that `session_accepted` was received. Patching the wrapper
after validating and realizing the pack is not an admissible completion path:
it changes digest-bound participant and observation behavior.

The existing fail-closed text is the conservative admission posture for this
pack, but it is not permission to invent a pack-local semantic field. Before a
participant command starts, the runtime must either satisfy the admitted RAES
capture requirement and obtain positive capture admission, or deny the command.
A future degraded-capture posture is a different authored research policy. It
may allow execution only when RAES can express that policy and the admitted
runtime can report the resulting limitation and loss explicitly. If the pinned
RAES contract cannot express the required distinction, the gap belongs upstream
in RAES.

## End-to-end ownership

| Input or result | Producer | Consumer | Lifecycle | Required observation |
| --- | --- | --- | --- | --- |
| Participant SSH access intent | Scenario owner, using RAES `Agent.interactive_access` | RAES validator and runtime planner | Pack version | Resolved participant, VM, channel, and optional starting account; never a host locator or credential |
| Participant-observable SSH policy | Scenario owner, using `Node.runtime.ssh_servers` | Runtime realizer and SSH policy readback | Pack version, then realized generation | Typed `Match`, name-only `AcceptEnv`, and `ForceCommand`; `sshd -t` plus runtime readback |
| Run and session identity | Runtime control plane | SSH admission path, capture service, and evidence records | One admitted SSH attempt/session | Exact correlation references at admission and finalization; missing or invalid identity is rejected, never replaced with an anonymous id |
| Capture admission proof, including a credential if the runtime design uses one | Runtime control plane or its trusted secret broker | Capture service verifier | Minted after run/session admission; short-lived, audience-bound, single-use, atomically consumed, then expired | Safe disposition and correlation references only; never the raw proof |
| Capture readiness | Runtime realization and capture service | Participant admission gate | Continuously observed, generation-bound | Issuance/validation path, protocol compatibility, evidence sink writability, SSH policy, and finalization path—not a connectivity-only ping |
| PTY stream | Forced-command capture client | Capture service writer | One admitted connection | Positive start acknowledgement, bounded ordered chunks, and positive finalization or an explicit interruption |
| Captured artifact and capture loss | Runtime capture/evidence subsystem | Evaluator and authorized evidence consumers | Run/study retention policy | RAES capture/evidence records, checksums/provenance, sensitivity/redaction, and mandatory loss disclosure |
| Participant command outcome | Participant execution runtime | Participant caller and run record | One command/session | Command start and exit remain distinct from capture admission and evidence completeness |

The capture admission proof is deliberately mechanism-neutral here. A bearer
token, protected local broker, inherited descriptor, or another runtime-owned
mechanism must satisfy the same lifecycle and disclosure properties. The pack,
its generated-artifact declarations, and its compatibility manifest do not
issue this per-session proof. A client-supplied SSH environment value is
untrusted input; allowing its name through `AcceptEnv` does not authenticate it.

## Canonical carriers and validators

The implementation must compose these existing authorities:

- `validate_pack()` and the exactly pinned public RAES parser are the single
  pack/SDL validation path. No copied SDL schema, alternate parser, or capture
  validator belongs in this repository.
- RAES `Agent.interactive_access` owns portable participant-to-VM SSH intent.
  It does not carry ports, credentials, sessions, or realization claims.
- RAES `Node.runtime.ssh_servers` owns observable `sshd` policy. Its
  `accept_env` field carries names only, its match rules join to local identity,
  and its forced-command model enforces absolute-path or redacted-command shape.
- RAES `evidence_requirements` owns authored capture intent, including apparatus
  sources, participant output, sensitivity, integrity, retention, redaction,
  and loss disclosure. An authored requirement is not captured evidence.
- RAES experiment capture, apparatus-context, and evidence-record contracts own
  admitted capture, apparatus identity, realized evidence, and limitations.
  `ParticipantExecutionServiceState` is the existing evidence-backed readiness
  carrier for participant execution scopes; it applies to SSH only if the
  admitted runtime actually places this access path in such a scope. It is not a
  generic shell-readiness schema.
- The existing associated-artifact manifest, resolver, and digest checks bind
  the wrapper, client, SDL, and other pack bytes. A realization must use those
  bytes unchanged.
- The existing `kali_captures` volume boundary keeps participant and writer
  access separate. It is storage intent, not proof that a complete transcript
  exists.
- The current single-connection, bounded-frame, acknowledged capture-client
  protocol and its drain-on-stream-failure behavior are useful mechanics to
  preserve. They do not replace synchronous admission, mutual endpoint trust,
  or RAES evidence records.
- Static failures continue through bounded `Diagnostic`/`ValidationResult`
  records. Runtime admission and capture failures use the runtime's canonical
  redacted error and audit envelopes; this repository must not add an exception
  hierarchy or runtime log format.

RAES run-local secret-reference and runtime-fact contracts are not a generic
SSH credential store: their current sink is a compiled participant action
input. They may be reused only if the upstream contract actually admits this
SSH-session use, not by relabeling the capture proof as an action argument.
Likewise, a capture authorization proof is not a Linux `CAP_*` capability and
not a participant semantic capability.

## Security and observation guardrails

Every path must pass all of the following boundaries:

1. **SDL and pack shape.** Strict bounded YAML loading, RAES model validation,
   reference resolution, and exact artifact inventory must succeed. RAES
   redaction classifications reject a raw value on a redacted/operator-secret
   field; pack provenance/materialization checks and publication/release leak
   scans protect their narrower surfaces. Those controls do not make it safe to
   misclassify a proof as plain scenario data, so the no-live-proof invariant
   needs an explicit regression check across SDL, metadata, generated content,
   compatibility data, and the associated-artifact manifest.
2. **SSH policy.** Model the effective `AcceptEnv`/`Match`/`ForceCommand` policy
   through `runtime.ssh_servers`, validate the native config with `sshd -t`, and
   observe the realized policy. Do not infer policy from an inline bootstrap
   script alone.
3. **Admission.** Validate bounded run/session correlation and atomically consume
   a proof bound to that exact attempt before `SSH_ORIGINAL_COMMAND` or a login
   shell can run. Reachability (`ping`) is not admission. Missing, malformed,
   expired, replayed, wrong-audience, or mismatched proof is a denial under the
   current fail-closed posture.
4. **Secret transport.** Never place raw proof material in argv, command text,
   durable environment configuration, files, volumes, logs, exception text,
   portable evidence, or participant output. If a transient process environment
   remains the selected runtime handoff, treat it as an untrusted bearer channel,
   bound its size, consume it once before command start, remove it immediately,
   and demonstrate that neither child processes nor diagnostic envelopes receive
   it.
5. **IPC.** Bound identifiers, proof size, frames, deadlines, and state
   transitions. Authenticate the capture endpoint as well as the caller; a
   participant-controlled process must not be able to impersonate the sidecar,
   acknowledge capture, and obtain an unrecorded shell.
6. **Evidence.** A successful shell or command exit is never evidence of a
   complete capture. Only persisted, checksummed finalization may support a
   complete evidence record; rejection yields a denied-attempt observation;
   mid-stream loss yields partial/invalid evidence with loss disclosure. No
   exit-code remapping may erase that the command already ran.
7. **Readiness and errors.** Readiness must be fresh and evidence-backed for the
   whole issuance-to-finalization chain. Where the SSH path is legitimately part
   of a RAES participant execution scope, `accepting_new_work` may be true only
   when its existing service-state contract says `ready`; otherwise reuse the
   runtime's canonical SSH readiness carrier rather than relabeling the scope.
   Errors expose stable bounded reason codes and safe references, not raw proof,
   environment dumps, frames, native payloads, or absolute storage paths.

Fail closed is meaningful only before the protected side effect. Once a command
has executed, a later capture failure cannot retroactively make it unexecuted;
the runtime may stop further work, but must record the command and the incomplete
evidence honestly. Degraded capture means the command is intentionally admitted
without the complete required measurement and therefore carries an explicit
validity limitation. It is never a hidden fallback from fail closed.

## Extension seam

The variation that must remain possible is an explicitly authored change from
capture-required admission to deliberately degraded capture. The pinned RAES
`loss_disclosure` field says how incomplete evidence is disclosed; it does not
say whether participant execution may begin without capture. Do not overload it
or add a local enum. The disposition must be a RAES-owned authored/admitted
policy resolved by the runtime into its admission state machine. The runtime
proof transport is a separate replaceable mechanism behind that decision, so a
future broker or mutually authenticated channel does not require changing the
portable TechVault identity.

## Known hazards in the current pack

- `AcceptEnv APTL_CAPTURE_CAPABILITY` supplies a client-controlled value; the
  allowlist itself neither produces nor authenticates a capability.
- The background stream client can race participant command start: the wrapper
  does not synchronously receive `session_accepted` before invoking `script`.
- `ping` proves only that something answered. The abstract socket and one-way
  bearer proof do not by themselves prove that the expected capture apparatus
  owns the endpoint.
- Invalid or absent run/session ids are converted into anonymous ids, breaking
  binding and evidence correlation instead of failing admission.
- `mktemp -u` followed by `mkfifo` has a name-allocation race. Temporary IPC must
  use an atomically created private location and deterministic cleanup.
- The client prose says capture may degrade and the shell continue, while the
  wrapper prose says every missing prerequisite denies access. There must be one
  policy authority and one tested state machine.
- Current `APTL_*` names and downstream ADR comments are migrated runtime
  details, not canonical pack vocabulary or semantic authority. Do not spread
  them into new SDL, compatibility, validation, or evidence fields.
- A final stream failure currently replaces the real command status with 70.
  That can signal invalid capture to SSH, but it cannot be the only run record;
  command outcome and capture outcome are separate facts.
- Service-unit `active` intent, a healthy container, a writable volume, or a
  protocol `pong` is not evidence-backed participant readiness.
- The current SDL has no authored Kali participant access binding or Kali shell
  capture evidence requirement. The sole evidence requirement is unrelated
  Cortex schema readback.

## Verification contract

Tests must cover positive admission and finalization; missing, malformed,
expired, replayed, and mismatched proof; invalid/missing correlation identity;
sidecar impersonation or channel-authentication failure; readiness loss before
admission; loss during a command; interactive and original-command execution;
exit-status preservation; evidence creation, partial evidence, and loss
disclosure; proof redaction from argv, descendants, logs, diagnostics, and
portable artifacts; clean realization from digest-bound bytes; and rejection of
post-realization mutation.

Pack-local unit tests may exercise shipped wrapper/client mechanics. Static pack
and release checks must exercise the normal RAES parser, content identity, and
release surfaces. The runtime consumer must own integration tests for proof
issuance, sidecar verification, SSH delivery, realized readiness, and persisted
RAES evidence records; a mock in this repository cannot establish those claims.

## Non-goals

- No pack-owned token format, issuer, secret store, evidence schema, readiness
  schema, collector registry, error envelope, or logging framework.
- No compatibility-manifest or generated-artifact workaround for a per-session
  secret.
- No backend commands, compose fragments, container names, host paths, storage
  paths, or product-specific patch hooks added to the portable contract.
- No claim that `built` maturity is golden participant/readiness proof.
- No local extension of RAES to encode fail/degrade semantics. If required
  expressivity is absent, it is added and released by RAES first.
- No selection here of the runtime credential mechanism. That decision belongs
  with the runtime-side session, SSH, capture, and evidence-boundary records and
  must satisfy the constraints above.

## Coordinated records

- [Environment-pack/runtime capture ownership](../public/ownership-boundary.md)
- [ADR 0009: zero RAES semantic extensions](../decisions/adrs/0009-scenario-packs-subordinate-to-aces.md)
- [ADR 0012: associated-artifact content identity](../decisions/adrs/0012-pack-content-identity-and-trust-boundary.md)
- [ADR 0036: first-party content remains RAES-subordinate](../decisions/adrs/0036-publish-first-party-content-with-env-packs.md)
- [Runtime capture/admission/evidence preflight](https://github.com/Brad-Edwards/aptl/blob/main/docs/architecture/exp-010-capture-admission-evidence-preflight.md)
- [Runtime environment-pack capture ownership](https://github.com/Brad-Edwards/aptl/blob/main/docs/architecture/issue-589-scenario-pack-capture-ownership-preflight.md)
- [Runtime SSH module boundary](https://github.com/Brad-Edwards/aptl/blob/main/docs/architecture/issue-790-ssh-module-split-preflight.md)
- [Runtime correlation identity and clock boundary](https://github.com/Brad-Edwards/aptl/blob/main/docs/architecture/obs-002-correlation-identity-clock-preflight.md)
- [Runtime patch removal](https://github.com/Brad-Edwards/aptl/issues/915)
- [Runtime closed-world enforcement](https://github.com/Brad-Edwards/aptl/issues/916)
