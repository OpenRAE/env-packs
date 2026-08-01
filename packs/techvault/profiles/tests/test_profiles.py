from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from raes import parse_sdl_file


PROFILES_DIR = Path(__file__).resolve().parents[1]
PACK_ROOT = PROFILES_DIR.parent
sys.path.insert(0, str(PROFILES_DIR))

import validate_profiles as vp  # noqa: E402


class ProfileBundleValidationTest(unittest.TestCase):
    def _copy_pack(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name) / "techvault"
        shutil.copytree(PACK_ROOT, root)
        return temporary, root

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_yaml(path: Path, document: dict) -> None:
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    def test_real_pack_is_clean_and_uses_one_operational_runtime(self) -> None:
        self.assertEqual(vp.validate_pack(PACK_ROOT), [])
        manifest = self._load_yaml(PACK_ROOT / "profiles/bundles.yaml")
        self.assertEqual(
            [row["id"] for row in manifest["bundles"]],
            list(vp.REQUIRED_BUNDLE_IDS),
        )
        self.assertTrue(
            all(
                row["runtime_profiles"] == ["operational"]
                for row in manifest["bundles"]
            )
        )

    def test_sdl_is_directly_parseable_aces_without_local_contract(self) -> None:
        path = PACK_ROOT / "sdl/techvault.sdl.yaml"
        scenario = parse_sdl_file(path)
        raw = self._load_yaml(path)
        self.assertEqual(scenario.name, "techvault")
        self.assertTrue(scenario.nodes)
        self.assertTrue(scenario.infrastructure)
        self.assertFalse(scenario.objectives)
        self.assertFalse(any(str(key).startswith("x-") for key in raw))

    def test_aces_sources_are_pack_contained(self) -> None:
        scenario = parse_sdl_file(PACK_ROOT / "sdl/techvault.sdl.yaml")
        content_source = scenario.content["fileshare-onboarding-packet"].source.name
        self.assertEqual(content_source, "assets/content/onboarding")
        for artifact in scenario.generated_artifacts.values():
            provenance = PACK_ROOT / artifact.provenance
            self.assertTrue(provenance.is_file())
            provenance.resolve().relative_to(PACK_ROOT.resolve())

    def test_manifest_path_traversal_is_rejected(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        path = root / "profiles/bundles.yaml"
        manifest = self._load_yaml(path)
        manifest["bundles"][0]["participant_entrypoints"][0] = "../README.md"
        self._write_yaml(path, manifest)
        self.assertIn(
            "canonical contained path required", "\n".join(vp.validate_pack(root))
        )

    def test_pack_document_path_traversal_is_rejected_before_access(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        issues: list[vp.Issue] = []
        self.assertIsNone(vp._load_yaml(root, "../outside.yaml", issues))
        self.assertEqual(len(issues), 1)
        self.assertIn("regular contained file required", str(issues[0]))

    def test_symlink_entrypoint_is_rejected(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        entrypoint = root / "profiles/guided/participant/plan.md"
        entrypoint.unlink()
        entrypoint.symlink_to(root / "profiles/_shared/mission-context.md")
        self.assertIn(
            "bundle:guided.guided/participant/plan.md: regular contained file required",
            vp.validate_pack(root),
        )

    def test_undeclared_participant_file_is_scanned_and_rejected(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        leaked = root / "profiles/guided/participant/extra.md"
        leaked.write_text("operator-only proof predicate\n", encoding="utf-8")
        joined = "\n".join(vp.validate_pack(root))
        self.assertIn("undeclared profile content forbidden", joined)
        self.assertIn("restricted participant content forbidden", joined)

    def test_pack_local_scenario_extension_is_rejected(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        path = root / "sdl/techvault.sdl.yaml"
        document = self._load_yaml(path)
        document["nodes"]["kali"]["x-techvault:runtime"] = {"parallel": "contract"}
        self._write_yaml(path, document)
        self.assertIn(
            "pack-local scenario contract forbidden", "\n".join(vp.validate_pack(root))
        )

    def test_pack_and_compatibility_indexes_must_match_manifest(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        path = root / "pack.compatibility.yaml"
        compatibility = self._load_yaml(path)
        compatibility["delivery_bundles"][0]["bundle_id"] = "legacy-alias"
        self._write_yaml(path, compatibility)
        self.assertIn(
            "manifest pack and compatibility ids must agree",
            "\n".join(vp.validate_pack(root)),
        )

    def test_agent_benchmark_cannot_be_added_without_aces_contract(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        path = root / "profiles/bundles.yaml"
        manifest = self._load_yaml(path)
        manifest["required_bundles"].append("agent-benchmark")
        self._write_yaml(path, manifest)
        self.assertIn(
            "required bundle order and ids must match",
            "\n".join(vp.validate_pack(root)),
        )

    def test_malformed_manifest_audiences_returns_field_issue(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        path = root / "profiles/bundles.yaml"
        manifest = self._load_yaml(path)
        manifest["audiences"] = None
        self._write_yaml(path, manifest)
        self.assertIn(
            "manifest:bundles.yaml.audiences: string list required",
            vp.validate_pack(root),
        )

    def test_malformed_bundle_includes_returns_field_issue(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        path = root / "profiles/bundles.yaml"
        manifest = self._load_yaml(path)
        manifest["bundles"][0]["shared_includes"] = {"not": "a list"}
        self._write_yaml(path, manifest)
        self.assertIn(
            "manifest:guided.shared_includes: string list required",
            vp.validate_pack(root),
        )

    def test_malformed_pack_index_returns_issues_without_exception(self) -> None:
        temporary, root = self._copy_pack()
        self.addCleanup(temporary.cleanup)
        path = root / "pack.yaml"
        pack = self._load_yaml(path)
        pack["profile_bundles"] = None
        self._write_yaml(path, pack)
        self.assertIn(
            "pack:pack.yaml.profile_bundles: mapping required",
            vp.validate_pack(root),
        )


if __name__ == "__main__":
    unittest.main()
