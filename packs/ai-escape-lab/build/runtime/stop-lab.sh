#!/bin/bash
set -euo pipefail

rm -f /run/ai-escape-lab/ready
docker compose --project-name ai-escape-room --file /opt/ai-escape-lab/docker-compose.yml \
  down --volumes --remove-orphans --timeout 15
