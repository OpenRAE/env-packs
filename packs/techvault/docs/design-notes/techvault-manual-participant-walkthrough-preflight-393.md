# TechVault final manual participant walkthrough preflight

Issue: `#393` (`techvault: run final manual participant walkthrough`). This
note is architecture guidance only. It does not launch the range, execute
participant commands, inspect live telemetry, remediate defects, write the
run-specific walkthrough report, change pack maturity, or mutate GitHub. The
issue is the contract for this requirement-free slice.

## Decisions and boundaries

- Treat this slice as the human proof and evidence-reconciliation gate over the
  existing `operational` Docker Compose profile. It is not another runtime
  profile, scenario definition, objective/oracle model, rehearsal harness, or
  lifecycle implementation.
- The current pack, not the superseded standalone TechVault design notes, owns
  the scenario meaning. `sdl/techvault.sdl.yaml` is the authored scenario
  authority. `docs/attack-path.md`, the participant briefing, and the delivery
  bundles declare a non-linear purple-team exercise with no scored objectives,
  mandatory exploit chain, flags, or completion oracle.
- Do not manufacture a “full attack path” to make the walkthrough resemble a
  scored CTF. The manual journey must align with the stable actions already
  exercised by `build/rehearsal.py`: enter at ACES `kali`, establish the portal
  baseline, prove invalid authentication is rejected, validate the authored
  `webapp-sqli-login` weakness, reach the resulting dashboard/admin surfaces,
  create participant state through upload and SMB, exercise a bounded
  telemetry-generating action, compare red activity with defensive
  observation, reset, and prove authored start state returns while stale
  participant state does not.
- For this scenario, the required human success conditions come from
  `assets/briefing/mission-brief.md` and the guided checkpoints: a defensible
  participant assessment, timestamped red activity, a non-destructive proof of
  the portal weakness, in-world enterprise context, and a red/blue comparison
  identifying at least one observed action and one visibility gap. Absence of
  objectives/oracle/flags is an explicit `not applicable` finding, not an empty
  passing oracle and not itself participant success.
- Keep action-plane and observation-plane evidence distinct. Participant
  actions originate manually in the Kali shell reached through the loopback
  `kali-ssh-proxy`. Docker/Compose, host/root access, generated operator
  material, service administration, direct data stores, and APTL collectors may
  provision, observe, diagnose, reset, and tear down; none may perform or
  fabricate the participant action being proved.
- Keep reusable guidance separate from run evidence. A command-by-command
  operator walkthrough under `docs/walkthroughs/` may describe the stable
  `operational` procedure and expected outcome shapes. The issue-specific
  committed report under `docs/` records what a human actually typed, the
  observed result, defects/fixes/reruns, automated follow-up, static/unit
  results, and teardown. Neither artifact becomes a topology, oracle, telemetry
  schema, or copy of the automated run archive.
- Keep `docs/golden-readiness-checklist.md` unchecked as the reusable source.
  Copy it into the issue-specific report and check only facts proven by that
  run. Unchecked or not-applicable items need an explicit reason; do not edit
  the source checklist into a historical run record.
- Maturity reconciliation is evidence-driven, not assumed by the issue title.
  `contents.reference_triangle` may become true only when the packaged build,
  automated rehearsal, and command-by-command walkthrough all ship and agree.
  `status: golden` is allowed only if the final run also proves every advertised
  required service/success surface, reset, post-manual automation, static/unit
  gates, and independent teardown. A representative partial journey may finish
  the report but must leave the pack `draft`/`built` with limitations stated.

## Canonical incumbents to reuse

- `scenarios/README.md`, `scenarios/_template/README.md`, and
  `docs/golden-readiness.md`: reference-triangle semantics, explicit
  participant-role declaration, self-contained source, isolated-host doctrine,
  manual walkthrough protocol, report discipline, maturity meanings, and
  last-pass issue handling.
- `scenarios/techvault/pack.yaml`, `pack.compatibility.yaml`, `README.md`, and
  `docs/topology-reference-triangle.md`: pack identity, current `draft`
  maturity, `operational` runtime profile, artifact visibility, validation
  commands, existing live-rehearsal evidence, and incomplete manual side of the
  triangle.
