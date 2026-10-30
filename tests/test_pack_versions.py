"""Every pack in this repository carries the package version (ADR 0045)."""

from __future__ import annotations

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


def _versions(pack: pathlib.Path) -> dict[str, str]:
    manifest = json.loads((pack / "associated-artifacts.json").read_text(encoding="utf-8"))
    compatibility = yaml.safe_load(
        (pack / "pack.compatibility.yaml").read_text(encoding="utf-8")
    )
    versions = {
        "pack.yaml": yaml.safe_load((pack / "pack.yaml").read_text(encoding="utf-8"))["version"],
        "pack.compatibility.yaml": compatibility["pack"]["version"],
        "manifest_version": manifest["manifest_version"],
    }
    (sdl,) = sorted((pack / "sdl").glob("*.sdl.yaml"))
    content = yaml.safe_load(sdl.read_text(encoding="utf-8")).get("content") or {}
    for content_id, item in content.items():
        source = item.get("source") or {}
        exact = (source.get("artifact_requirement") or {}).get("exact_artifact") or {}
        if exact.get("artifact_id") in manifest["artifacts"]:
            versions[f"content.{content_id}.source"] = source["version"]
            versions[f"content.{content_id}.exact_artifact"] = exact["version"]
    return versions


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
