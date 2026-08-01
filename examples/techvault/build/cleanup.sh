#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$SCRIPT_DIR/aptl-runtime"
ENV_FILE="$(python3 "$SCRIPT_DIR/validate_build.py" resolve-operator-env "${TECHVAULT_OPERATOR_ENV:-$SCRIPT_DIR/operator-defaults.env}")"
PROJECT="$(python3 "$SCRIPT_DIR/validate_build.py" validate-project "${TECHVAULT_COMPOSE_PROJECT:-techvault_golden}")"
PROFILES=(wazuh soc enterprise fileshare dns victim kali otel)

COMPOSE=(docker compose --env-file "$ENV_FILE" -p "$PROJECT" -f "$RUNTIME_DIR/docker-compose.yml")
for profile in "${PROFILES[@]}"; do
    COMPOSE+=(--profile "$profile")
done

"${COMPOSE[@]}" down -v --remove-orphans
docker volume rm "${PROJECT}_suricata_config_seed" "${PROJECT}_suricata_misp_rules" >/dev/null 2>&1 || true
echo "[cleanup] TechVault compose project removed: $PROJECT"
