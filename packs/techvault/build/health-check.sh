#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$SCRIPT_DIR/aptl-runtime"
ENV_FILE="$(python3 "$SCRIPT_DIR/validate_build.py" resolve-operator-env "${TECHVAULT_OPERATOR_ENV:-$SCRIPT_DIR/operator-defaults.env}")"
PROJECT="$(python3 "$SCRIPT_DIR/validate_build.py" validate-project "${TECHVAULT_COMPOSE_PROJECT:-techvault_golden}")"
PROFILES=(wazuh soc enterprise fileshare dns victim kali otel)
SERVICES=(kali kali-ssh-proxy webapp ad db fileshare dns victim workstation wazuh.manager wazuh.indexer wazuh.dashboard suricata misp thehive cortex shuffle-backend aptl-otel-collector)

COMPOSE=(docker compose --env-file "$ENV_FILE" -p "$PROJECT" -f "$RUNTIME_DIR/docker-compose.yml")
for profile in "${PROFILES[@]}"; do
    COMPOSE+=(--profile "$profile")
done

"${COMPOSE[@]}" ps >/dev/null
for service in "${SERVICES[@]}"; do
    status="$("${COMPOSE[@]}" ps --status running --services "$service" 2>/dev/null || true)"
    if [[ "$status" != "$service" ]]; then
        echo "[health] ERROR: $service is not running" >&2
        exit 1
    fi
done

"${COMPOSE[@]}" exec -T kali test -f /run/aptl-kali-ready
"${COMPOSE[@]}" exec -T kali ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i /host-ssh-keys/kali_pivot_key labadmin@172.20.2.20 true

echo "[health] TechVault participant start surface and core services are reachable."