- `sdl/techvault.sdl.yaml` and the released ACES parser/pack validator: nodes,
  networks, services, dependencies, content, vulnerability, domains,
  relationships, and accounts. Do not parse or restate these as a walkthrough
  inventory. ACES currently authors no scored objectives/evidence contract.
- `docs/attack-path.md`, `assets/briefing/mission-brief.md`,
  `profiles/guided/participant/{plan,checkpoints}.md`, and the unguided and
  purple-team bundle documents: role, no-linear-path boundary, human success
  conditions, containment, and red/blue comparison contract.
- `build/launch.sh`, `health-check.sh`, `reset.sh`, and `cleanup.sh`: the only
  pack lifecycle entrypoints. They already enforce the operator-env and
  Compose-project validators and bind the full profile set. The walkthrough
  must not reproduce their Docker logic.
- `build/validate_build.py`: canonical contained regular-file resolution for
  `TECHVAULT_OPERATOR_ENV`, Compose project-id grammar, safe YAML loading,
  ACES-to-Compose joins, environment-name/policy checks, generated-state
  boundaries, loopback ingress, image pins, and value-sparse
  `object:id.field: invariant` diagnostics.
- `build/render_runtime.py` and `build/operator-defaults.env`: generated state
  plus committed synthetic defaults. The env-file path and
  `TECHVAULT_COMPOSE_PROJECT` are existing configuration/namespace seams; the
  repository-root environment file is not a TechVault input.
- `build/rehearsal.py`, `build/tests/test_rehearsal.py`, and
  `docs/rehearsal-report-392.md`: stable action/check ids, participant connector,
  representative journey, negative checks, telemetry summary, reset/freshness,
  residual verification, report redaction, and the exact automated/manual
  boundary. Reuse that vocabulary; do not call the harness as manual proof.
- Pack-local APTL incumbents: `aptl.utils.redaction.redact`,
  `aptl.utils.curl_safe`, the `aptl.*` logger hierarchy,
  `aptl.core.runstore.LocalRunStore`, backend snapshot/readiness helpers, and
  telemetry collectors. Do not add another redactor, logger, run archive,
  Docker inspection layer, or exception hierarchy.
- `scripts/ci/scenario_content_ci.py`, the released
  `aces-pack-validate`/`aces-pack-release` commands, and existing TechVault
  pack-local tests: canonical schema, path/symlink, visibility, release,
  validator-discovery, participant-leak, and regression gates.

## Cross-cutting layers the design must pass

