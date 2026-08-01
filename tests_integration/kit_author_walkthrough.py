#!/usr/bin/env python3
"""Executable multi-kit author walkthrough for issue #190.

This manual integration harness drives the shipped wizard, kit, validation, and
release command modules against an explicitly staged local kit catalog. It
never acquires content, calls a backend, or executes catalog code.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from raes_env_packs.digest import validate_pack_content_manifest

_REPO = Path(__file__).resolve().parents[1]
_VERSION = "1.0.0"
_KITS = (
    ("infrastructure.windows-active-directory-domain-controller", "directory"),
    ("infrastructure.browser-workstation", "workstation"),
    ("infrastructure.authoritative-dns-service", "dns"),
    ("infrastructure.application-api-service", "application"),
    ("infrastructure.postgresql-database", "database"),
)


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_REPO / "src"), env.get("PYTHONPATH", "")]
    )
    return env


def _run(module: str, args: list[str], *, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=str(_REPO),
        env=_env(),
        input=stdin,
        capture_output=True,
        text=True,
    )


class Result:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        mark = "PASS" if condition else "FAIL"
        suffix = f" — {detail}" if detail and not condition else ""
        print(f"  [{mark}] {label}{suffix}")
        self.passed += int(condition)
        self.failed += int(not condition)

    def command(self, label: str, completed: subprocess.CompletedProcess) -> None:
        detail = (completed.stderr or completed.stdout).strip()
        self.check(label, completed.returncode == 0, detail)


def _revision(catalog: Path, supplied: str | None) -> str:
    if supplied:
        return supplied
    completed = subprocess.run(
        ["git", "-C", str(catalog), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _source(catalog: Path, revision: str) -> list[str]:
    return [
        str(catalog),
        "--source-id",
        "reference",
        "--source-revision",
        revision,
    ]


def _kit(args: list[str], *, parameters: dict[str, object] | None = None) -> subprocess.CompletedProcess:
    stdin = json.dumps(parameters) if parameters is not None else None
    return _run("raes_env_packs.kit_cli", args, stdin=stdin)


def _parameters(label: str) -> dict[str, object]:
    return {"deployment_profile": "standard", "service_label": label}


def _json(completed: subprocess.CompletedProcess) -> object:
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def _walk(result: Result, catalog: Path, revision: str, workspace: Path) -> None:
    print("\n== create a minimal ordinary pack ==")
    author_repo = workspace / "catalog"
    (author_repo / ".git").mkdir(parents=True)
    (author_repo / "environments").mkdir()
    created = _run(
        "raes_env_packs.wizard",
        ["realistic-lab", "--route", "minimal", "--repo", str(author_repo), "--yes"],
    )
    result.command("minimal pack created", created)
    pack = author_repo / "environments" / "realistic-lab"
    checklist = pack / "docs" / "golden-readiness-checklist.md"
    checklist.parent.mkdir(parents=True, exist_ok=True)
    checklist.write_text(
        "# Golden readiness checklist\n\n"
        "This draft authoring pack makes no golden-runtime claim.\n\n"
        "## Golden Definition Of Done\n\n"
        "- [ ] A backend-specific reference build is intentionally out of scope.\n\n"
        "## Final Manual Participant Walkthrough Protocol\n\n"
        "- [ ] No runtime walkthrough is claimed by this authoring demonstration.\n",
        encoding="utf-8",
    )

    print("\n== discover and inspect ==")
    listed = _kit(["list", *_source(catalog, revision), "--json"])
    result.command("catalog listed", listed)
    entries = _json(listed)
    result.check("all initial releases are discoverable", isinstance(entries, list) and len(entries) == 38)
    searched = _kit(["search", *_source(catalog, revision), "domain controller", "--json"])
    result.command("catalog searched", searched)
    result.check("search returns identity infrastructure", bool(_json(searched)))
    inspected = _kit(
        [
            "inspect",
            *_source(catalog, revision),
            _KITS[0][0],
            _VERSION,
            "--json",
        ]
    )
    result.command("exact release inspected", inspected)
    inspection = _json(inspected)
    result.check(
        "inspection derives parameters and topology",
        isinstance(inspection, dict)
        and isinstance(inspection.get("module"), dict)
        and bool(inspection["module"].get("parameters"))
        and bool(inspection.get("topology")),
    )

    print("\n== preview, then compose five infrastructure kits ==")
    first_id, first_namespace = _KITS[0]
    previewed = _kit(
        [
            "add",
            str(pack),
            *_source(catalog, revision),
            first_id,
            _VERSION,
            "--namespace",
            first_namespace,
            "--target-sdl",
            "sdl/realistic-lab.sdl.yaml",
            "--parameters",
            "-",
            "--preview",
            "--json",
        ],
        parameters=_parameters(first_namespace),
    )
    result.command("first add previewed", previewed)
    result.check("preview wrote nothing", not (pack / "kit.materializations.json").exists())

    for kit_id, namespace in _KITS:
        added = _kit(
            [
                "add",
                str(pack),
                *_source(catalog, revision),
                kit_id,
                _VERSION,
                "--namespace",
                namespace,
                "--target-sdl",
                "sdl/realistic-lab.sdl.yaml",
                "--parameters",
                "-",
                "--json",
            ],
            parameters=_parameters(namespace),
        )
        result.command(f"added {namespace}", added)

    ledger = json.loads((pack / "kit.materializations.json").read_text(encoding="utf-8"))
    lock = json.loads((pack / "sdl" / "raes.lock.json").read_text(encoding="utf-8"))
    manifest = validate_pack_content_manifest(pack)
    result.check("five exact materializations recorded", len(ledger["materializations"]) == 5)
    result.check("RAES lock records all module resolutions", len(lock["imports"]) == 5)
    result.check("RAES associated-artifact identity validates", bool(manifest.set_digest))

    validated = _run("raes_env_packs.content_ci", ["--pack", str(pack)])
    result.command("composed pack passes trusted author validation", validated)

    print("\n== update, replace, and remove transactionally ==")
    updated = _kit(
        [
            "update",
            str(pack),
            *_source(catalog, revision),
            "infrastructure.application-api-service",
            _VERSION,
            "application",
            "--parameters",
            "-",
            "--json",
        ],
        parameters={"deployment_profile": "compact", "service_label": "application-v2"},
    )
    result.command("application parameter updated", updated)

    replaced = _kit(
        [
            "replace",
            str(pack),
            *_source(catalog, revision),
            "infrastructure.reverse-proxy-api-gateway",
            _VERSION,
            "application",
            "--namespace",
            "gateway",
            "--target-sdl",
            "sdl/realistic-lab.sdl.yaml",
            "--parameters",
            "-",
            "--json",
        ],
        parameters=_parameters("gateway"),
    )
    result.command("application implementation replaced", replaced)
    removed = _kit(["remove", str(pack), "dns", "--json"])
    result.command("DNS kit removed", removed)

    final_ledger = json.loads((pack / "kit.materializations.json").read_text(encoding="utf-8"))
    final_ids = {item["id"] for item in final_ledger["materializations"]}
    result.check("replacement has one complete successor", "gateway" in final_ids and "application" not in final_ids)
    result.check("removed materialization and its ownership", "dns" not in final_ids)
    final_validation = _run("raes_env_packs.content_ci", ["--pack", str(pack)])
    result.command("final ordinary pack validates without kit UI", final_validation)
    release = _run("raes_env_packs.release", ["check", "--pack", str(pack)])
    result.command("final ordinary pack passes release checks", release)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path, help="staged local kit catalog root")
    parser.add_argument("--source-revision", help="immutable admitted catalog revision")
    args = parser.parse_args(argv)
    catalog = args.catalog.resolve()
    revision = _revision(catalog, args.source_revision)
    print("Infrastructure kits — end-to-end author walkthrough")
    print(f"catalog revision: {revision}")
    result = Result()
    with tempfile.TemporaryDirectory(prefix="kit-author-walkthrough-") as temporary:
        _walk(result, catalog, revision, Path(temporary))
    print(f"\n{result.passed} passed, {result.failed} failed")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
