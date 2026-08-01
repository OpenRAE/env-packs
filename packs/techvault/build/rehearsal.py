#!/usr/bin/env python3
"""Run TechVault's automated live rehearsal for issue #392."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import yaml


BUILD_ROOT = Path(__file__).resolve().parent
PACK_ROOT = BUILD_ROOT.parent
RUNTIME_ROOT = BUILD_ROOT / "aptl-runtime"
APTL_SRC = RUNTIME_ROOT / "src"
DEFAULT_ENV = BUILD_ROOT / "operator-defaults.env"
DEFAULT_PROJECT = "techvault_golden"
DEFAULT_REPORT = PACK_ROOT / "docs" / "rehearsal-report-392.md"
PROFILE = "operational"
SCENARIO = "techvault"
PROFILES = ("wazuh", "soc", "enterprise", "fileshare", "dns", "victim", "kali", "otel")
CHECK_LINE_RE = re.compile(r"^REHEARSAL_CHECK\s+([a-z0-9_.-]+)\s+(ok|fail)\s*$")
NEGATIVE_TELEMETRY_IDENTITY_PREFIX = "aptl-live-gate-invalid"
KALI_INTERNAL_IP = "172.20.2.35"
VICTIM_IP = "172.20.2.20"
NEGATIVE_TELEMETRY_PORTS = {22, 80, 443, 445}

CHECK_CATEGORIES = {
    "isolated_docker_host_attested": "backend_instantiation",
    "operator_inputs_validated": "backend_instantiation",
    "setup_launch": "backend_instantiation",
    "setup_health": "defensive_stack_readiness",
    "participant_start_surface": "kali_reachability",
    "portal_reachable": "kali_reachability",
    "negative_invalid_login_rejected": "kali_reachability",
    "sqli_login_accepted": "kali_reachability",
    "dashboard_reachable": "kali_reachability",
    "admin_surface_reachable": "kali_reachability",
    "web_upload_created": "kali_reachability",
    "public_share_content": "kali_reachability",
    "shared_marker_created": "kali_reachability",
    "telemetry_negative_ssh_generated": "kali_reachability",
    "objectives_oracle_flags_not_declared": "aces_specification",
    "telemetry_evidence_path": "evidence_capture",
    "reset_lifecycle": "backend_instantiation",
    "portal_reachable_after_reset": "kali_reachability",
    "sqli_login_after_reset": "kali_reachability",
    "shared_share_reachable_after_reset": "kali_reachability",
    "public_share_content_after_reset": "kali_reachability",
    "shared_marker_removed": "kali_reachability",
    "cleanup_lifecycle": "backend_instantiation",
    "cleanup_no_residual_resources": "evidence_capture",
    "report_written": "evidence_capture",
    "orchestration_error": "evidence_capture",
}

INITIAL_PARTICIPANT_CHECKS = (
    "portal_reachable",
    "negative_invalid_login_rejected",
    "sqli_login_accepted",
    "dashboard_reachable",
    "admin_surface_reachable",
    "web_upload_created",
    "public_share_content",
    "shared_marker_created",
)
NEGATIVE_TELEMETRY_CHECKS = (
    "telemetry_negative_ssh_generated",
)
RESET_PARTICIPANT_CHECKS = (
    "portal_reachable_after_reset",
    "sqli_login_after_reset",
    "shared_share_reachable_after_reset",
    "public_share_content_after_reset",
    "shared_marker_removed",
)

if str(BUILD_ROOT) not in sys.path:
    sys.path.insert(0, str(BUILD_ROOT))

from render_runtime import _load_env  # noqa: E402
from validate_build import resolve_operator_env, validate_compose_project  # noqa: E402


class CommandRunner(Protocol):
    def run(
        self,
        args: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        input_text: str | None = None,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        ...


class SubprocessRunner:
    def run(
        self,
        args: list[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        input_text: str | None = None,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=cwd,
            env=env,
            input=input_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )


@dataclass
class RehearsalOptions:
    run_id: str
    project: str
    env_file: Path
    report_path: Path
    isolated_docker_host: bool
    telemetry_window_seconds: int
    marker: str


@dataclass
class RehearsalContext:
    options: RehearsalOptions
    runner: CommandRunner
    store: Any
    checks: list[Any] = field(default_factory=list)
    commands: list[dict[str, Any]] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    blocked: bool = False
    kali_proxy_port: int | None = None


class RunnerBackend:
    """Small adapter so APTL collectors can use this harness' command runner."""

    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    def container_exec(
        self,
        container: str,
        cmd: list[str],
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        return self._runner.run(
            ["docker", "exec", container, *cmd],
            cwd=PACK_ROOT,
            timeout=timeout,
        )


def _add_aptl_src() -> None:
    if str(APTL_SRC) not in sys.path:
        sys.path.insert(0, str(APTL_SRC))


_add_aptl_src()
from aptl.core.runstore import LocalRunStore, _validate_id as aptl_validate_id  # noqa: E402
from aptl.utils.redaction import redact  # noqa: E402
from aptl.validation.techvault_live_gate import LiveGateCheck, LiveGateReport  # noqa: E402


def _live_gate_classes() -> tuple[type[Any], type[Any]]:
    return LiveGateCheck, LiveGateReport


def _redact(value: Any) -> Any:
    return redact(value)


def _validate_id(value: str, kind: str) -> str:
    return aptl_validate_id(value, kind)


def _run_store() -> Any:
    return LocalRunStore(RUNTIME_ROOT / "runs")


def _make_check(name: str, passed: bool, diagnostics: list[str] | None = None) -> Any:
    live_gate_check, _report = _live_gate_classes()
    category = CHECK_CATEGORIES.get(name, "evidence_capture")
    safe_diagnostics = tuple(str(_redact(item)) for item in diagnostics or [])
    return live_gate_check(name, category, passed, safe_diagnostics)


def _check_to_dict(check: Any) -> dict[str, Any]:
    return {
        "name": check.name,
        "category": check.category,
        "ok": bool(check.passed),
        "diagnostics": list(check.diagnostics),
    }


def _record_check(
    ctx: RehearsalContext,
    name: str,
    passed: bool,
    diagnostics: list[str] | None = None,
) -> None:
    ctx.checks.append(_make_check(name, passed, diagnostics))


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PACK_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _resolve_report_path(value: str | Path | None) -> Path:
    raw = Path(value) if value is not None else DEFAULT_REPORT
    root = PACK_ROOT.resolve(strict=True)
    docs_root = (root / "docs").resolve(strict=True)
    candidate = raw if raw.is_absolute() else root / raw
    parent = candidate.parent.resolve(strict=True)
    try:
        parent.relative_to(docs_root)
    except ValueError as exc:
        raise ValueError("report path must stay under scenarios/techvault/docs") from exc
    if candidate.is_symlink():
        raise ValueError("report path must not be a symlink")
    if candidate.suffix != ".md":
        raise ValueError("report path must be a Markdown file")
    return candidate


def _default_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"tv392-{stamp}-{uuid.uuid4().hex[:8]}"


def _default_marker() -> str:
    return f"tv392-{uuid.uuid4().hex[:12]}"


def _lifecycle_env(ctx: RehearsalContext) -> dict[str, str]:
    env = os.environ.copy()
    env["TECHVAULT_OPERATOR_ENV"] = str(ctx.options.env_file)
    env["TECHVAULT_COMPOSE_PROJECT"] = ctx.options.project
    return env


def _compose_base(ctx: RehearsalContext) -> list[str]:
    cmd = [
        "docker",
        "compose",
        "--env-file",
        str(ctx.options.env_file),
        "-p",
        ctx.options.project,
        "-f",
        str(RUNTIME_ROOT / "docker-compose.yml"),
    ]
    for profile in PROFILES:
        cmd.extend(["--profile", profile])
    return cmd


def _run_command(
    ctx: RehearsalContext,
    command_id: str,
    args: list[str],
    *,
    timeout: int,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    started = time.monotonic()
    try:
        result = ctx.runner.run(
            args,
            cwd=PACK_ROOT,
            env=env,
            input_text=input_text,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        ctx.commands.append(
            {
                "id": command_id,
                "argv0": Path(args[0]).name,
                "returncode": "timeout",
                "elapsed_seconds": round(elapsed, 3),
            }
        )
        raise
    elapsed = time.monotonic() - started
    ctx.commands.append(
        {
            "id": command_id,
            "argv0": Path(args[0]).name,
            "returncode": result.returncode,
            "elapsed_seconds": round(elapsed, 3),
        }
    )
    return result


def _run_wrapper(ctx: RehearsalContext, check_name: str, script_name: str, timeout: int) -> bool:
    try:
        result = _run_command(
            ctx,
            check_name,
            ["bash", str(BUILD_ROOT / script_name)],
            env=_lifecycle_env(ctx),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        _record_check(ctx, check_name, False, [f"{script_name} timed out after {timeout}s"])
        return False
    except OSError as exc:
        _record_check(ctx, check_name, False, [f"{script_name} execution failed: {_redact(str(exc))}"])
        return False
    if result.returncode == 0:
        _record_check(ctx, check_name, True)
        return True
    _record_check(ctx, check_name, False, [f"{script_name} exited {result.returncode}"])
    return False


def _parse_proxy_port(stdout: str) -> int:
    first = stdout.strip().splitlines()[0] if stdout.strip() else ""
    if not first:
        raise ValueError("kali-ssh-proxy port output was empty")
    host, sep, port_text = first.rpartition(":")
    if not sep or host not in {"127.0.0.1", "localhost", "[::1]", "::1"}:
        raise ValueError("kali-ssh-proxy must publish on loopback")
    port = int(port_text)
    if not 1 <= port <= 65535:
        raise ValueError("kali-ssh-proxy port is outside TCP range")
    return port


def _resolve_kali_proxy(ctx: RehearsalContext) -> int | None:
    result = _run_command(
        ctx,
        "participant_start_surface",
        [*_compose_base(ctx), "port", "kali-ssh-proxy", "2023"],
        env=_lifecycle_env(ctx),
        timeout=30,
    )
    if result.returncode != 0:
        _record_check(ctx, "participant_start_surface", False, ["kali-ssh-proxy port lookup failed"])
        return None
    try:
        port = _parse_proxy_port(result.stdout)
    except (IndexError, TypeError, ValueError) as exc:
        _record_check(ctx, "participant_start_surface", False, [str(exc)])
        return None
    ctx.kali_proxy_port = port
    _record_check(ctx, "participant_start_surface", True)
    return port


def _ssh_args(port: int) -> list[str]:
    return [
        "ssh",
        "-i",
        str(BUILD_ROOT / ".operator" / "ssh" / "aptl_lab_key"),
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "SendEnv=APTL_RUN_ID",
        "-o",
        "SendEnv=APTL_SESSION_ID",
        "-o",
        "SendEnv=APTL_TRACE_ID",
        "kali@127.0.0.1",
        "bash -s",
    ]


def _ssh_command_args(port: int, command: str) -> list[str]:
    args = _ssh_args(port)[:-1]
    args.append(f"bash -lc {shlex.quote(command)}")
    return args


def _participant_env(ctx: RehearsalContext, phase: str) -> dict[str, str]:
    env = os.environ.copy()
    env["APTL_RUN_ID"] = ctx.options.run_id
    env["APTL_TRACE_ID"] = ctx.options.run_id
    env["APTL_SESSION_ID"] = f"{ctx.options.run_id}-{phase}"
    return env


def _parse_participant_checks(stdout: str) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for line in stdout.splitlines():
        match = CHECK_LINE_RE.match(line.strip())
        if match:
            checks[match.group(1)] = match.group(2) == "ok"
    return checks


def _run_participant_script(
    ctx: RehearsalContext,
    phase: str,
    expected: tuple[str, ...],
    script: str,
    *,
    timeout: int,
) -> bool:
    port = ctx.kali_proxy_port or _resolve_kali_proxy(ctx)
    if port is None:
        for check_name in expected:
            _record_check(ctx, check_name, False, ["participant SSH surface unavailable"])
        return False
    try:
        result = _run_command(
            ctx,
            f"participant_{phase}",
            _ssh_args(port),
            env=_participant_env(ctx, phase),
            input_text=script,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        for check_name in expected:
            _record_check(ctx, check_name, False, [f"{phase} participant SSH command timed out"])
        return False
    except OSError as exc:
        for check_name in expected:
            _record_check(ctx, check_name, False, [f"{phase} participant SSH execution failed: {_redact(str(exc))}"])
        return False
    observed = _parse_participant_checks(result.stdout)
    ctx.evidence.setdefault("participant", {})[phase] = {
        "returncode": result.returncode,
        "checks": observed,
    }
    process_ok = result.returncode == 0
    checks_ok = all(observed.get(check_name) is True for check_name in expected)
    ok = process_ok and checks_ok
    for check_name in expected:
        passed = process_ok and observed.get(check_name) is True
        diagnostics = []
        if not passed:
            if not process_ok:
                diagnostics.append(f"{phase} participant SSH command exited {result.returncode}")
            if observed.get(check_name) is not True:
                diagnostics.append(f"{phase} participant check did not pass")
        _record_check(ctx, check_name, passed, diagnostics)
    return ok


def _run_participant_command(
    ctx: RehearsalContext,
    phase: str,
    expected: tuple[str, ...],
    command: str,
    *,
    timeout: int,
) -> bool:
    port = ctx.kali_proxy_port or _resolve_kali_proxy(ctx)
    if port is None:
        for check_name in expected:
            _record_check(ctx, check_name, False, ["participant SSH surface unavailable"])
        return False
    try:
        result = _run_command(
            ctx,
            f"participant_{phase}",
            _ssh_command_args(port, command),
            env=_participant_env(ctx, phase),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        for check_name in expected:
            _record_check(ctx, check_name, False, [f"{phase} participant SSH command timed out"])
        return False
    except OSError as exc:
        for check_name in expected:
            _record_check(ctx, check_name, False, [f"{phase} participant SSH execution failed: {_redact(str(exc))}"])
        return False
    observed = _parse_participant_checks(result.stdout)
    ctx.evidence.setdefault("participant", {})[phase] = {
        "returncode": result.returncode,
        "checks": observed,
    }
    process_ok = result.returncode == 0
    checks_ok = all(observed.get(check_name) is True for check_name in expected)
    ok = process_ok and checks_ok
    for check_name in expected:
        passed = process_ok and observed.get(check_name) is True
        diagnostics = []
        if not passed:
            if not process_ok:
                diagnostics.append(f"{phase} participant SSH command exited {result.returncode}")
            if observed.get(check_name) is not True:
                diagnostics.append(f"{phase} participant check did not pass")
        _record_check(ctx, check_name, passed, diagnostics)
    return ok


def _initial_participant_script(marker: str) -> str:
    return f"""set -euo pipefail
ok() {{ printf 'REHEARSAL_CHECK %s ok\\n' "$1"; }}
fail() {{ printf 'REHEARSAL_CHECK %s fail\\n' "$1"; exit 20; }}
MARKER="{marker}"
PORTAL="http://172.20.1.20:8080"
COOKIE="/tmp/${{MARKER}}.cookies"
TMP="/tmp/${{MARKER}}"
rm -f "$COOKIE" "$TMP".*
status="$(curl -sS -o "$TMP.index" -w "%{{http_code}}" "$PORTAL/")"
case "$status" in 200|302) ok portal_reachable ;; *) fail portal_reachable ;; esac
status="$(curl -sS -o "$TMP.invalid" -w "%{{http_code}}" -X POST \
  --data-urlencode "username=invalid-${{MARKER}}" \
  --data-urlencode "password=not-the-password" "$PORTAL/login")"
[ "$status" = "401" ] && ok negative_invalid_login_rejected || fail negative_invalid_login_rejected
status="$(curl -sS -o "$TMP.sqli" -w "%{{http_code}}" -c "$COOKIE" -b "$COOKIE" -X POST \
  --data-urlencode "username=' OR '1'='1' --" \
  --data-urlencode "password=not-used" "$PORTAL/login")"
[ "$status" = "302" ] && ok sqli_login_accepted || fail sqli_login_accepted
status="$(curl -sS -o "$TMP.dashboard" -w "%{{http_code}}" -b "$COOKIE" "$PORTAL/dashboard")"
[ "$status" = "200" ] && ok dashboard_reachable || fail dashboard_reachable
status="$(curl -sS -o "$TMP.admin" -w "%{{http_code}}" -b "$COOKIE" "$PORTAL/admin")"
[ "$status" = "200" ] && ok admin_surface_reachable || fail admin_surface_reachable
printf 'TechVault rehearsal marker: %s\\n' "$MARKER" > "$TMP.marker.txt"
status="$(curl -sS -o "$TMP.upload" -w "%{{http_code}}" -b "$COOKIE" \
  -F "file=@$TMP.marker.txt;filename=${{MARKER}}.txt" "$PORTAL/upload")"
[ "$status" = "302" ] && ok web_upload_created || fail web_upload_created
smbclient //172.20.2.12/Public -N -c "get welcome.txt $TMP.public.txt" </dev/null > "$TMP.smb-public" 2>&1 \
  || fail public_share_content
grep -F "Welcome to TechVault Solutions file server." "$TMP.public.txt" >/dev/null \
  && ok public_share_content || fail public_share_content
smbclient //172.20.2.12/Shared -N -c "put $TMP.marker.txt ${{MARKER}}.txt" </dev/null > "$TMP.smb-put" 2>&1 \
  || fail shared_marker_created
smbclient //172.20.2.12/Shared -N -c "ls ${{MARKER}}.txt" </dev/null > "$TMP.smb-ls" 2>&1 \
  || fail shared_marker_created
grep -F "${{MARKER}}.txt" "$TMP.smb-ls" >/dev/null \
  && ok shared_marker_created || fail shared_marker_created
"""


def _negative_telemetry_command() -> str:
    return f"""
set -u
ok() {{ printf 'REHEARSAL_CHECK %s ok\\n' "$1"; }}
fail() {{ printf 'REHEARSAL_CHECK %s fail\\n' "$1"; exit 21; }}
TMP="/tmp/aptl-negative-telemetry-${{APTL_SESSION_ID:-manual}}"
IDENTITY="{NEGATIVE_TELEMETRY_IDENTITY_PREFIX}-${{APTL_RUN_ID:-manual}}"
for attempt in 1 2 3; do
  ssh -n -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o NumberOfPasswordPrompts=0 -o ConnectTimeout=3 \
    "${{IDENTITY}}@{VICTIM_IP}" true >/dev/null 2>&1 || true
done
nmap -Pn -T4 -p 22,80,443,445 {VICTIM_IP} </dev/null > "$TMP.nmap" 2>&1 \
  || fail telemetry_negative_ssh_generated
grep -Eq '^(22|80|443|445)/tcp[[:space:]]+(open|closed|filtered)' "$TMP.nmap" \
  || fail telemetry_negative_ssh_generated
ok telemetry_negative_ssh_generated
"""


def _reset_participant_script(marker: str) -> str:
    return f"""set -euo pipefail
ok() {{ printf 'REHEARSAL_CHECK %s ok\\n' "$1"; }}
fail() {{ printf 'REHEARSAL_CHECK %s fail\\n' "$1"; exit 20; }}
MARKER="{marker}"
PORTAL="http://172.20.1.20:8080"
COOKIE="/tmp/${{MARKER}}.reset.cookies"
TMP="/tmp/${{MARKER}}.reset"
rm -f "$COOKIE" "$TMP".*
status="$(curl -sS -o "$TMP.index" -w "%{{http_code}}" "$PORTAL/")"
case "$status" in 200|302) ok portal_reachable_after_reset ;; *) fail portal_reachable_after_reset ;; esac
status="$(curl -sS -o "$TMP.sqli" -w "%{{http_code}}" -c "$COOKIE" -b "$COOKIE" -X POST \
  --data-urlencode "username=' OR '1'='1' --" \
  --data-urlencode "password=not-used" "$PORTAL/login")"
[ "$status" = "302" ] && ok sqli_login_after_reset || fail sqli_login_after_reset
smbclient //172.20.2.12/Shared -N -c "ls" </dev/null > "$TMP.shared-ls" 2>&1 \
  && ok shared_share_reachable_after_reset || fail shared_share_reachable_after_reset
if grep -F "${{MARKER}}.txt" "$TMP.shared-ls" >/dev/null; then
  fail shared_marker_removed
fi
ok shared_marker_removed
smbclient //172.20.2.12/Public -N -c "get welcome.txt $TMP.public.txt" </dev/null > "$TMP.smb-public" 2>&1 \
  || fail public_share_content_after_reset
grep -F "Welcome to TechVault Solutions file server." "$TMP.public.txt" >/dev/null \
  && ok public_share_content_after_reset || fail public_share_content_after_reset
"""


def _objectives_oracle_flags_check(ctx: RehearsalContext) -> None:
    try:
        pack = yaml.safe_load((PACK_ROOT / "pack.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        _record_check(ctx, "objectives_oracle_flags_not_declared", False, [f"pack.yaml parse failed: {exc}"])
        return
    diagnostics: list[str] = []
    if pack.get("flags"):
        diagnostics.append("pack.yaml declares flags, so issue #392 cannot treat flags as N/A")
    objectives = pack.get("objectives") or pack.get("oracle")
    if objectives:
        diagnostics.append("pack.yaml declares scored objectives/oracle, so issue #392 cannot treat them as N/A")
    _record_check(ctx, "objectives_oracle_flags_not_declared", not diagnostics, diagnostics)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _negative_telemetry_identity(run_id: str) -> str:
    return f"{NEGATIVE_TELEMETRY_IDENTITY_PREFIX}-{_validate_id(run_id, 'run_id')}"


def _collect_until_evidence(
    backend: RunnerBackend,
    start_iso: str,
    window_seconds: int,
    *,
    indexer_url: str,
    indexer_auth: tuple[str, str],
    identity: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _add_aptl_src()
    from aptl.core.collectors import collect_suricata_eve, collect_wazuh_alerts

    steps = max(1, window_seconds // 10)
    eve: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    for _step in range(steps):
        time.sleep(10)
        now = _now_iso()
        eve = collect_suricata_eve(start_iso, now, backend)
        alerts = collect_wazuh_alerts(start_iso, now, indexer_url=indexer_url, auth=indexer_auth)
        if any(_is_correlated_wazuh_alert(alert, identity) for alert in alerts):
            break
    return eve, alerts


def _event_type_tally(eve: list[dict[str, Any]]) -> dict[str, int]:
    tally: dict[str, int] = {}
    for entry in eve:
        event_type = str(entry.get("event_type", "unknown")) if isinstance(entry, dict) else "unknown"
        tally[event_type] = tally.get(event_type, 0) + 1
    return tally


def _int_field(entry: dict[str, Any], name: str) -> int | None:
    try:
        return int(entry[name])
    except (KeyError, TypeError, ValueError):
        return None


def _is_correlated_suricata_event(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    src_ip = str(entry.get("src_ip", ""))
    dest_ip = str(entry.get("dest_ip", ""))
    src_port = _int_field(entry, "src_port")
    dest_port = _int_field(entry, "dest_port")
    if src_ip == KALI_INTERNAL_IP and dest_ip == VICTIM_IP:
        return dest_port in NEGATIVE_TELEMETRY_PORTS
    if src_ip == VICTIM_IP and dest_ip == KALI_INTERNAL_IP:
        return src_port in NEGATIVE_TELEMETRY_PORTS
    return False


def _nested_strings(value: object) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, dict):
        for nested in value.values():
            strings.extend(_nested_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            strings.extend(_nested_strings(nested))
    return strings


def _is_correlated_wazuh_alert(alert: object, identity: str) -> bool:
    return isinstance(alert, dict) and any(
        identity in value for value in _nested_strings(alert)
    )


def _wazuh_alert_digest(alert: dict[str, Any]) -> str:
    canonical = json.dumps(alert, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _collect_victim_auth_log_evidence(backend: RunnerBackend, identity: str) -> dict[str, Any]:
    command = (
        "grep -h -F -- "
        f"{shlex.quote(identity)} "
        "/var/log/secure /var/log/auth.log 2>/dev/null | tail -n 20"
    )
    try:
        result = backend.container_exec("aptl-victim", ["sh", "-lc", command], timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "collection_failed", "error": _redact(str(exc))}
    lines = [line for line in result.stdout.splitlines() if identity in line]
    evidence: dict[str, Any] = {
        "status": "observed" if lines else "not_observed",
        "match_count": len(lines),
    }
    if lines:
        canonical = "\n".join(lines).encode("utf-8")
        evidence["sha256"] = hashlib.sha256(canonical).hexdigest()
    elif result.returncode not in (0, 1):
        evidence["error"] = f"victim auth log grep exited {result.returncode}"
    return evidence


def _collect_wazuh_manager_alert_evidence(backend: RunnerBackend, identity: str) -> dict[str, Any]:
    command = (
        "grep -h -F -- "
        f"{shlex.quote(identity)} "
        "/var/ossec/logs/alerts/alerts.json /var/ossec/logs/alerts/alerts.log 2>/dev/null | tail -n 20"
    )
    try:
        result = backend.container_exec("aptl-wazuh-manager", ["sh", "-lc", command], timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "collection_failed", "error": _redact(str(exc))}
    lines = [line for line in result.stdout.splitlines() if identity in line]
    evidence: dict[str, Any] = {
        "status": "observed" if lines else "not_observed",
        "match_count": len(lines),
    }
    if lines:
        canonical = "\n".join(lines).encode("utf-8")
        evidence["sha256"] = hashlib.sha256(canonical).hexdigest()
    elif result.returncode not in (0, 1):
        evidence["error"] = f"Wazuh manager alert grep exited {result.returncode}"
    return evidence


def _collect_telemetry(ctx: RehearsalContext, start_iso: str) -> None:
    identity = _negative_telemetry_identity(ctx.options.run_id)
    backend = RunnerBackend(ctx.runner)
    try:
        values = _load_env(ctx.options.env_file)
        username = values["INDEXER_USERNAME"]
        password = values["INDEXER_PASSWORD"]
        indexer_port = int(values.get("APTL_HP_WAZUH_INDEXER_9200", "9200"))
        if not 1 <= indexer_port <= 65535:
            raise ValueError("invalid Wazuh indexer port")
        eve, alerts = _collect_until_evidence(
            backend,
            start_iso,
            ctx.options.telemetry_window_seconds,
            indexer_url=f"https://localhost:{indexer_port}",
            indexer_auth=(username, password),
            identity=identity,
        )
    except Exception as exc:
        ctx.evidence["telemetry"] = {"status": "collection_failed"}
        _record_check(ctx, "telemetry_evidence_path", False, [f"telemetry collection failed: {exc}"])
        return
    correlated = [alert for alert in alerts if _is_correlated_wazuh_alert(alert, identity)]
    correlated_eve = [entry for entry in eve if _is_correlated_suricata_event(entry)]
    wazuh_manager_alert = _collect_wazuh_manager_alert_evidence(backend, identity)
    wazuh_manager_alert_present = wazuh_manager_alert.get("match_count", 0) > 0
    victim_auth_log = _collect_victim_auth_log_evidence(backend, identity)
    telemetry_present = bool(correlated) or wazuh_manager_alert_present
    summary: dict[str, Any] = {
        "window_start": start_iso,
        "window_end": _now_iso(),
        "suricata_event_count": len(eve),
        "suricata_correlated_event_count": len(correlated_eve),
        "suricata_correlated_event_types": _event_type_tally(correlated_eve),
        "wazuh_alert_count": len(alerts),
        "wazuh_correlated_alert_count": len(correlated),
        "wazuh_manager_alert": wazuh_manager_alert,
        "victim_auth_log": victim_auth_log,
    }
    if correlated:
        summary["first_correlated_alert_sha256"] = _wazuh_alert_digest(correlated[0])
    ctx.evidence["telemetry"] = summary
    _record_check(
        ctx,
        "telemetry_evidence_path",
        telemetry_present,
        []
        if telemetry_present
        else [
            "no run-specific Wazuh indexer or manager alert observed; "
            "Suricata and victim-local logs are supporting evidence only"
        ],
    )


def _cleanup_residuals(ctx: RehearsalContext) -> None:
    project = ctx.options.project
    resources: dict[str, list[str]] = {}
    queries = {
        "containers": ["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={project}", "--format", "{{.Names}}"],
        "networks": ["docker", "network", "ls", "--filter", f"label=com.docker.compose.project={project}", "--format", "{{.Name}}"],
        "volumes_labeled": ["docker", "volume", "ls", "--filter", f"label=com.docker.compose.project={project}", "--format", "{{.Name}}"],
        "volumes_all": ["docker", "volume", "ls", "--format", "{{.Name}}"],
    }
    failed = False
    for name, args in queries.items():
        try:
            result = _run_command(ctx, f"cleanup_probe_{name}", args, timeout=60)
        except subprocess.TimeoutExpired:
            resources[name] = ["probe_timeout"]
            failed = True
            continue
        except OSError as exc:
            resources[name] = [f"probe_error:{_redact(str(exc))}"]
            failed = True
            continue
        if result.returncode != 0:
            resources[name] = ["probe_failed"]
            failed = True
            continue
        rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if name == "volumes_all":
            rows = [row for row in rows if row.startswith(f"{project}_")]
            name = "volumes_project_prefix"
        resources[name] = rows
    ctx.evidence["cleanup_residuals"] = resources
    residuals = [item for rows in resources.values() for item in rows]
    _record_check(
        ctx,
        "cleanup_no_residual_resources",
        not failed and not residuals,
        [] if not failed and not residuals else [f"residual project resources: {', '.join(residuals[:8])}"],
    )


def _build_report(ctx: RehearsalContext) -> Any:
    _check, live_gate_report = _live_gate_classes()
    return live_gate_report(
        scenario=SCENARIO,
        profile=PROFILE,
        run_id=ctx.options.run_id,
        checks=tuple(ctx.checks),
    )


def _status(ctx: RehearsalContext, report: Any) -> str:
    if ctx.blocked:
        return "BLOCKED"
    return "PASS" if report.passed else "FAIL"


def _write_manifest_and_report(ctx: RehearsalContext) -> Any:
    report = _build_report(ctx)
    finished_at = datetime.now(timezone.utc)
    manifest = {
        "scenario": SCENARIO,
        "profile": PROFILE,
        "run_id": ctx.options.run_id,
        "status": _status(ctx, report),
        "started_at": ctx.started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - ctx.started_at).total_seconds(), 3),
        "operator_config": {
            "path": _relative(ctx.options.env_file),
            "compose_project": ctx.options.project,
        },
        "checks": [_check_to_dict(check) for check in ctx.checks],
        "commands": ctx.commands,
        "evidence": ctx.evidence,
    }
    ctx.store.write_json(ctx.options.run_id, "manifest.json", manifest)
    report_text = _render_markdown_report(ctx, manifest)
    ctx.options.report_path.write_text(report_text, encoding="utf-8")
    _record_check(ctx, "report_written", True)
    report = _build_report(ctx)
    manifest["checks"] = [_check_to_dict(check) for check in ctx.checks]
    ctx.store.write_json(ctx.options.run_id, "manifest.json", manifest)
    ctx.options.report_path.write_text(_render_markdown_report(ctx, manifest), encoding="utf-8")
    return report


def _render_markdown_report(ctx: RehearsalContext, manifest: dict[str, Any]) -> str:
    report = _build_report(ctx)
    status = _status(ctx, report)
    checks = [_check_to_dict(check) for check in ctx.checks]
    lines = [
        "# TechVault Automated Live Rehearsal Report (#392)",
        "",
        f"- Status: `{status}`",
        f"- Scenario: `{SCENARIO}`",
        f"- Profile: `{PROFILE}`",
        f"- Run id: `{ctx.options.run_id}`",
        f"- Compose project: `{ctx.options.project}`",
        f"- Operator config: `{_relative(ctx.options.env_file)}`",
        f"- Runtime archive: `{_relative(ctx.store.get_run_path(ctx.options.run_id))}`",
        f"- Updated: `{manifest['finished_at']}`",
        "",
        "## Boundary",
        "",
        "Participant actions use the loopback `kali-ssh-proxy` SSH surface and execute on ACES `kali`.",
        "Operator commands are limited to launch, health observation, telemetry collection, reset, cleanup, and teardown verification.",
        "The report records stable check ids, counts, timings, and digests; raw service payloads, credential values, flags, and command output stay out of the committed document.",
        "",
        "## Objective and Flag Handling",
        "",
        "TechVault currently declares no scored objective oracle and no pack-level flags in `pack.yaml`.",
        "The rehearsal therefore records those surfaces as not applicable and does not invent or seed objectives, flags, users, services, or data.",
        "",
        "## Checks",
        "",
        "| Check | Category | Result | Diagnostics |",
        "| --- | --- | --- | --- |",
    ]
    for check in checks:
        diagnostics = "; ".join(check["diagnostics"]) if check["diagnostics"] else ""
        lines.append(
            f"| `{check['name']}` | `{check['category']}` | "
            f"`{'PASS' if check['ok'] else 'FAIL'}` | {diagnostics} |"
        )
    lines.extend(
        [
            "",
            "## Future Manual Walkthrough Alignment",
            "",
            "The automated path is aligned to the #393 manual walkthrough boundary: start at Kali, prove portal reachability, prove a rejected login, exploit the declared SQLi path, touch the admin surface, read in-world share content, create participant state, reset, and prove stale participant state is gone.",
            "Issue #393 remains the human command-by-command walkthrough gate; this automated report does not replace it and does not promote TechVault status by itself.",
        ]
    )
    if status == "BLOCKED":
        lines.extend(
            [
                "",
                "## Blocker",
                "",
                "The rehearsal was not launched because the operator did not attest to a disposable isolated Docker host. TechVault publishes vulnerable services, uses fixed container names/subnets, and includes Docker-socket consumers; it must not be run as proof on a shared long-lived daemon.",
            ]
        )
    telemetry = manifest.get("evidence", {}).get("telemetry")
    if telemetry:
        lines.extend(
            [
                "",
                "## Telemetry Summary",
                "",
                "```json",
                json.dumps(_redact(telemetry), indent=2, sort_keys=True, default=str),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def run_rehearsal(options: RehearsalOptions, runner: CommandRunner | None = None) -> Any:
    _validate_id(options.run_id, "run_id")
    _validate_id(options.marker, "marker")
    store = _run_store()
    store.create_run(options.run_id)
    ctx = RehearsalContext(options=options, runner=runner or SubprocessRunner(), store=store)
    ctx.evidence["host_attestation"] = {"isolated_docker_host": options.isolated_docker_host}
    _record_check(ctx, "operator_inputs_validated", True)
    if not options.isolated_docker_host:
        ctx.blocked = True
        _record_check(
            ctx,
            "isolated_docker_host_attested",
            False,
            ["pass --isolated-docker-host only on a disposable isolated Docker host"],
        )
        return _write_manifest_and_report(ctx)
    _record_check(ctx, "isolated_docker_host_attested", True)
    launch_attempted = False
    launch_succeeded = False
    try:
        launch_attempted = True
        launch_succeeded = _run_wrapper(ctx, "setup_launch", "launch.sh", 3600)
        if launch_succeeded:
            _run_wrapper(ctx, "setup_health", "health-check.sh", 600)
            telemetry_start = _now_iso()
            initial_ok = _run_participant_script(
                ctx,
                "initial",
                INITIAL_PARTICIPANT_CHECKS,
                _initial_participant_script(options.marker),
                timeout=900,
            )
            telemetry_generated = False
            if initial_ok:
                telemetry_generated = _run_participant_command(
                    ctx,
                    "negative_telemetry",
                    NEGATIVE_TELEMETRY_CHECKS,
                    _negative_telemetry_command(),
                    timeout=120,
                )
            if initial_ok and telemetry_generated:
                _objectives_oracle_flags_check(ctx)
                _collect_telemetry(ctx, telemetry_start)
                reset_ok = _run_wrapper(ctx, "reset_lifecycle", "reset.sh", 1800)
                if reset_ok:
                    _run_participant_script(
                        ctx,
                        "reset",
                        RESET_PARTICIPANT_CHECKS,
                        _reset_participant_script(options.marker),
                        timeout=600,
                    )
    except Exception as exc:
        _record_check(ctx, "orchestration_error", False, [f"unhandled rehearsal error: {_redact(str(exc))}"])
    finally:
        if launch_attempted:
            try:
                _run_wrapper(ctx, "cleanup_lifecycle", "cleanup.sh", 600)
            finally:
                try:
                    _cleanup_residuals(ctx)
                except Exception as exc:
                    _record_check(
                        ctx,
                        "cleanup_no_residual_resources",
                        False,
                        [f"residual verification failed: {_redact(str(exc))}"],
                    )
    return _write_manifest_and_report(ctx)


def _build_options(args: argparse.Namespace) -> RehearsalOptions:
    env_file = resolve_operator_env(args.operator_env)
    project = validate_compose_project(args.project)
    run_id = _validate_id(args.run_id or _default_run_id(), "run_id")
    marker = _validate_id(args.marker or _default_marker(), "marker")
    report_path = _resolve_report_path(args.report)
    if args.telemetry_window_seconds < 10:
        raise ValueError("telemetry window must be at least 10 seconds")
    return RehearsalOptions(
        run_id=run_id,
        project=project,
        env_file=env_file,
        report_path=report_path,
        isolated_docker_host=args.isolated_docker_host,
        telemetry_window_seconds=args.telemetry_window_seconds,
        marker=marker,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--run-id")
    run_parser.add_argument("--marker")
    run_parser.add_argument("--project", default=os.environ.get("TECHVAULT_COMPOSE_PROJECT", DEFAULT_PROJECT))
    run_parser.add_argument("--operator-env", default=os.environ.get("TECHVAULT_OPERATOR_ENV", str(DEFAULT_ENV)))
    run_parser.add_argument("--report", default=str(DEFAULT_REPORT))
    run_parser.add_argument("--telemetry-window-seconds", type=int, default=180)
    run_parser.add_argument(
        "--isolated-docker-host",
        action="store_true",
        help="Required attestation before launching the live vulnerable range.",
    )
    args = parser.parse_args()
    if (args.command or "run") != "run":
        parser.error("unknown command")
    try:
        options = _build_options(args)
        report = run_rehearsal(options)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(_render_cli_summary(report))
    return 0 if report.passed else 1


def _render_cli_summary(report: Any) -> str:
    status = "PASS" if report.passed else "FAIL"
    failed = [check.name for check in report.failures()]
    if failed:
        return f"TechVault rehearsal {status}: failing checks: {', '.join(failed)}"
    return f"TechVault rehearsal {status}: all checks passed"


if __name__ == "__main__":
    raise SystemExit(main())
