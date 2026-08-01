# TechVault automated live-rehearsal preflight

Issue: `#392` (`techvault: add automated live rehearsal`). This note is
architecture guidance only. It does not implement a rehearsal, launch or alter
a live range, write a successful rehearsal report, define a participant
walkthrough, change pack maturity, or create a Ground Control requirement. The
issue is the contract for this requirement-free slice.

## Decisions and boundaries

- Rehearse exactly the compatibility manifest's `operational` Docker Compose
  runtime through `build/launch.sh`, `build/health-check.sh`, `build/reset.sh`,
  and `build/cleanup.sh`. The imported APTL `aptl lab validate-live` command,
  reduced curated scenarios, direct service startup, fixtures, and static
  `_NoStartBackend` realization are not alternate golden profiles.
- Keep ACES authoritative. `sdl/techvault.sdl.yaml` owns nodes, networks,
  services, dependencies, content, vulnerabilities, relationships, and
  accounts. The rehearsal may reference ACES addresses and observed provider
  bindings; it must not add a topology inventory, account ledger, service list,
  objective schema, or TechVault preset.
- Treat TechVault as the explicitly declared non-linear purple-team exercise it
  is. The SDL authors no scored objectives, evidence predicates, flags, or
  mandatory exploit chain. `docs/attack-path.md` remains authoritative about
  that absence. A deterministic rehearsal journey may prove representative
  affordances and defensive observation, but its phases are proof checks, not a
  new hidden path or completion oracle.
- Split transport by authority. Participant actions enter the loopback-published
  `kali-ssh-proxy` and run as the participant on ACES `kali`. `docker compose
  exec`, container inspection, direct databases, SOC administration, generated
  credentials, Docker APIs, and host/root access are limited to provisioning,
  observation, diagnostics, reset, and teardown.
- The build must place every tested service, account, content item, key, route,
  and vulnerability before rehearsal starts. The rehearsal must detect absent
  start state and fail; it must never repair or seed it.
- Runtime archives stay in the gitignored APTL run store. The committed report
  is a small, redacted derivation containing stable ACES addresses, check ids,
  statuses, timings, counts, and digests. It is not a copied transcript,
  snapshot, Docker inspection, or credential store.
- `pack.yaml.status` stays honest, and
  `contents.reference_triangle` remains `false`, until live proof and the
  matching manual walkthrough complete the all-or-nothing build/test/walkthrough
  triangle. Automated rehearsal alone is not `golden` and does not replace the
  final manual participant walkthrough.

## Canonical incumbents to reuse

- `scenarios/README.md`, `scenarios/_template/README.md`, and
  `docs/golden-readiness.md`: pack layout, offensive/non-offensive declaration,
  golden proof boundary, reference triangle, report, reset, and teardown rules.
- `README.md`, `pack.yaml`, `pack.compatibility.yaml`,
  `docs/attack-path.md`, `docs/topology-reference-triangle.md`, and
  `docs/golden-readiness-checklist.md`: TechVault maturity, `operational`
  runtime identity, visibility boundaries, participant role, lack of scoring,
  and proof status.
- `sdl/techvault.sdl.yaml` plus the ACES reference parser/compiler used by
  `aptl.validation.techvault_gate`: scenario shapes, semantic validation,
  backend conformance, and resource addresses. Do not parse YAML independently
  to reinterpret ACES meaning.
- `build/validate_build.py` and `build/tests/test_build_contract.py`: contained
  path checks, safe YAML loading, SDL-to-Compose joins, active profile set,
  required environment names, generated-path policy, loopback ingress, image
  pins, and the existing `object:id.field: invariant` static issue style.
- `build/render_runtime.py` and `build/operator-defaults.env`: generated state
  and committed synthetic-default binding. `TECHVAULT_OPERATOR_ENV` and
  `TECHVAULT_COMPOSE_PROJECT` are the existing override and namespace seams;
  the repository root environment file is not a TechVault input.
