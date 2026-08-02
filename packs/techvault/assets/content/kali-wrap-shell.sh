#!/bin/bash
# OBS-003 / ADR-033 / ADR-041 per-session shell wrapper invoked by sshd's
# ForceCommand.  Delegates all capture file writes to the aptl-kali-capture
# sidecar daemon via `aptl-capture-client` so the kali user (passwordless
# sudo) cannot delete or modify capture evidence.
#
# Capture lifecycle (single owning connection — codex pre-push F1/F3):
#   1. Require the control-plane-issued, single-use session capability.
#   2. aptl-capture-client ping
#      → mandatory reachability probe; denies access when capture is unavailable.
#   3. aptl-capture-client stream RUN_ID SESSION_ID (one connection)
#      → sends session_start, forwards script(1)'s --log-io transcript as
#        pty_chunk frames, then session_end on EOF. The sidecar binds the
#        capability to the declared run/session and this connection, rejects
#        missing/invalid/replayed capabilities, and acknowledges both admission
#        and finalization.
#
# The Kali container does NOT mount the captures volume (ADR-041) and does NOT
# share the sidecar's PID namespace: all writes happen in the sidecar, so a
# sudo-capable agent cannot read, delete, or alter any session's evidence.
# This wrapper never touches a capture file directly.
#
# If any capture prerequisite is unavailable, the ForceCommand denies the
# session. An authenticated participant must never receive an unrecorded shell.
#
# ID validation:
#   Canonical rule: `^[A-Za-z0-9_][A-Za-z0-9._-]*$` AND no `..`.
#   Must match src/aptl/core/runstore.py _ID_RE and
#   mcp/aptl-mcp-common/src/runs.ts ID_RE.

set -u
umask 077

valid_id() {
  case "$1" in
    *..* | */* | "" ) return 1 ;;
    *) ;;
  esac
  printf '%s' "$1" | LC_ALL=C grep -Eq '^[A-Za-z0-9_][A-Za-z0-9._-]*$'
}

safe_id() {
  local raw="${1:-}"
  if valid_id "$raw"; then
    printf '%s' "$raw"
  else
    printf 'anon-%s-%s' "$(date +%s)" "$$"
  fi
}

SESSION_ID="$(safe_id "${APTL_SESSION_ID:-}")"
RUN_ID="$(safe_id "${APTL_RUN_ID:-_unbound}")"

if [ -z "${APTL_CAPTURE_CAPABILITY:-}" ]; then
  echo "[aptl-wrap-shell] capture capability missing; access denied" >&2
  exit 70
fi

# Reachability is a hard admission gate. This runs before either an interactive
# shell or SSH_ORIGINAL_COMMAND is executed.
if ! aptl-capture-client ping 2>/dev/null; then
  echo "[aptl-wrap-shell] capture sidecar unavailable; access denied" >&2
  exit 70
fi

# Clean up the spool FIFO on every exit path.
SPOOL=""
cleanup() {
  [ -n "$SPOOL" ] && rm -f "$SPOOL" 2>/dev/null
  return 0
}
trap cleanup EXIT TERM INT

if ! command -v script >/dev/null 2>&1; then
  echo "[aptl-wrap-shell] script(1) missing; access denied" >&2
  exit 70
fi

# Route script(1)'s --log-io transcript to the sidecar through a private FIFO.
# `script`'s own stdout/stdin stay wired to the SSH channel so the agent sees
# output and `kali_run_command` returns the real result — only the transcript
# is forwarded. (Piping script's stdout into the client instead would send all
# output to the sidecar and return an EMPTY result to the caller.)
#
# One `stream` client owns the whole session on a SINGLE connection
# (session_start -> pty_chunks -> session_end), so finalization cannot race a
# separate "end" call and a killed wrapper still gets EOF-driven finalization
# in the sidecar (codex pre-push F1/F3). We `wait` for the client so every
# pty_chunk is flushed before the wrapper exits (no tail loss). The FIFO only
# carries this session's own bytes in transit; the written evidence lives in
# the sidecar, out of this container's mount namespace.
#
# `script -q` suppresses the banner; `-f` flushes each write; `--return`
# propagates the wrapped command's exit status (correct result semantics + OCSF
# outcome); `--log-io` records combined input+output (non-echoed input such as
# `read -s` passwords included).
SPOOL="$(mktemp -u "${TMPDIR:-/tmp}/aptl-cap-XXXXXX")"
if ! mkfifo -m 0600 "$SPOOL" 2>/dev/null; then
  echo "[aptl-wrap-shell] could not create capture spool; access denied" >&2
  exit 70
fi

# Start the reader (stream client) first so script's open-for-write rendezvous
# on the FIFO succeeds; it forwards FIFO bytes to the sidecar until EOF.
aptl-capture-client stream "$RUN_ID" "$SESSION_ID" < "$SPOOL" &
CLIENT_PID=$!
# The capability is only needed by the already-started capture client. Do not
# expose it to the participant shell or command environment.
unset APTL_CAPTURE_CAPABILITY

SCRIPT_ARGS=( -q -f --return --log-io "$SPOOL" )
if [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
  script "${SCRIPT_ARGS[@]}" --command "$SSH_ORIGINAL_COMMAND"
else
  script "${SCRIPT_ARGS[@]}" --command "/bin/bash --login"
fi
RC=$?

# script closed the FIFO write end on exit → the client sees EOF, flushes the
# tail, sends session_end, and exits. Wait so finalization completes before we
# return the command's exit status to sshd.
if ! wait "$CLIENT_PID" 2>/dev/null; then
  echo "[aptl-wrap-shell] capture stream failed; session invalid" >&2
  exit 70
fi
exit "$RC"
