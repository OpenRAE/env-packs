#!/bin/bash
# OBS-003 (APTL ADR-033 / ADR-041 — this repository's own ADR 0033 is
# unrelated: "resolve pack artifacts through one bounded open") per-session
# shell wrapper invoked by sshd's ForceCommand. Delegates all capture file
# writes to the aptl-kali-capture sidecar daemon via `aptl-capture-client` so
# the kali user (passwordless sudo) cannot delete or modify capture evidence.
#
# Capture is best-effort (issue #282): an authenticated SSH session is never
# denied for a capture-availability reason. Capture activates only when the
# control-plane-issued, single-use session capability is present AND the
# sidecar, script(1), and the private spool FIFO are all available; any
# missing prerequisite degrades the session to unrecorded instead of denying
# access. A capture attempt that starts but fails after the command begins
# still returns the participant command's real exit status — it never
# re-runs the command, and a failed/partial stream is never reported as valid
# evidence.
#
# Capture lifecycle when active (single owning connection — codex pre-push F1/F3):
#   1. aptl-capture-client ping
#      → best-effort reachability probe; capture is skipped, not denied, when
#        the sidecar is unreachable.
#   2. aptl-capture-client stream RUN_ID SESSION_ID (one connection)
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

warn() {
  echo "[aptl-wrap-shell] WARNING: $1; continuing unrecorded" >&2
}

# Run the participant's command (or login shell) with no capture wrapping.
# `exec` replaces this process outright, so sshd sees the command's own exit
# status directly and there is no path back into this script afterward.
exec_uncaptured_shell() {
  if [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
    exec /bin/bash --login -c "$SSH_ORIGINAL_COMMAND"
  else
    exec /bin/bash --login
  fi
}

SESSION_ID="$(safe_id "${APTL_SESSION_ID:-}")"
RUN_ID="$(safe_id "${APTL_RUN_ID:-_unbound}")"

# The capability authorizes a sidecar capture *attempt*; it is never
# authorization for the shell itself, and it must never reach the
# participant's own command environment on any path below.
CAPABILITY="${APTL_CAPTURE_CAPABILITY:-}"
unset APTL_CAPTURE_CAPABILITY

if [ -z "$CAPABILITY" ]; then
  warn "capture capability missing"
  exec_uncaptured_shell
fi

# Reachability is a best-effort check, not an admission gate: an unreachable
# sidecar degrades to an unrecorded shell instead of denying access.
if ! aptl-capture-client ping 2>/dev/null; then
  warn "capture sidecar unavailable"
  exec_uncaptured_shell
fi

if ! command -v script >/dev/null 2>&1; then
  warn "script(1) missing"
  exec_uncaptured_shell
fi

# Clean up the private spool directory on every exit path.
SPOOL_DIR=""
cleanup() {
  [ -n "$SPOOL_DIR" ] && rm -rf "$SPOOL_DIR" 2>/dev/null
  return 0
}
trap cleanup EXIT TERM INT

# A private, race-free temporary directory (rather than a `mktemp -u` path)
# so the FIFO name cannot be pre-created or swapped by another local process
# between naming and creation.
SPOOL_DIR="$(mktemp -d "${TMPDIR:-/tmp}/aptl-cap-XXXXXX" 2>/dev/null)"
if [ -z "$SPOOL_DIR" ]; then
  warn "could not create capture spool"
  exec_uncaptured_shell
fi
SPOOL="$SPOOL_DIR/spool"
if ! mkfifo -m 0600 "$SPOOL" 2>/dev/null; then
  warn "could not create capture spool"
  exec_uncaptured_shell
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
# Start the reader (stream client) first so script's open-for-write rendezvous
# on the FIFO succeeds; it forwards FIFO bytes to the sidecar until EOF. The
# capability is passed only to this command's environment, never exported to
# the current shell, so the participant shell/command below cannot see it.
APTL_CAPTURE_CAPABILITY="$CAPABILITY" aptl-capture-client stream "$RUN_ID" "$SESSION_ID" < "$SPOOL" &
CLIENT_PID=$!

SCRIPT_ARGS=( -q -f --return --log-io "$SPOOL" )
if [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
  script "${SCRIPT_ARGS[@]}" --command "$SSH_ORIGINAL_COMMAND"
else
  script "${SCRIPT_ARGS[@]}" --command "/bin/bash --login"
fi
RC=$?

# script closed the FIFO write end on exit → the client sees EOF, flushes the
# tail, sends session_end, and exits. Wait so finalization completes before we
# return the command's exit status to sshd. A failed/partial stream degrades
# the session to unrecorded — it never re-runs the command or invalidates an
# otherwise-successful participant result, and it is never reported as valid
# evidence.
if ! wait "$CLIENT_PID" 2>/dev/null; then
  warn "capture stream failed after session start"
fi
exit "$RC"