- `build/aptl-runtime/src/aptl/core/deployment/`, `core/snapshot.py`, and
  `validation/range_snapshot_summary.py`: backend inspection, project-scoped
  lifecycle/cleanup result semantics, redacted live snapshots, and
  evidence-sized snapshot summaries. Do not add raw Docker parsing when these
  interfaces expose the needed fact.
- `aptl.validation.techvault_live_gate`, `_live_gate_checks`, and their probe
  helpers: stable live-check vocabulary, layer-specific failure categories,
  ACES-derived realization checks, readiness, Kali reachability, telemetry
  evidence, and report-first expected-failure behavior. Reuse individual checks
  or their lower-level owners only where they observe the already launched
  `operational` build; do not call their top-level destructive boot workflow as
  a second lifecycle authority.
- `aptl.validation.participant_live_proof` and the ACES participant snapshot
  validators: operation, episode, behavior, shared-state, and concurrency
  contract validation. Initializing an ACES participant episode is supporting
  control-plane evidence; by itself it is not proof that a Kali participant
  performed the exercise journey.
- `aptl.utils.redaction.redact`, `aptl.utils.curl_safe`,
  `aptl.utils.logging.get_logger`, and `aptl.core.runstore.LocalRunStore`:
  secret-shaped value redaction, credential-safe HTTP probes, the `aptl.*`
  logger hierarchy, contained run ids/paths, and redaction at JSON/JSONL
  persistence boundaries. Do not create another redactor, logger, run archive,
  or exception hierarchy.
- `profiles/bundles.yaml`, `profiles/validate_profiles.py`, the guided/demo proof
  moments, and participant briefings: delivery exposure and human alignment
  inputs. A delivery bundle is not a runtime profile, and facilitator prompts
  are not an oracle.
- `scripts/ci/scenario_content_ci.py`, `scripts/ci/pack_release.py`, and
  `.github/workflows/scenario-content.yml`: test discovery, compatibility and
  provenance validation, participant leak scanning, golden-checklist checks,
  staged-release leak scanning, and the canonical repo gate.

## Cross-cutting layers the design must pass