| Layer | Required fit for issue `#393` |
|---|---|
| Pack/catalog schemas | `pack.yaml` remains descriptive and stores no commands, evidence, environment values, Docker state, or proof. Any new walkthrough/report path is indexed at an operator/commercial boundary in `pack.compatibility.yaml`, issue `393` is added to existing issue provenance, and central validation/release checks pass. Promote only the optional layer and maturity actually proven. |
| ACES shape and semantics | Resolve scenario facts through the released ACES parser. Reference stable ACES ids such as `kali` and `webapp-sqli-login`; do not add a walkthrough topology, account list, service catalog, hidden path, objective, evidence predicate, or extension field. Confirm objectives/evidence/flags are absent from their canonical surfaces before recording them as not applicable. |
| Build/config validation | Run `build/validate_build.py validate` before lifecycle work. Resolve `TECHVAULT_OPERATOR_ENV` through `resolve_operator_env` and the project through `validate_compose_project`; missing, symlinked, non-regular, or out-of-pack env files fail closed. Pass only the env-file path to wrappers/Compose and never expand values into commands or evidence. |
| Host isolation | Run only on a disposable isolated Docker host. Fixed container names, fixed subnets, vulnerable services, elevated capabilities, host publications, and Docker-socket consumers make `TECHVAULT_COMPOSE_PROJECT` insufficient for same-daemon concurrency. Preserve loopback publications, Kali's network boundary, and one TechVault run per daemon. |
| Participant authentication and entry | Resolve the loopback `kali-ssh-proxy` port and enter as `kali` using the generated operator-side SSH private key. The key is transport material, not scenario evidence: its contents never enter Kali, argv values, logs, screenshots, or the report. After entry, only in-world participant-reachable services and discoverable synthetic content may advance the journey. |
| Participant action plane | A human types each action in the Kali participant shell and preserves the intended privilege context. Do not pipe the rehearsal script into SSH, run `docker compose exec kali`, replay a transcript, invoke test helpers, seed missing state, or use host/root/service-admin access to stand in for the human action. Record exact or safely redacted command shapes and bounded expected/observed output, not raw secret-bearing transcripts. |
| Observation/telemetry plane | Preserve a run/timestamp correlation id and reuse existing collectors, snapshots, Wazuh/Suricata surfaces, and SOC services for observation. Label observer evidence separately from participant evidence. Direct containers, service APIs, or data stores may diagnose observation but cannot prove the red action occurred; a participant self-report or captured command cannot prove the defensive observation. |
| Objective/flag/success handling | Record objective oracle and flag board as `not applicable`, based on canonical source. Prove the authored human checkpoints and the rehearsal-aligned outcomes instead. Do not promote health, SQLi alone, an uploaded marker, telemetry count, SOC alert, or an N/A row into a completion oracle. |
| Negative gates | Preserve invalid-login rejection before SQLi, bounded target/port containment, pre-reset presence of participant-created state, post-reset absence of that state, and post-reset presence of authored content/services. A negative result is tied to a real affordance and context; marker files and HTTP status alone are supporting observations, not a new objective model. |
| Secret handling | Real host/cloud credentials, GC/CTFd/admin tokens, private keys, generated certificates/passwords, cookies, environment values, and service credentials remain outside source and committed evidence. Synthetic scenario credentials are valid in-world content but are still redacted at process/log/report boundaries. `APTL_EXPERIMENT_NO_REDACT` must remain disabled. |
| OS/process exposure | Do not put credentials, cookies, secret-bearing headers, raw SQL/SMB payloads with sensitive values, generated answers, or low-entropy secret digests in process argv, URLs, shell history, Docker labels, image metadata, Compose output, filenames, terminal capture, screenshots, service logs, issue comments, or report metadata. Use stdin, restricted files, or existing safe HTTP helpers where a secret-bearing operator observation is unavoidable. |
| Persistence and reset | Use `build/reset.sh`; do not hand-delete or reseed state. Prove participant-created upload/share state cannot satisfy the next run while ACES-authored services, content, routes, and accounts return. Report retained versus regenerated state using the existing lifecycle semantics rather than inventing a reset ledger. |
| Cleanup and teardown | Use `build/cleanup.sh`, then independently verify the validated Compose project has no containers, networks, or project-prefixed volumes. A successful `docker compose down` exit is not teardown proof. Every launched manual, remediation-rerun, or automated instance must have an attributable cleanup result. |
| Persistence/reporting | Raw activity logs, captures, service responses, snapshots, environment material, Docker output, keys, and certificates remain in ignored operator/run-store paths. The committed report is value-sparse and may contain run/profile/commit ids, action/check ids, sanitized command shapes, expected/observed status, timestamps, counts, approved digests, defects, reruns, and cleanup outcome. |
| Error envelope | Reuse the existing issue/check vocabulary and `redact` at every serialization boundary. Failures may name phase, ACES/check id, field/invariant, safe path, exit status, count, duration, and digest. Do not paste raw stdout/stderr, exception payloads, HTTP bodies/headers, Docker inspections, environment blocks, credentials, cookies, or secret-derived hashes. |
| Repo CI and release | After the manual path and any fixes, run the existing automated rehearsal against `operational`, TechVault static/unit checks, repo scenario-content CI, and central pack validation/release checks. A manually green report never waives a failing schema, leak, unit, rehearsal, reset, or teardown gate. |

## Manual evidence contract

The issue-specific report is an operator evidence digest, not an automated
manifest or secret transcript. Its run metadata and action rows must let a
reviewer distinguish manual participant proof from observer and harness work.

