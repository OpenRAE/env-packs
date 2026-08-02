"""Repository gates for the published first-party infrastructure kits."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from raes import parse_sdl_file

from raes_env_packs.kits import KitSource, build_kit_catalog, load_kit_release


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_KIT_COUNT = 38


class PublishedKitTests(unittest.TestCase):
    def test_all_releases_are_discoverable_and_deterministic(self) -> None:
        source = KitSource(
            id="openrae-env-packs",
            revision="test-revision",
            root=str(ROOT),
        )
        first = build_kit_catalog((source,))
        second = build_kit_catalog((source,))
        self.assertEqual(first, second)
        self.assertEqual(len(first["entries"]), EXPECTED_KIT_COUNT)

    def test_every_release_composes_with_two_parameter_sets(self) -> None:
        for manifest in sorted(ROOT.glob("kits/*/*/kit.yaml")):
            release = load_kit_release(manifest.parent)
            module = yaml.safe_load(
                (manifest.parent / "module.sdl.yaml").read_text(encoding="utf-8")
            )
            cases = yaml.safe_load(
                (manifest.parent / "tests/composition.yaml").read_text(
                    encoding="utf-8"
                )
            )
            domain_parameters = set(module["module"]["parameters"]) - {
                "deployment_profile",
                "service_label",
            }
            self.assertGreaterEqual(len(domain_parameters), 1, release.id)
            self.assertIn("seed_inventory", module["module"]["exports"]["content"])
            self.assertGreaterEqual(
                len(module["content"]["seed_inventory"]["items"]), 3, release.id
            )
            self.assertTrue(
                any(
                    cases["default"].get(parameter)
                    != cases["variation"].get(parameter)
                    for parameter in domain_parameters
                ),
                release.id,
            )
            for name in ("default", "variation"):
                with self.subTest(kit=release.id, case=name), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    shutil.copy2(
                        manifest.parent / "module.sdl.yaml", root / "module.sdl.yaml"
                    )
                    document = {
                        "name": "composition",
                        "imports": [
                            {
                                "source": "local:module.sdl.yaml",
                                "namespace": "subject",
                                "version": "1.0.0",
                                "parameters": cases[name],
                            }
                        ],
                    }
                    (root / "scenario.sdl.yaml").write_text(
                        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
                    )
                    parse_sdl_file(root / "scenario.sdl.yaml")

    def test_every_release_has_substantive_authoring_material(self) -> None:
        for manifest in sorted(ROOT.glob("kits/*/*/kit.yaml")):
            release = load_kit_release(manifest.parent)
            readme = (manifest.parent / "README.md").read_text(encoding="utf-8")
            integration = (manifest.parent / "assets/integration.md").read_text(
                encoding="utf-8"
            )
            seed = yaml.safe_load(
                (manifest.parent / "assets/seed.yaml").read_text(encoding="utf-8")
            )
            self.assertIn("authoring content", readme.lower(), release.id)
            self.assertIn("## Exported RAES declarations", integration, release.id)
            self.assertIn("## Composition notes", integration, release.id)
            self.assertGreaterEqual(len(seed["declared_objects"]), 3, release.id)
            self.assertTrue(seed["integration_requirements"], release.id)

    def test_representative_multi_kit_environment_composes(self) -> None:
        selected = [
            "infrastructure.windows-active-directory-domain-controller",
            "infrastructure.browser-workstation",
            "infrastructure.authoritative-dns-service",
            "infrastructure.application-api-service",
            "infrastructure.postgresql-database",
            "infrastructure.wazuh-security-monitoring-stack",
            "infrastructure.telemetry-collector",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            imports = []
            for index, kit_id in enumerate(selected):
                source = ROOT / "kits" / kit_id / "1.0.0" / "module.sdl.yaml"
                target = root / f"module-{index}.sdl.yaml"
                shutil.copy2(source, target)
                imports.append(
                    {
                        "source": f"local:{target.name}",
                        "namespace": f"kit{index}",
                        "version": "1.0.0",
                        "parameters": {
                            "deployment_profile": "compact",
                            "service_label": f"service-{index}",
                        },
                    }
                )
            (root / "scenario.sdl.yaml").write_text(
                yaml.safe_dump(
                    {"name": "realistic-environment", "imports": imports},
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            scenario = parse_sdl_file(root / "scenario.sdl.yaml")
            self.assertGreaterEqual(len(scenario.nodes), 9)


if __name__ == "__main__":
    unittest.main()
