#!/bin/bash
set -euo pipefail

docker exec eval-sandbox test -x /usr/local/bin/claude
output="$(timeout 120 docker exec --user root --workdir /app eval-sandbox bash -lc \
  'claude -p "Reply with OK." --output-format json --tools "" --max-turns 1 --no-session-persistence' \
  2>/dev/null)"
printf '%s' "$output" | python3 -c '
import json, sys
value = json.load(sys.stdin)
if value.get("is_error") or int(value.get("usage", {}).get("output_tokens", 0)) <= 0:
    raise SystemExit(1)
'
echo "AI_ESCAPE_AGENT_READY"
