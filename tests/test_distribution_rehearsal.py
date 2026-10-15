"""Regression coverage for the pack-distribution rehearsal harness (#452, #451).

``tests_integration/distribution_rehearsal.py`` used to read ``techvault-0.1.0``
paths, so it stopped working once TechVault's ``pack.yaml`` moved past 0.1.0,
and it always rehearsed TechVault whatever pack the workflow's ``pack`` input
named. These tests run it at whatever version ``pack.yaml`` declares, for
TechVault and for the pack ``REHEARSAL_PACK`` names: the offline rehearsal
through the script's own entry point, and the registry rehearsal against stub
``oras`` and ``cosign`` executables that keep pushed files in a local store and
serve them back on pull.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
REHEARSAL = ROOT / "tests_integration" / "distribution_rehearsal.py"
TECHVAULT = ROOT / "packs" / "techvault"
# A second hosted pack, so a rehearsal that ignores REHEARSAL_PACK is caught.
STUDY = ROOT / "packs" / "techvault-participant-study"


def _manifest(pack_dir: Path) -> dict:
    return yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))


def _stem(pack_dir: Path) -> str:
    manifest = _manifest(pack_dir)
    return f"{manifest['name']}-{manifest['version']}"

# One stub stands in for both tools. It logs every call, and cosign calls just
# succeed, as a keyless signature from the GitHub OIDC identity would in CI.
_STUB = """
import json, os, shutil, sys
store = os.environ["REHEARSAL_STUB_STORE"]
tool, args = os.path.basename(sys.argv[0]), sys.argv[1:]
with open(os.path.join(store, "calls.jsonl"), "a", encoding="utf-8") as log:
    log.write(json.dumps([tool, *args]) + "\\n")
blobs = os.path.join(store, "blobs")
if tool == "oras" and args[0] == "push":
    os.makedirs(blobs, exist_ok=True)
    for spec in args[3:]:
        shutil.copy(spec.split(":", 1)[0], blobs)
elif tool == "oras" and args[0] == "resolve":
    print("sha256:" + "0" * 64)
elif tool == "oras" and args[0] == "pull":
    for name in os.listdir(blobs):
        shutil.copy(os.path.join(blobs, name), os.getcwd())
"""


def _rehearse(pack: str | None) -> subprocess.CompletedProcess:
    """Run the script as the workflow does, with ``REHEARSAL_PACK`` set or unset."""

    env = {key: value for key, value in os.environ.items()
           if key not in ("REHEARSAL_REGISTRY", "REHEARSAL_PACK")}
    if pack is not None:
        env["REHEARSAL_PACK"] = pack
    return subprocess.run(
        [sys.executable, str(REHEARSAL)], cwd=ROOT, env=env,
        capture_output=True, text=True, timeout=600)


def _load_rehearsal():
    spec = importlib.util.spec_from_file_location("distribution_rehearsal", REHEARSAL)
    module = importlib.util.module_from_spec(spec)
    # The script puts src/ on sys.path; keep that out of the test process.
    with mock.patch.object(sys, "path", list(sys.path)):
        spec.loader.exec_module(module)
    return module


class DistributionRehearsalTests(unittest.TestCase):
    def test_offline_rehearsal_passes_at_the_pack_yaml_version(self) -> None:
        completed = _rehearse(None)

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn(f"[rehearsal] published {_stem(TECHVAULT)} ", completed.stdout)
        self.assertIn("[rehearsal] OFFLINE REHEARSAL PASSED", completed.stdout)

    def test_offline_rehearsal_rehearses_the_pack_the_dispatch_names(self) -> None:
        completed = _rehearse("packs/techvault-participant-study")

        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn(f"[rehearsal] published {_stem(STUDY)} ", completed.stdout)
        self.assertIn("[rehearsal] OFFLINE REHEARSAL PASSED", completed.stdout)

    def test_a_directory_that_is_not_a_pack_stops_before_publishing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # A pack.yaml whose name is not its directory's name.
            mismatched = Path(tmp, "not-techvault")
            mismatched.mkdir()
            (mismatched / "pack.yaml").write_text(
                (TECHVAULT / "pack.yaml").read_text(encoding="utf-8"), encoding="utf-8")
            for pack in ("docs", "packs/no-such-pack", str(mismatched)):
                with self.subTest(pack=pack):
                    completed = _rehearse(pack)

                    self.assertNotEqual(completed.returncode, 0, completed.stdout)
                    self.assertIn(f"rehearsal stopped: {pack} (", completed.stderr)
                    self.assertIn("is not a pack", completed.stderr)
                    self.assertNotIn("[rehearsal] published", completed.stdout)

    def _assert_registry_rehearsal(self, pack_dir: Path) -> None:
        manifest, stem = _manifest(pack_dir), _stem(pack_dir)
        rehearsal = _load_rehearsal()
        with tempfile.TemporaryDirectory() as tmp:
            store, stubs = Path(tmp, "store"), Path(tmp, "bin")
            store.mkdir()
            stubs.mkdir()
            for tool in ("oras", "cosign"):
                path = stubs / tool
                path.write_text(f"#!{sys.executable}\n{_STUB}", encoding="utf-8")
                path.chmod(0o700)
            env = {"PATH": f"{stubs}{os.pathsep}{os.environ.get('PATH', '')}",
                   "REHEARSAL_STUB_STORE": str(store)}
            output = io.StringIO()
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(output):
                rehearsal.registry_rehearsal(
                    "registry.invalid", str(Path(tmp, "work")), str(pack_dir))
            calls = [json.loads(line) for line in
                     (store / "calls.jsonl").read_text(encoding="utf-8").splitlines()]

        push = next(call for call in calls if call[:2] == ["oras", "push"])
        self.assertEqual(push[3], f"registry.invalid/{manifest['name']}:{manifest['version']}")
        self.assertEqual(
            [spec.split(":", 1)[0] for spec in push[4:]],
            [f"{stem}.tar.gz", "release.yaml", f"{stem}.cdx.json", f"{stem}.provenance.json"])
        self.assertIn(["cosign", "sign", "--yes", "--allow-http-registry",
                       f"registry.invalid/{manifest['name']}@sha256:{'0' * 64}"], calls)
        # Passing means the pack-named consumer directories passed static validation.
        self.assertIn("[rehearsal] REGISTRY REHEARSAL PASSED", output.getvalue())

    def test_registry_rehearsal_pushes_the_built_release_under_the_pack_version(self) -> None:
        self._assert_registry_rehearsal(TECHVAULT)

    def test_registry_rehearsal_names_the_repository_and_consumers_after_the_pack(self) -> None:
        self._assert_registry_rehearsal(STUDY)


if __name__ == "__main__":
    unittest.main()
