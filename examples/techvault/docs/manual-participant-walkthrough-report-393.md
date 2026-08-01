# TechVault final manual participant walkthrough report (#393)

- Status: `PASS`
- Scenario: `techvault`
- Profile: `operational`
- Manual run: `tv393-manual-20260729-r1`
- Automated follow-up: `tv393-auto-20260729-r1`
- Final committed-tree rehearsal: `tv393-final-20260729-r1`
- Compose project: `techvault_golden`
- Source commit at successful clean launch: `6aff6d10661648d81cd2359a6f6d2af6eaf12f6f`
- Source commit at final-tree rehearsal: `e2d89fd7561cbf0cd54f9fc9fee9646a268b4d68`
- Participant window opened: `2026-07-29T02:58:04Z`
- Evidence and infrastructure reconciliation completed:
  `2026-07-29T04:03:19Z`

## Run boundary

The manual range ran on one disposable EC2 Docker host in a dedicated
issue-tagged VPC and subnet in `us-east-2`. The default VPC was not used. Only
SSH from the execution runner was admitted; all scenario service publications
remained loopback-bound or inside the TechVault networks.

The successful range was extracted from a clean `git archive` of the source
commit above. It used committed pack content and
`build/operator-defaults.env`; no repository-root `.env`, user secret file,
cloud console, SSM command, generated credential value, direct database
console, root shell, or test harness action advanced the participant journey.

Lifecycle and observer commands ran from the disposable host. Every red action
ran as `kali` through the loopback `kali-ssh-proxy`. The terminal driver did not
hold a persistent nested PTY after its first prompt, so the human issued one
explicit SSH remote command per action. This stayed on the declared participant
surface and did not use Docker exec or the rehearsal harness for red proof.

TechVault declares no scored objectives, completion oracle, mandatory exploit
chain, or flags. Those surfaces were verified as not applicable from the
canonical pack and ACES sources; the manual success conditions came from the
participant brief and guided checkpoints.

## Participant evidence

Only bounded results are recorded. HTTP bodies, cookies, SSH keys, generated
values, SMB transcripts, terminal captures, and activity logs were destroyed
with the range.

| Path ref | UTC phase | Manual command shape | Expected | Observed |
|---|---|---|---|---|
| `participant_start_surface` | 02:58 | SSH through loopback proxy; `whoami`, `hostname`, UTC time | `kali` on ACES Kali | `kali`; `kali-redteam`; timestamp emitted |
| guided exposure checkpoint | 02:59 | `ip -brief address`; `ip route` | Authored DMZ/internal/red-team reachability | Three in-range interfaces/routes present |
| `portal_reachable` | 03:00 | `curl` unauthenticated portal baseline | HTTP 200 or redirect | HTTP 200 |
| `negative_invalid_login_rejected` | 03:00 | `curl` invalid synthetic login | HTTP 401 | HTTP 401 |
| `sqli_login_accepted` | 03:01 | `curl` authored `webapp-sqli-login` payload; cookie stored in Kali | HTTP 302 | HTTP 302 |
| `dashboard_reachable` | 03:02 | Authenticated `curl`; bounded heading/count/role excerpt | HTTP 200 and enterprise context | HTTP 200; admin role and synthetic customer context visible |
| `admin_surface_reachable` | 03:03 | Authenticated `curl`; body retained only in Kali | HTTP 200 | HTTP 200 |
| `web_upload_created` | 03:04 | Create run marker; multipart upload | HTTP 302 | HTTP 302 |
| `public_share_content` | 03:05 | Anonymous SMB get of authored `welcome.txt` | Authored company line | `Welcome to TechVault Solutions file server.` |
| `shared_marker_created` | 03:06 | Anonymous SMB put and exact-name list | Run marker present | Run marker present |
| `telemetry_negative_ssh_generated` | 03:07 | Three separate invalid SSH attempts; bounded four-port Nmap | Three rejections plus in-range scan result | Three exit-255 rejections; victim SSH open, other requested ports closed |
| `objectives_oracle_flags_not_declared` | source review | Inspect canonical ACES/pack surfaces | Explicitly not applicable | No objective/oracle/flag contract declared |

The participant demonstrated the intended normal-versus-vulnerable portal
contrast, reached authenticated dashboard/admin context, read authored
enterprise content, and created non-destructive web and SMB state.

## Observer evidence

Observer commands ran only after the participant actions and returned counts,
not raw records.