| Field | Rule |
|---|---|
| `run` | Issue, UTC timestamps, git commit and clean/dirty state at launch, profile `operational`, validated Compose project, isolated-host attestation, and final cleanup outcome. Do not record host/account identifiers beyond the bounded range namespace. |
| `plane` | `participant`, `observer`, or `lifecycle`. Only `participant` rows can prove participant actions; observer and lifecycle rows are supporting evidence. |
| `path_ref` | Existing ACES id, rehearsal check id, or participant checkpoint. Do not create hidden state/objective ids. |
| `context` | Source node/user/privilege and entry transport. Participant rows must say `kali` through `kali-ssh-proxy`; observer rows name the bounded defensive surface. |
| `command` | What the human typed, exactly when safe and otherwise a redacted command shape. Never include credential, cookie, token, private-key, or answer values. |
| `expected` / `observed` | Bounded status, safe excerpt, count, timestamp, or approved digest that demonstrates the expected effect. Raw response and terminal dumps remain uncommitted. |
| `success_condition` | Existing briefing/checkpoint or rehearsal outcome satisfied, or explicit `not applicable` for undeclared objective/oracle/flag surfaces. |
| `defect` | Symptom, canonical owner changed, fix summary, affected manual step, and rerun result. Do not hide a defect with an operator repair or weaker expected result. |
| `automation` | Post-manual rehearsal and static/unit/CI command plus pass/fail status and report reference. Harness output is not copied into manual rows. |
| `teardown` | Wrapper result plus independent zero-residual counts for the exact project namespace. Failure or skipped verification blocks a readiness claim. |

The run-specific checklist must state separately what was manually proven, what
was observed by operator/defensive tooling, what was automated afterward, what
was not applicable, and what remains out of scope. A small structural report
test may enforce required sections, stable ids, value-sparse metadata, and leak
patterns; it must not become a second proof engine or decide whether a human
actually performed the actions.

## Extensibility seams

- **Run/lifecycle namespace:** keep run id, Compose project, operator-env path,
  participant activity correlation id, report path, and runtime archive as
  separate validated inputs. A future remote Docker host may bind the same
  evidence contract. Parallel runs require removal of fixed container/subnet
  identities, not a misleading project-name-only switch.
- **Participant connector:** isolate proxy-port resolution, SSH user, and key
  path at the entry boundary. A future portal, VPN, or remote connector may
  replace transport while still landing in the same ACES `kali` role and
  leaving the scenario journey unchanged.
- **Outcome identity:** align reusable walkthrough sections, manual report rows,
  and automated evidence through existing ACES/check/checkpoint ids. If ACES
  later adds objectives, evidence, or flags, join those canonical ids as new
  validators; do not retrofit today's representative actions into a private
  oracle.
- **Observation adapter:** a future SIEM or provider may supply the same
  correlation window, source/target context, counts, statuses, and safe digests.
  It must not change participant success semantics or turn product telemetry
  into the scenario authority.
- **Report projection:** keep one operator evidence report with explicit planes
  and value-sparse fields. New delivery bundles can project safe summaries from
  it without copying commands, raw telemetry, hidden diagnostics, or secrets
  into participant content.

## Whole-repo surfaces in scope

- Catalog and central contract: `scenarios/README.md`,
  `scenarios/_template/README.md`, `docs/golden-readiness.md`, TechVault
  `pack.yaml`, `pack.compatibility.yaml`, provenance metadata, and the released
  ACES pack validator/release checker.
- Scenario and audience truth: `sdl/techvault.sdl.yaml`, `docs/attack-path.md`,
  `assets/briefing/`, `profiles/bundles.yaml`, and participant/operator profile
  documents. These define the role and success boundary; the report only
  references them.
- Reference triangle and lifecycle: `build/{launch,health-check,reset,cleanup}.sh`,
  `build/validate_build.py`, `build/render_runtime.py`,
  `build/operator-defaults.env`, `build/rehearsal.py`, build tests,
  `docs/rehearsal-report-392.md`, future `docs/walkthroughs/`, the final report,
  and `docs/golden-readiness-checklist.md`.
- Shared runtime concerns: APTL redaction, safe HTTP, logging, run store,
  snapshots/readiness, telemetry collectors, Docker Compose, generated files,
  ignored run archives, and secret scanning.
