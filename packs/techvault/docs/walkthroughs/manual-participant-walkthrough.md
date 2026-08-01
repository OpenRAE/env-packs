# TechVault manual participant walkthrough

This is the reusable command-by-command walkthrough for the `operational`
profile. It aligns with the stable check ids in `build/rehearsal.py`, but it is
performed by a human and does not invoke that harness as proof.

TechVault is a non-linear purple-team exercise. It has no scored objective
oracle, mandatory exploit chain, flag board, or completion token. The manual
success contract is the participant brief and guided checkpoints: establish a
timestamped activity record, demonstrate normal and vulnerable portal
behavior, learn in-world enterprise context, create non-destructive participant
state, and compare the red actions with defensive observations.

## Boundaries

- Run on one disposable, isolated Docker daemon. The fixed container and subnet
  identities do not support a shared daemon or concurrent TechVault projects.
- Use only `build/launch.sh`, `build/health-check.sh`, `build/reset.sh`, and
  `build/cleanup.sh` for lifecycle changes.
- Participant actions execute as `kali` through the loopback-only
  `kali-ssh-proxy`. Do not substitute `docker compose exec`, root, a service
  console, a database console, or the automated rehearsal.
- Operator access may validate, launch, observe, reset, and tear down. Keep
  those observations separate from participant evidence.
- Do not commit cookies, private keys, environment values, raw HTTP bodies,
  terminal captures, Docker output, service logs, or generated runtime state.

## Operator setup

From `scenarios/techvault/` in a clean checkout:

```bash
python3 build/validate_build.py validate
export TECHVAULT_COMPOSE_PROJECT=techvault_golden
./build/launch.sh
./build/health-check.sh
```

Resolve the participant connector without reading the operator environment:

```bash
PROXY_PORT="$(
  docker compose \
    --env-file build/operator-defaults.env \
    -p "$TECHVAULT_COMPOSE_PROJECT" \
    -f build/aptl-runtime/docker-compose.yml \
    --profile wazuh --profile soc --profile enterprise --profile fileshare \
    --profile dns --profile victim --profile kali --profile otel \
    port kali-ssh-proxy 2023 |
  sed -n 's/^127\.0\.0\.1://p'
)"
test -n "$PROXY_PORT"

RUN_ID="tv393-manual-YYYYMMDD-rN"
PARTICIPANT_KEY="$PWD/build/.operator/ssh/aptl_lab_key"
PARTICIPANT_SSH=(
  ssh -i "$PARTICIPANT_KEY" -p "$PROXY_PORT"
  -o BatchMode=yes
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
  -o SendEnv=APTL_RUN_ID
  -o SendEnv=APTL_SESSION_ID
  kali@127.0.0.1
)
export APTL_RUN_ID="$RUN_ID"
```

The private key path is operator transport material. Never print, copy into
Kali, or include its contents in a transcript or report.

## Participant evidence

Run each command separately. Preserve only the bounded result named below.

### Identity, time, and exposure

```bash
export APTL_SESSION_ID="$RUN_ID-identity"
"${PARTICIPANT_SSH[@]}" 'whoami; hostname; date -u +%Y-%m-%dT%H:%M:%SZ'
```

Expected: user `kali` on the Kali participant node and a UTC timestamp.

```bash
export APTL_SESSION_ID="$RUN_ID-exposure"
"${PARTICIPANT_SSH[@]}" 'ip -brief address show scope global; ip route show'
```

Expected: the authored DMZ, internal, and red-team paths are visible from Kali.
This is contextual evidence, not a topology authority.

### Portal baseline and negative authentication

```bash
export APTL_SESSION_ID="$RUN_ID-portal-baseline"
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.index" -w "portal_reachable=%{http_code}\n" http://172.20.1.20:8080/'
```

Expected: `portal_reachable=200` (a redirect is also acceptable if the provider
changes its unauthenticated landing behavior).

```bash
export APTL_SESSION_ID="$RUN_ID-invalid-login"
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.invalid" -w "negative_invalid_login_rejected=%{http_code}\n" -X POST --data-urlencode "username=invalid-$APTL_RUN_ID" --data-urlencode "password=not-the-password" http://172.20.1.20:8080/login'
```