| Surface | Correlation | Observed | Interpretation |
|---|---|---:|---|
| Victim authentication log | Invalid run-specific SSH identity | 6 matching records | Host-local action path observed |
| Wazuh manager alert files | Invalid run-specific SSH identity | 6 matching records | Defensive manager path observed |
| Suricata EVE | Kali `172.20.2.35` ↔ victim `172.20.2.20` | 3 correlated events | Network action path observed |
| Wazuh indexer collector | Manual correlation window and identity | 0; collector returned HTTP failure | Indexed-alert visibility gap |

The well-observed action is the invalid SSH activity: victim, Wazuh manager,
and Suricata evidence all align with the participant timestamp and identity.
The visibility gap is indexed Wazuh collection, which returned HTTP failure and
no correlated alert. The run does not relabel manager files, participant
capture, or Suricata events as indexed detections.

## Reset and freshness

`build/reset.sh` returned zero and ran its own health gate. The human then
re-entered through `kali-ssh-proxy`.

| Path ref | Expected | Observed |
|---|---|---|
| `portal_reachable_after_reset` | Portal baseline restored | HTTP 200 |
| `sqli_login_after_reset` | Authored SQLi affordance restored | HTTP 302 |
| `shared_share_reachable_after_reset` | Shared SMB surface restored | SMB command exit 0 |
| `shared_marker_removed` | Run-specific marker cannot satisfy the next run | Marker absent |
| `public_share_content_after_reset` | Authored company content restored | Welcome line present |

The reset removed participant-created Shared state while restoring the authored
portal weakness, shares, and content. No operator deletion or reseeding was
used as participant proof.

## Automated follow-up

The packaged rehearsal ran after the manual path against the same
`operational` profile:

```text
python3 build/rehearsal.py run \
  --run-id tv393-auto-20260729-r1 \
  --report docs/auto-report-393-runtime.md \
  --isolated-docker-host
```

Result: `PASS` (exit 0). Its generated report and raw run store remained on the
disposable host and were destroyed; the immutable #392 report remains the
packaged automated-run detail. The follow-up reproduced the indexed Wazuh
visibility gap but passed the existing manager-evidence fallback, reset,
freshness, and cleanup gates.

After the dependency and evidence commits, the exact committed tree at
`e2d89fd7561cbf0cd54f9fc9fee9646a268b4d68` was archived into a second fresh
issue-tagged EC2 host. The build contract passed there, followed by:

```text
python3 build/rehearsal.py run \
  --run-id tv393-final-20260729-r1 \
  --report docs/final-tree-rehearsal-393-runtime.md \
  --isolated-docker-host
```

Result: `PASS` (exit 0). The cold build created the complete 31-service range,
all health gates cleared, and the rehearsal again passed its action, reset,
freshness, and cleanup checks. It reproduced the already-declared indexed
Wazuh visibility gap and passed via manager evidence. An independent audit
after the wrapper returned zero Compose-project containers, networks, labeled
volumes, and project-prefixed volumes.

Final-tree static, unit, web, catalog, and central pack results are recorded by
the issue/PR workflow and summarized here:

| Final-tree check | Result |
|---|---|
| `python3 scenarios/techvault/build/validate_build.py validate` | PASS |
| `python3 -m unittest discover -s scenarios/techvault/build/tests` | PASS — 38 tests |
| TechVault ACES/profile validator | PASS |
| `raes-pack-validate --pack scenarios/techvault` | PASS — includes scenario-content CI |
| `raes-pack-release check --pack scenarios/techvault` | PASS |
| `npm audit` in the pack-local web source | PASS — zero vulnerabilities |
| `npm test` in the pack-local web source | PASS — 238 tests |

## Teardown

The automated rehearsal invoked `build/cleanup.sh`. An independent post-wrapper
Docker audit returned:

| Residual class | Count |
|---|---:|
| Compose-project containers | 0 |
| Compose-project networks | 0 |
| Compose-project labeled volumes | 0 |
| `techvault_golden_`-prefixed volumes | 0 |

Both EC2 hosts were terminated and their encrypted root volumes deleted. Each
dedicated subnet, route table, security group, internet gateway, VPC, imported
key pair, and local temporary key/archive file was deleted. After the final
committed-tree run, a fresh `GroundControlIssue=393` audit again returned zero
active instances, volumes, VPCs, subnets, gateways, security groups, route
tables, and key pairs.

## Defects and reruns

### D1 — Wazuh generator permissions blocked a clean launch

- Symptom: after the pinned Wazuh generator completed, `render_runtime.py`
  attempted to overwrite and chmod generator-owned certificate files; a clean
  host failed with `PermissionError` before Compose launch.
