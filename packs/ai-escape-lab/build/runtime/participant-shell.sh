#!/bin/bash
set -euo pipefail

if [[ "${SSH_ORIGINAL_COMMAND:-}" != "" ]]; then
  echo "AI Escape Lab provides an interactive terminal only." >&2
  exit 2
fi

args=(exec --interactive --user root --workdir /app)
if [[ -t 0 && -t 1 ]]; then
  args+=(--tty)
fi
exec sudo --non-interactive /usr/local/sbin/ai-escape-enter "${args[@]}" eval-sandbox bash --login
