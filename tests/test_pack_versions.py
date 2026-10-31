"""Every pack in this repository carries the package version (ADR 0045)."""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import shutil
import tempfile
import unittest

import yaml

from raes_env_packs import validate_pack
from raes_env_packs.digest import validate_pack_content_manifest
from tools import sync_pack_versions as sync


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACKS = sorted(path.parent for path in (_ROOT / "packs").glob("*/pack.yaml"))
_WORKFLOW = _ROOT / ".github" / "workflows" / "release-please.yml"
_RELEASE_BRANCH = "release-please--branches--main--components--raes-env-packs"


_versions = sync.declared_versions


class PackVersionTests(unittest.TestCase):
    def test_every_pack_carries_the_package_version(self) -> None:
        version = sync.package_version()
        self.assertTrue(_PACKS)
        for pack in _PACKS:
            for location, declared in _versions(pack).items():
                with self.subTest(pack=pack.name, location=location):
                    self.assertEqual(declared, version)

    def test_sync_changes_only_version_scalars_and_keeps_the_pack_valid(self) -> None:
        source = _ROOT / "packs" / "techvault"
        with tempfile.TemporaryDirectory() as directory:
            pack = pathlib.Path(directory) / "techvault"
            shutil.copytree(source, pack, ignore=shutil.ignore_patterns("__pycache__"))

            self.assertTrue(sync.sync_pack(pack, "99.0.0"))

            self.assertEqual(set(_versions(pack).values()), {"99.0.0"})
            result = validate_pack(pack)
            self.assertTrue(result.ok, result.errors)
            validate_pack_content_manifest(pack)
            for name in ("pack.yaml", "pack.compatibility.yaml", "sdl/techvault.sdl.yaml"):
                with self.subTest(file=name):
                    before = (source / name).read_text(encoding="utf-8").splitlines()
                    after = (pack / name).read_text(encoding="utf-8").splitlines()
                    self.assertEqual(len(before), len(after))
                    changed = [new for old, new in zip(before, after) if old != new]
                    self.assertTrue(changed)
                    for line in changed:
                        self.assertRegex(line, r"^\s*version: 99\.0\.0$")
            self.assertFalse(sync.sync_pack(pack, "99.0.0"))

    def test_scalar_replacement_keeps_quoting_and_rejects_a_missing_path(self) -> None:
        text = "a:\n  version: '1.0.0'  # pinned\nb: 2\n"
        self.assertEqual(
            sync.set_yaml_scalars(text, [("a", "version")], "2.0.0"),
            "a:\n  version: '2.0.0'  # pinned\nb: 2\n",
        )
        with self.assertRaisesRegex(ValueError, "missing or duplicated"):
            sync.set_yaml_scalars(text, [("a", "absent")], "2.0.0")

    def test_check_passes_for_this_repository(self) -> None:
        self.assertEqual(sync.check(), [])
        self.assertEqual(sync.main(["--check"]), 0)

    def test_check_reports_a_stale_pack_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            shutil.copy(_ROOT / "pyproject.toml", root / "pyproject.toml")
            pack = root / "packs" / "techvault"
            shutil.copytree(
                _ROOT / "packs" / "techvault",
                pack,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            sync.sync_pack(pack, "0.0.1")
            before = {path: path.read_bytes() for path in pack.rglob("*") if path.is_file()}

            mismatches = sync.check(root)

            self.assertTrue(mismatches)
            for mismatch in mismatches:
                self.assertIn("is 0.0.1, not ", mismatch)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(sync.main(["--check"], root), 1)
            after = {path: path.read_bytes() for path in pack.rglob("*") if path.is_file()}
            self.assertEqual(before, after)


class ReleaseWorkflowPackVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
        self.job = self.workflow["jobs"]["sync-pack-versions"]
        self.text = json.dumps(self.job)

    def test_runs_after_each_release_pr_update(self) -> None:
        self.assertEqual(set(self.job["needs"]), {"release-please", "resume-release-please"})
        condition = str(self.job["if"])
        self.assertIn("needs.release-please.result == 'success'", condition)
        self.assertIn("needs.resume-release-please.result == 'success'", condition)
        self.assertNotIn("always()", condition)

    def test_writes_only_the_release_pr_branch_without_signing_privilege(self) -> None:
        self.assertEqual(
            self.job["permissions"], {"contents": "write", "pull-requests": "read"}
        )
        self.assertIn(_RELEASE_BRANCH, self.text)
        self.assertIn("tools/sync_pack_versions.py", self.text)
        self.assertIn("--require-hashes", self.text)

    def test_installs_the_package_before_the_tool_imports_it(self) -> None:
        # #544: raes_env_packs reads its own distribution metadata at import.
        steps = self.job["steps"]
        names = [step.get("name") for step in steps]
        install = names.index("Install hash-locked tooling and the package")
        write = names.index("Write the release version into every pack")
        self.assertLess(install, write)
        script = steps[install]["run"]
        self.assertIn("--require-hashes -r requirements/build.txt", script)
        self.assertIn("pip install --no-deps --no-build-isolation -e .", script)
        self.assertNotIn("PYTHONPATH", json.dumps(steps[write]))


class ReleaseWorkflowPackVersionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        self.job = self.jobs["verify-pack-versions"]

    def test_publish_waits_for_the_pack_version_gate(self) -> None:
        self.assertIn("verify-pack-versions", self.jobs["publish"]["needs"])
        self.assertNotIn("always()", str(self.jobs["publish"]["if"]))

    def test_gate_checks_the_release_target_read_only(self) -> None:
        self.assertEqual(self.job["needs"], ["detect-release"])
        self.assertEqual(self.job["if"], "needs.detect-release.outputs.release == 'true'")
        self.assertEqual(self.job["permissions"], {"contents": "read"})
        checkout = self.job["steps"][0]
        self.assertEqual(
            checkout["with"]["ref"], "${{ needs.detect-release.outputs.target }}"
        )
        self.assertIn(
            "python tools/sync_pack_versions.py --check",
            [step.get("run") for step in self.job["steps"]],
        )
