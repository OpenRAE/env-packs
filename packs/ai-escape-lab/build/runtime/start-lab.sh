#!/bin/bash
set -euo pipefail

ROOT=/opt/ai-escape-lab
RUNTIME=/run/ai-escape-lab
METADATA=http://169.254.169.254/computeMetadata/v1
mode="${1:---runtime}"
case "$mode" in
  --bake|--runtime) ;;
  *) echo "usage: start-lab.sh [--bake|--runtime]" >&2; exit 2 ;;
esac
mkdir -p "$RUNTIME"
chmod 0700 "$RUNTIME"
rm -f "$RUNTIME/ready"

metadata() {
  curl --fail --silent --show-error --max-time 3 \
    -H 'Metadata-Flavor: Google' "$METADATA/$1"
}

if [[ "$mode" == --bake ]]; then
  project=build-probe
else
  project="$(metadata project/project-id)"
fi
model_region="${AI_ESCAPE_MODEL_REGION:-us-east5}"
if [[ "$mode" == --runtime && ! "$project" =~ ^[a-z][a-z0-9-]{4,62}$ ]]; then
  echo "AI Escape Lab: invalid metadata project identity" >&2
  exit 1
fi
if [[ ! "$model_region" =~ ^[a-z]+-[a-z]+[0-9]+$ ]]; then
  echo "AI Escape Lab: invalid model region" >&2
  exit 1
fi

umask 077
cat > "$RUNTIME/agent.env" <<EOF
ANTHROPIC_VERTEX_PROJECT_ID=$project
CLOUD_ML_REGION=$model_region
ANTHROPIC_MODEL=claude-sonnet-4-6
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-6
ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-4-5
EOF
export MODEL_REGION="$model_region"

docker compose --project-name ai-escape-room --file "$ROOT/docker-compose.yml" \
  up --detach --pull never --no-build --remove-orphans
"$ROOT/readiness.sh" "$mode"
if [[ "$mode" == --runtime ]]; then
  "$ROOT/probe-agent.sh"
fi
touch "$RUNTIME/ready"
