#!/usr/bin/env python3
"""End-to-end persona walkthroughs for the scaffold wizard (issue #189).

This is a *manual* integration harness. It is deliberately kept out of the
`tests/` tree so the normal CI suite (`unittest discover -s tests`) does not run
it — running it exercises the real shipped commands as subprocesses and takes a
few seconds per persona. Run it by hand and attach the output as evidence; see
`docs/development/wizard-integration-runbook.md`.

Unlike the unit tests, this drives the actual command-line programs end to end:
it invokes ``python -m raes_env_packs.wizard`` to scaffold a pack into a real
catalog directory, then ``python -m raes_env_packs.check`` to prove the pack a
consumer receives passes the same static check. It covers one non-developer task
per primary persona (hub ADR 0003), the machine-readable replay mode, and the
no-silent-overwrite guarantee.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

# One non-developer task per primary persona (route + optional layers).
PERSONAS: dict[str, tuple[str, list[str]]] = {
    "ai-researcher": ("ai-agent-eval", []),
    "security-researcher": ("security-exercise", []),
    "dr-resilience-practitioner": ("dr-recovery", []),
    "product-test-engineer": ("product-integration", []),
    "ai-engineer": ("runnable-local", ["--with", "compatibility"]),
}


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_REPO / "src"), env.get("PYTHONPATH", "")])
    return env


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", *args],
        cwd=str(_REPO), env=_env(), capture_output=True, text=True, **kwargs)


def _catalog() -> Path:
    catalog = Path(tempfile.mkdtemp(prefix="wizard-int-"))
    (catalog / ".git").mkdir()
    (catalog / "environments").mkdir()
    return catalog


class _Result:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        mark = "PASS" if condition else "FAIL"
        print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not condition else ""))
        if condition:
            self.passed += 1
        else:
            self.failed += 1


def _walk_persona(result: _Result, persona: str, route: str, layers: list[str]) -> None:
    print(f"\n== persona: {persona} (route {route}) ==")
    catalog = _catalog()
    pack_id = f"{persona}-pack"
    created = _run([
        "raes_env_packs.wizard", pack_id, "--route", route, *layers,
        "--repo", str(catalog), "--yes"])
    result.check(f"{persona}: wizard exited 0", created.returncode == 0,
                 created.stderr.strip())
    pack_dir = catalog / "environments" / pack_id
    result.check(f"{persona}: pack directory created", pack_dir.is_dir())

    checked = _run(["raes_env_packs.check", str(pack_dir)])
    result.check(f"{persona}: raes-pack-check OK", checked.returncode == 0,
                 checked.stdout.strip() + checked.stderr.strip())
    result.check(f"{persona}: check reports OK", "OK" in checked.stdout)

    # No silent overwrite: a second run against the same target must fail.
    again = _run([
        "raes_env_packs.wizard", pack_id, "--route", route, *layers,
        "--repo", str(catalog), "--yes"])
    result.check(f"{persona}: refuses to overwrite existing pack",
                 again.returncode != 0)


def _walk_replay(result: _Result) -> None:
    print("\n== machine-readable replay (Hub/MCP contract) ==")
    catalog = _catalog()
    payload = json.dumps({
        "version": "raes-pack-wizard-input/v1",
        "pack_id": "replay-pack",
        "route": "minimal",
    })
    done = _run(
        ["raes_env_packs.wizard", "--repo", str(catalog), "--replay", "-", "--json"],
        input=payload)
    result.check("replay: wizard exited 0", done.returncode == 0, done.stderr.strip())
    try:
        document = json.loads(done.stdout)
    except json.JSONDecodeError:
        document = {}
    result.check("replay: emits versioned document",
                 document.get("version") == "raes-pack-wizard/v1")
    checked = _run(["raes_env_packs.check",
                    str(catalog / "environments" / "replay-pack")])
    result.check("replay: produced pack passes check", checked.returncode == 0)


def main() -> int:
    print("Scaffold wizard — end-to-end persona walkthroughs")
    print(f"repo: {_REPO}")
    result = _Result()
    for persona, (route, layers) in PERSONAS.items():
        _walk_persona(result, persona, route, layers)
    _walk_replay(result)
    print(f"\n{result.passed} passed, {result.failed} failed")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