- Repository workflow: `scripts/ci/scenario_content_ci.py`, central validation
  and release commands, documentation links, participant-boundary leak scans,
  and last-pass issue/PR handling (`Refs #393` until all final evidence and
  reconciliation are complete).
- Host/OS exposure: process argv/environ, shell history, SSH client state,
  terminal capture, Docker API/socket and daemon state, Compose logs/inspect,
  service HTTP/DB/SOC APIs, generated keys/certificates/password files,
  screenshots, Markdown reports, issue/PR comments, and CI logs.

## Gotchas and anti-patterns

- Do not use `build/rehearsal.py`, its generated shell, `docker compose exec`,
  a pasted script, or a prior transcript as the human command-by-command proof.
- Do not conflate a representative purple-team journey with a newly mandatory
  linear attack chain, or conflate objectives, oracle states, flags, briefing
  checkpoints, rehearsal checks, HTTP statuses, SOC alerts, and maturity.
- Do not treat `not applicable` objective/flag rows, service health, SQLi alone,
  an uploaded marker, a captured command, or a telemetry count as a completion
  oracle.
- Do not read `telemetry_evidence_path: PASS` in the #392 report as proof that
  every SOC correlation worked. That run recorded zero indexed Wazuh alerts and
  zero correlated Wazuh/Suricata events while bounded manager/victim log
  evidence was present. The human comparison must report the current observed
  path and the gap honestly; it must not relabel fallback evidence as a
  successful indexed detection.
- Do not use the generated operator env, SSH private key, Docker/root access,
  direct database/SOC administration, generated passwords, or raw service
  output as participant evidence. Observer use must be labeled and bounded.
- Do not hard-code another node/service/network/account/credential inventory or
  duplicate environment parsing, path containment, reset, teardown, telemetry,
  report, validation, redaction, logging, or exception logic.
- Do not widen loopback ports, attach Kali to the control network, run on a
  shared daemon, permit uncontrolled egress, use real third-party targets, or
  weaken a negative gate to make the walkthrough pass.
- Do not commit activity logs, packet/terminal captures, cookies, HTTP bodies,
  generated material, environment files, Docker output, screenshots, private
  keys, certificates, passwords, or secret-shaped digests.
- Do not silently repair a missing service, route, content item, account, or
  detector from the operator plane. Fix the canonical owner, relaunch or reset
  as appropriate, rerun the affected human step, and rerun automation.
- Do not overwrite `docs/rehearsal-report-392.md` with manual evidence or mark
  the source checklist. Keep automation, reusable walkthrough, run report, and
  checklist roles distinct.
- Do not preserve stale readiness prose during final reconciliation.
  `README.md`, `build/README.md`, and `docs/attack-path.md` still contain
  pre-#392 statements that live rehearsal or teardown has not been proven,
  while the immutable #392 report records a passing isolated-host run. Update
  current-status prose from the final evidence without rewriting the historical
  report or overstating the still-missing manual proof.
- Do not set `reference_triangle: true` or `status: golden` merely because issue
  `#393` produced a report. Missing advertised service proof, a failed red/blue
  success condition, stale state, failed automation/CI, residual Docker state,
  or an honest remaining limitation blocks the corresponding claim.

## Non-goals

- This preflight does not choose exact exploit commands, safe excerpts,
  correlation ids, report filename, participant marker, host port, Docker host,
  runtime credentials, telemetry verdict, defect fix, or final maturity.
- It does not add a Ground Control requirement, ACES extension, hidden path,
  objective/evidence/scoring model, flag/CTFd layer, delivery bundle, runtime
  profile, range engine, provider abstraction, service/repository layer,
  report-schema framework, logger, redactor, exception hierarchy, or second
  lifecycle implementation.
- It does not execute the manual walkthrough, automated rehearsal, static/unit
  checks, release validation, reset, or teardown, and it does not claim that the
  current pack is golden.
- It does not broaden the exercise to malware, destructive impact, public
  callbacks, internet targets, real credentials, customer data, live tenants,
  or concurrent ranges on the same Docker daemon.
