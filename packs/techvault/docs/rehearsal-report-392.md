# TechVault Automated Live Rehearsal Report (#392)

- Status: `PASS`
- Scenario: `techvault`
- Profile: `operational`
- Run id: `tv392-live-20260721-r6`
- Compose project: `techvault_golden`
- Operator config: `build/operator-defaults.env`
- Runtime archive: `build/aptl-runtime/runs/tv392-live-20260721-r6`
- Updated: `2026-07-21T00:32:16.450111+00:00`

## Boundary

Participant actions use the loopback `kali-ssh-proxy` SSH surface and execute on ACES `kali`.
Operator commands are limited to launch, health observation, telemetry collection, reset, cleanup, and teardown verification.
The report records stable check ids, counts, timings, and digests; raw service payloads, credential values, flags, and command output stay out of the committed document.

## Objective and Flag Handling

TechVault currently declares no scored objective oracle and no pack-level flags in `pack.yaml`.
The rehearsal therefore records those surfaces as not applicable and does not invent or seed objectives, flags, users, services, or data.

## Checks

| Check | Category | Result | Diagnostics |
| --- | --- | --- | --- |
| `operator_inputs_validated` | `backend_instantiation` | `PASS` |  |
| `isolated_docker_host_attested` | `backend_instantiation` | `PASS` |  |
| `setup_launch` | `backend_instantiation` | `PASS` |  |
| `setup_health` | `defensive_stack_readiness` | `PASS` |  |
| `participant_start_surface` | `kali_reachability` | `PASS` |  |
| `portal_reachable` | `kali_reachability` | `PASS` |  |
| `negative_invalid_login_rejected` | `kali_reachability` | `PASS` |  |
| `sqli_login_accepted` | `kali_reachability` | `PASS` |  |
| `dashboard_reachable` | `kali_reachability` | `PASS` |  |
| `admin_surface_reachable` | `kali_reachability` | `PASS` |  |
| `web_upload_created` | `kali_reachability` | `PASS` |  |
| `public_share_content` | `kali_reachability` | `PASS` |  |
| `shared_marker_created` | `kali_reachability` | `PASS` |  |
| `telemetry_negative_ssh_generated` | `kali_reachability` | `PASS` |  |
| `objectives_oracle_flags_not_declared` | `aces_specification` | `PASS` |  |
| `telemetry_evidence_path` | `evidence_capture` | `PASS` |  |
| `reset_lifecycle` | `backend_instantiation` | `PASS` |  |
| `portal_reachable_after_reset` | `kali_reachability` | `PASS` |  |
| `sqli_login_after_reset` | `kali_reachability` | `PASS` |  |
| `shared_share_reachable_after_reset` | `kali_reachability` | `PASS` |  |
| `public_share_content_after_reset` | `kali_reachability` | `PASS` |  |
| `shared_marker_removed` | `kali_reachability` | `PASS` |  |
| `cleanup_lifecycle` | `backend_instantiation` | `PASS` |  |
| `cleanup_no_residual_resources` | `evidence_capture` | `PASS` |  |
| `report_written` | `evidence_capture` | `PASS` |  |

## Future Manual Walkthrough Alignment

The automated path is aligned to the #393 manual walkthrough boundary: start at Kali, prove portal reachability, prove a rejected login, exploit the declared SQLi path, touch the admin surface, read in-world share content, create participant state, reset, and prove stale participant state is gone.
Issue #393 remains the human command-by-command walkthrough gate; this automated report does not replace it and does not promote TechVault status by itself.

## Telemetry Summary

```json
{
  "suricata_correlated_event_count": 0,
  "suricata_correlated_event_types": {},
  "suricata_event_count": 23,
  "victim_auth_log": {
    "match_count": 6,
    "sha256": "2da8a4bdc494c28d8e730da2e039aab86c4e34f0134191a93263ae431899930b",
    "status": "observed"
  },
  "wazuh_alert_count": 0,
  "wazuh_correlated_alert_count": 0,
  "wazuh_manager_alert": {
    "match_count": 6,
    "sha256": "529af599b243d77ef2ddd87a32ddfbe54daa4a1fa33fd76a569dbb3ad2c6d8c5",
    "status": "observed"
  },
  "window_end": "2026-07-21T00:29:55.390039+00:00",
  "window_start": "2026-07-21T00:26:47.498007+00:00"
}
```