- Canonical fix: trust the generator-owned certificate set, require its root
  and manager CA files, and preserve its ownership/modes.
- Regression: `test_wazuh_certificate_generation_preserves_generator_permissions`
  failed before the fix and passes after it.
- Rerun: a fresh archive of fixed commit `6aff6d1` passed build validation,
  clean launch, full health, manual journey, reset, automated rehearsal, and
  teardown.

An initial automated-follow-up command supplied a report path outside the
pack’s allowed docs boundary. Argument validation rejected it before Docker was
touched. The report path was corrected and the real automated run passed.

### D2 — Web dependency audit reported sanitizer and toolchain advisories

- Symptom: the required `npm ci` check reported a vulnerable production
  DOMPurify version plus advisories in the build/test graph.
- Canonical fix: update DOMPurify, remove the unused coverage plugin that owned
  the vulnerable coverage-only chain, update compatible Svelte/Vite/Vitest
  locks, and override the SvelteKit cookie transitive to the patched compatible
  release.
- Verification: the existing markdown XSS enforcement tests and all 238 web
  tests pass; `npm audit` reports zero vulnerabilities.
- Live-boundary verification: the fresh isolated-host rehearsal
  `tv393-final-20260729-r1` ran from exact commit `e2d89fd`, passed with exit
  zero, left no TechVault Docker resources, and was followed by complete AWS
  cleanup.

## Run-specific golden-readiness checklist

### Milestone structure

- [x] Scenario contract and pack skeleton exist.
- [x] Topology, assets, and reference-triangle design are complete.
- [x] Hidden-path/objective-oracle work is explicitly not applicable to this
      non-linear, unscored exercise; the authored weakness and human success
      contract are documented.
- [x] Flag, challenge, and CTFd work is explicitly out of scope.
- [x] Guided, unguided, purple-team, and demo bundles exist.
- [x] The `operational` golden build exists and launched in isolated cloud
      infrastructure.
- [x] Packaged automated live rehearsal exists and passed.
- [x] Final manual participant walkthrough is tracked by issue #393 and this
      report.
- [x] Final docs, maturity, evidence, and teardown are reconciled in the #393
      change.

### Golden definition of done

- [x] The range applied from a clean archive of committed pack content.
- [x] No repository-root `.env`, external scenario-content fetch, or
      undocumented manual setup was required.
- [x] The `operational` profile created the participant start state.
- [x] The loopback Kali SSH participant surface existed and was reachable.
- [x] The human issued the happy-path actions manually through that surface.
- [x] Operator channels were limited to provisioning, observation, reset, and
      teardown.
- [x] All declared human success conditions were reached from Kali.
- [x] Objective/oracle/flag surfaces were explicitly not applicable; the
      invalid-login rejection supplied the relevant negative gate.
- [x] Reset removed stale participant state and restored authored state.
- [x] Automated rehearsal passed against the same profile.
- [x] Manual and automated paths agree on stable action/check ids.
- [x] Durable value-sparse evidence is committed in this report.
- [x] Docker and AWS teardown were independently verified.
- [x] `pack.yaml.status` may advance to `golden`.

### Final manual participant walkthrough protocol

- [x] Stand up from the documented build entrypoint.
- [x] Enter only through the participant execution surface.
- [x] Work the intended journey manually, command by command.
- [x] Do not substitute management-plane or harness actions for participant
      actions.
- [x] Fix the discovered certificate-generation defect in code.
- [x] Commit that distinct defect separately.
- [x] Relaunch from a clean fixed commit and rerun the affected launch step.
- [x] Complete the entire participant journey after the fix.
- [x] Run automated rehearsal and relevant final-tree gates.
- [x] Tear down and independently verify cleanup.
- [x] Report manual, observer, automated, not-applicable, and limited surfaces
      separately.

## Limitations

- Indexed Wazuh collection returned HTTP failure and no correlated alerts.
  Manager and Suricata evidence are useful but do not erase that visibility
  gap. This is an exercise finding, not a participant-path failure.
- The terminal driver used for this run did not retain a persistent nested PTY.
  Each action was therefore issued as a separate SSH remote command through the
  same ForceCommand-wrapped Kali participant endpoint. Persistent browser
  terminal UX was not evaluated.
- TechVault remains intentionally non-linear and unscored. Golden status proves
  the declared participant/observer journey and reference build; it does not
  introduce objectives, flags, or a hidden mandatory chain.