Expected: `negative_invalid_login_rejected=401`.

### Authored SQL injection and authenticated surfaces

```bash
export APTL_SESSION_ID="$RUN_ID-sqli-login"
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.sqli" -w "sqli_login_accepted=%{http_code}\n" -c "/tmp/$APTL_RUN_ID.cookies" -b "/tmp/$APTL_RUN_ID.cookies" -X POST --data-urlencode "username='\'' OR '\''1'\''='\''1'\'' --" --data-urlencode "password=not-used" http://172.20.1.20:8080/login'
```

Expected: `sqli_login_accepted=302`.

```bash
export APTL_SESSION_ID="$RUN_ID-dashboard"
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.dashboard" -w "dashboard_reachable=%{http_code}\n" -b "/tmp/$APTL_RUN_ID.cookies" http://172.20.1.20:8080/dashboard'
```

Expected: `dashboard_reachable=200`. A bounded heading/count/role excerpt may
be inspected for enterprise context; do not copy the full response.

```bash
export APTL_SESSION_ID="$RUN_ID-admin"
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.admin" -w "admin_surface_reachable=%{http_code}\n" -b "/tmp/$APTL_RUN_ID.cookies" http://172.20.1.20:8080/admin'
```

Expected: `admin_surface_reachable=200`. The page contains intentionally
sensitive synthetic training data, so record only the status.

### Participant-created web and SMB state

```bash
export APTL_SESSION_ID="$RUN_ID-upload"
"${PARTICIPANT_SSH[@]}" \
  'printf "TechVault manual marker: %s\n" "$APTL_RUN_ID" > "/tmp/$APTL_RUN_ID.marker.txt"'
```

```bash
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.upload" -w "web_upload_created=%{http_code}\n" -b "/tmp/$APTL_RUN_ID.cookies" -F "file=@/tmp/$APTL_RUN_ID.marker.txt;filename=$APTL_RUN_ID.txt" http://172.20.1.20:8080/upload'
```

Expected: `web_upload_created=302`.

```bash
export APTL_SESSION_ID="$RUN_ID-public-share"
"${PARTICIPANT_SSH[@]}" \
  'smbclient //172.20.2.12/Public -N -c "get welcome.txt /tmp/$APTL_RUN_ID.public.txt" </dev/null >/tmp/$APTL_RUN_ID.smb-public 2>&1; grep -F "Welcome to TechVault Solutions file server." "/tmp/$APTL_RUN_ID.public.txt"'
```

Expected: `public_share_content` is proven by the authored welcome line.

```bash
export APTL_SESSION_ID="$RUN_ID-shared-state"
"${PARTICIPANT_SSH[@]}" \
  'smbclient //172.20.2.12/Shared -N -c "put /tmp/$APTL_RUN_ID.marker.txt $APTL_RUN_ID.txt" </dev/null >/tmp/$APTL_RUN_ID.smb-put 2>&1'
```

```bash
"${PARTICIPANT_SSH[@]}" \
  'smbclient //172.20.2.12/Shared -N -c "ls $APTL_RUN_ID.txt" </dev/null 2>/dev/null | grep -F "$APTL_RUN_ID.txt"'
```

Expected: `shared_marker_created` is proven by the named marker entry.

### Bounded telemetry-generating activity

Set a telemetry session, then type the failed-SSH command three separate times.

```bash
export APTL_SESSION_ID="$RUN_ID-telemetry"
"${PARTICIPANT_SSH[@]}" \
  'ssh -n -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o NumberOfPasswordPrompts=0 -o ConnectTimeout=3 "invalid-$APTL_RUN_ID@172.20.2.20" true >/dev/null 2>&1; printf "telemetry_negative_ssh_generated=%s\n" "$?"'
```

Expected each time: exit `255`, showing the invalid identity was rejected.

```bash
"${PARTICIPANT_SSH[@]}" \
  'nmap -Pn -T4 -p 22,80,443,445 172.20.2.20 | awk "/^(22|80|443|445)\\/tcp/ {print \$1, \$2}"'
```

Expected: a bounded four-port result for the in-range victim. Together these
actions satisfy `telemetry_negative_ssh_generated`.

## Observer evidence