| Layer | Required fit for `#392` |
|---|---|
| Pack/catalog schemas | Add rehearsal artifacts as references in `pack.compatibility.yaml`; do not duplicate their contents there. Keep `operational` as the sole runtime profile, map `tests/` and the report to non-participant boundaries, and do not promote status from automation alone. |
| ACES shape and semantics | Parse and compile `sdl/techvault.sdl.yaml` through ACES and reuse its stable addresses. Absence of `objectives` and flags is an explicit not-applicable result, never an empty passing oracle or an invitation to invent one. |
| Build contract | Run `build/validate_build.py` before live work. Derive provider expectations through its contract and APTL realization/snapshot helpers; do not copy the service/profile/network inventories into rehearsal source. |
| Environment/config binding | Use the committed defaults or a documented `TECHVAULT_OPERATOR_ENV` regular file contained under the pack. Reuse `validate_build.py`'s canonical/path-containment pattern and required-name checks. Pass only the env-file path to Compose; never expand values into argv, report metadata, or logs. |
| Run and cleanup namespace | Bind report run id to `TECHVAULT_COMPOSE_PROJECT`, validate both before destructive work, and record the project identifier without credentials. Because Compose contains fixed `container_name` values and fixed subnets, current proof is one run per isolated Docker host; a project-name override alone does not make parallel runs safe. |
| Participant authentication | Connect to `127.0.0.1` at the resolved `kali-ssh-proxy` host port using the generated operator-side private key only as the participant-entry credential. The private key remains host-side; targets receive public keys and Kali receives only its distinct pivot key. Never prove participant work with `docker compose exec kali`. |
| Participant execution | Run the representative action journey from Kali and preserve participant privilege context. Any credential needed after entry must already be discoverable in-world. Report command shapes only after redaction; avoid secrets in remote argv, process listings, shell history, capture output, or terminal transcripts. |
| Setup/readiness | Invoke `build/health-check.sh`, then reuse APTL backend snapshot/readiness checks for richer evidence. Health is a prerequisite, not an objective verdict. It must cover the live ACES-derived resource surface rather than add a third hard-coded service inventory. |
| Purple-team observation | Reuse the APTL telemetry-evidence probes and existing Wazuh/Suricata/SOC surfaces. Distinguish participant success from sensor/configuration gaps as `docs/attack-path.md` requires, while still failing a golden-build claim when a required defensive proof surface is broken. |
| Objective/flag/negative gates | Record scored-objective and flag checks as explicitly not applicable. Negative checks must attach to real declared affordances and privilege/context boundaries (for example normal versus malformed portal behavior and pre-action versus post-action evidence), not marker files, fabricated objectives, or management-plane reads. |
| Reset/freshness | Invoke `build/reset.sh`; prove prior participant-created state and stale proof cannot satisfy the next run, while ACES-authored content, accounts, routes, and services return. Do not implement a second reset algorithm inside the rehearsal. |
| Cleanup/teardown | Invoke `build/cleanup.sh`, then verify the exact project has no remaining containers, networks, or volumes. A successful `docker compose down` message or the script's best-effort named-volume removal is not teardown proof. Cleanup failure must make the run fail and remain visible in the report. |
| Persistence/reporting | Write raw/redacted machine evidence only through `LocalRunStore` under the ignored runtime `runs/` root. Produce the committed Markdown report from value-sparse evidence; never redirect the run store into `docs/` or commit generated `.operator/`, `.aptl/`, captures, logs, certificates, keys, or Docker output. |
| Error envelope | Reuse `LiveGateCheck`/`LiveGateReport` and `LabResult`/`LabStatus` semantics, stable layer categories, and `redact(str(exc))` at serialization. Expected failures become FAIL/BLOCKED checks; raw subprocess stderr, exception payloads, SDL documents, Docker inspections, and HTTP bodies do not enter the report. |
| Logging/observability | Use the `aptl.*` logger and the existing snapshot/capture pipeline. Logs may contain check ids, ACES addresses, status, elapsed time, counts, and digests only. Keep OTEL platform traces, Kali capture evidence, security-event evidence, and the durable rehearsal summary conceptually distinct. |
| Host/OS containment | Run on a disposable, isolated Docker host, not a shared workstation or long-lived service host. The range contains intentionally vulnerable workloads, elevated capabilities, host-published control surfaces, and Docker-socket consumers. Preserve loopback publications and Kali's internal-only networks; rehearsal code must not widen binds or attach Kali to `aptl-control`. |
| Repo CI/release | Exercise pack-local static/unit tests and `python3 scripts/ci/scenario_content_ci.py`. Live proof supplements those gates. Any new participant-facing path or report projection must be represented in the compatibility manifest so both repository and staged-release leak scans see it. |

## Security blockers and guardrails

- `build/render_runtime.py` currently passes a generated PKCS#12 password as
  `openssl ... -passout pass:<value>`. That exposes the value in process argv.
  A successful live-proof claim is blocked until the build uses a non-argv
  channel such as a mode-0600 file descriptor/file or stdin, with cleanup on
  every outcome. The rehearsal must not copy this pattern.
- The documented pack-local boundary for `TECHVAULT_OPERATOR_ENV` is not yet
  enforced by the lifecycle shell wrappers. The rehearsal must fail closed on
  missing, symlinked, non-regular, or out-of-pack override files and should
  reuse the existing build validator's containment rules rather than add a
  looser parser.
- Synthetic scenario credentials may remain committed as scenario content, but
  they are still secret-shaped at process, log, capture, snapshot, error, and
  report boundaries. Always apply the existing redactor. Do not enable
  `APTL_EXPERIMENT_NO_REDACT` for a golden rehearsal.
- Use `curl_safe`'s mode-0600 header-file path for authenticated observation.
  Do not use `curl -u`, token-bearing URLs, command-line passwords, or HTTP
  bodies in diagnostics. Participant actions needing a secret must use a
  channel appropriate to the in-world tool without exporting it to the
  operator report.
- Fixed Compose container names and subnets can collide across projects. Until
  the provider removes those fixed identities, isolation is by disposable host
  as well as project name. Never run two TechVault rehearsals concurrently on
  one Docker daemon.
- The Kali capture sidecar and APTL run archive are evidence systems, not
  participant-visible storage and not an oracle. Do not expose sibling session
  captures, mount the capture volume into Kali, or treat captured commands as
  trustworthy objective proof.

## Extensibility seams

- **Run identity and lifecycle namespace:** preserve separate validated `run_id`,
  `TECHVAULT_COMPOSE_PROJECT`, operator-env path, report path, and runtime-root
  inputs. A future remote Docker host can bind the same lifecycle and evidence
  contract without changing ACES or report semantics. Parallel runs require a
  provider fix for fixed container names/subnets; do not hide that behind the
  project parameter.
- **Participant connector:** keep the participant host, resolved proxy port,
  SSH user, and key path at one transport boundary. A future portal/VPN/remote
  connector should replace that binding while producing the same participant
  action outcomes, not fork rehearsal logic.
- **Evidence checks:** key checks by stable ACES address plus a rehearsal check
  id and allowed evidence fields. Future ACES objectives or flags can join as
  additional canonical validators without rewriting existing affordance,
  health, telemetry, reset, or teardown checks.
- **Walkthrough alignment:** maintain one ordered set of public action shapes and
  expected outcome ids that both the automation report and future operator
  walkthrough can reference. Keep secrets, raw outputs, provider commands, and
  hidden diagnostics outside that alignment surface.

## Gotchas and anti-patterns

- Do not call the imported top-level live gate to boot a second lab, and do not
  let `aptl.json`'s historical default scenario/profile silently replace the
  pack's `operational` lifecycle.
- Do not confuse APTL's ACES participant-episode initialization with execution
  of the TechVault participant journey.
- Do not turn guided checkpoints, demo proof moments, SOC alerts, captured
  commands, a successful SQL injection, or a health check into a scored
  objective oracle.
- Do not create duplicate ACES, topology, profile, environment, readiness,
  telemetry, snapshot, report, validation, redaction, logging, exception,
  reset, cleanup, or lifecycle schemas.
- Do not hard-code another active-service list, host inventory, network map,
  port map, credential table, or account map in the rehearsal.
- Do not use operator access to repair missing state, inject test users/data,
  plant flags, install services, write success markers, or manufacture sensor
  evidence.
- Do not commit run archives, raw terminal/capture data, Docker/Compose output,
  HTTP bodies, full snapshots, generated keys/certificates/passwords, env files,
  screenshots, or secret-bearing command lines.
- Do not broaden host ports, publish the proxy beyond loopback, attach Kali to
  the control network, use external targets, or run this intentionally
  vulnerable stack on a shared Docker daemon.

## Non-goals

- No new Ground Control requirement, ACES extension, objective/scoring model,
  flag/CTFd layer, hidden linear attack path, delivery bundle, range engine,
  provider abstraction, service/repository layer, exception hierarchy,
  logging framework, redaction framework, or report schema framework.
- No final manual walkthrough, `golden` promotion, reference-triangle promotion,
  release export, customer/agent benchmark, or production hardening claim.
- No choice of exact participant exploit commands, credentials, evidence
  digests, run identifiers, report verdict, or live host is made here.
- Defects in build placement, isolation, participant reachability, telemetry,
  reset, or teardown are implementation blockers to fix and re-prove; the
  rehearsal must not compensate for them.