Use operator access only after the red actions. Record counts, not raw log
lines.

```bash
docker exec aptl-victim sh -lc \
  "grep -h -F -- 'invalid-$RUN_ID' /var/log/secure /var/log/auth.log 2>/dev/null | wc -l"

docker exec aptl-wazuh-manager sh -lc \
  "grep -h -F -- 'invalid-$RUN_ID' /var/ossec/logs/alerts/alerts.json /var/ossec/logs/alerts/alerts.log 2>/dev/null | wc -l"

docker exec aptl-suricata sh -lc \
  "grep -F '172.20.2.35' /var/log/suricata/eve.json 2>/dev/null | grep -F '172.20.2.20' | wc -l"
```

Use the existing `aptl.core.collectors.collect_wazuh_alerts` adapter for the
same time window when checking indexed Wazuh evidence. Load credentials from
the validated operator file in-process; never put them in argv or output.

The comparison must identify at least one well-observed action and one
visibility gap. A victim log, participant capture, or Suricata event does not
become an indexed Wazuh alert merely because it exists.

## Reset and freshness

Record the marker as present before reset, then use the wrapper:

```bash
./build/reset.sh
```

Re-enter through the same participant connector.

```bash
export APTL_SESSION_ID="$RUN_ID-post-reset"
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.reset.index" -w "portal_reachable_after_reset=%{http_code}\n" http://172.20.1.20:8080/'
```

Expected: `portal_reachable_after_reset=200`.

```bash
"${PARTICIPANT_SSH[@]}" \
  'curl -sS -o "/tmp/$APTL_RUN_ID.reset.sqli" -w "sqli_login_after_reset=%{http_code}\n" -c "/tmp/$APTL_RUN_ID.reset.cookies" -b "/tmp/$APTL_RUN_ID.reset.cookies" -X POST --data-urlencode "username='\'' OR '\''1'\''='\''1'\'' --" --data-urlencode "password=not-used" http://172.20.1.20:8080/login'
```

Expected: `sqli_login_after_reset=302`.

```bash
"${PARTICIPANT_SSH[@]}" \
  'smbclient //172.20.2.12/Shared -N -c "ls" </dev/null > "/tmp/$APTL_RUN_ID.reset.shared-ls" 2>&1'
```

```bash
"${PARTICIPANT_SSH[@]}" \
  'if grep -F "$APTL_RUN_ID.txt" "/tmp/$APTL_RUN_ID.reset.shared-ls" >/dev/null; then exit 1; else echo shared_marker_removed; fi'
```

Expected: the share is reachable and `shared_marker_removed` is printed.

```bash
"${PARTICIPANT_SSH[@]}" \
  'smbclient //172.20.2.12/Public -N -c "get welcome.txt /tmp/$APTL_RUN_ID.reset.public.txt" </dev/null >/tmp/$APTL_RUN_ID.reset.smb-public 2>&1; grep -F "Welcome to TechVault Solutions file server." "/tmp/$APTL_RUN_ID.reset.public.txt"'
```

Expected: `public_share_content_after_reset` is proven by the authored welcome
line.

## Automated follow-up and teardown

After the manual path succeeds:

```bash
python3 build/rehearsal.py run --isolated-docker-host
python3 -m unittest discover -s build/tests
python3 profiles/validate_profiles.py validate
```

Run repository and central pack gates from the repository root. Then clean up:

```bash
./build/cleanup.sh
```

Independently prove zero residuals for the validated project:

```bash
docker ps -a \
  --filter "label=com.docker.compose.project=$TECHVAULT_COMPOSE_PROJECT" \
  --format '{{.Names}}'
docker network ls \
  --filter "label=com.docker.compose.project=$TECHVAULT_COMPOSE_PROJECT" \
  --format '{{.Name}}'
docker volume ls \
  --filter "label=com.docker.compose.project=$TECHVAULT_COMPOSE_PROJECT" \
  --format '{{.Name}}'
docker volume ls --format '{{.Name}}' |
  awk -v prefix="${TECHVAULT_COMPOSE_PROJECT}_" 'index($0, prefix) == 1'
```

All four outputs must be empty. Destroy the disposable host and its isolated
network, then verify no tagged live infrastructure remains.
