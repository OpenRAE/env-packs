"""Owlbear kit contracts through the existing RAES and pack boundaries."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import yaml
from raes import SDLParseError, parse_sdl_file
from raes_processor.compiler import compile_scenario_runtime_model
from raes_processor.planner import plan

from raes_env_packs import kits
from raes_env_packs.digest import validate_pack_content_manifest
from raes_env_packs.validation import _validate_pack_for_author_ci
from tests.test_kit_compute_substrate import MANIFEST, _plan_release
from tests.test_kit_materialization import _write_content_identified_pack

ROOT = Path(__file__).resolve().parents[1]
KIT_ID = "infrastructure.owlbear-protected-target"
RELEASE = ROOT / "kits" / KIT_ID / "1.0.0"
REVISION = "fa4497f3273517611e2d62f5fb32c620a00a9681"
INPUTS = {"kernel_module", "daemon_binary", "game_binary", "signature_database"}


class OwlbearKitTests(unittest.TestCase):
    def test_release_is_admitted_with_every_member_byte_bound(self):
        self.assertTrue(RELEASE.is_dir(), "the Owlbear kit release is missing")
        release = kits.load_kit_release(RELEASE)
        self.assertEqual(release.id, KIT_ID)
        self.assertEqual(release.version, "1.0.0")
        self.assertEqual(release.document["concern"], "security-operations")
        self.assertEqual(
            len(release.associated_artifacts.artifacts), len(release.inventory) - 1
        )
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "release"
            shutil.copytree(RELEASE, copied)
            with (copied / "assets/seed.yaml").open("a") as stream:
                stream.write("\n# altered bytes\n")
            with self.assertRaises(kits.KitError):
                kits.load_kit_release(copied)

    def _compose(self, parameters, *, companion=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copy2(RELEASE / "module.sdl.yaml", root / "owlbear.sdl.yaml")
        imports = [{"source": "local:owlbear.sdl.yaml", "namespace": "protected",
                    "version": "1.0.0", "parameters": parameters}]
        if companion:
            shutil.copy2(
                ROOT / "kits/infrastructure.telemetry-collector/1.2.0/module.sdl.yaml",
                root / "collector.sdl.yaml",
            )
            imports.append({"source": "local:collector.sdl.yaml", "namespace": "telemetry",
                            "version": "1.2.0", "parameters": {"pipeline_name": "owlbear"}})
        scenario_path = root / "scenario.sdl.yaml"
        scenario_path.write_text(yaml.safe_dump({"name": "owlbear-composition", "imports": imports}))
        return parse_sdl_file(scenario_path, migration_policy="accept")

    def test_variation_changes_typed_runtime_state_and_compiles(self):
        cases = yaml.safe_load((RELEASE / "tests/composition.yaml").read_text())
        for name, expected in (("default", "active"), ("variation", "inactive")):
            with self.subTest(case=name):
                scenario = self._compose(cases[name], companion=True)
                target = scenario.nodes["protected.target"]
                self.assertEqual(target.os.value, "linux")
                self.assertEqual(target.architecture.value, "aarch64")
                self.assertEqual(target.resources.cpu, 2)
                self.assertFalse(target.services)
                unit, = target.runtime.service_manager_units
                self.assertEqual(unit.active_state.value, expected)
                self.assertNotIn("manager_kind", unit.model_fields_set)
                self.assertEqual(unit.unit_name, "")
                self.assertIn("telemetry.collector", scenario.nodes)
                self.assertEqual({c.name for c in target.runtime.software_components},
                                 {"owlbeard", "owlbear.ko", "owlbear-game"})
                for content_id in INPUTS:
                    content = scenario.content[f"protected.{content_id}"]
                    self.assertEqual(content.target, "protected.target")
                    self.assertEqual(content.source.version, REVISION)
                model = compile_scenario_runtime_model(scenario, parameters={})
                self.assertFalse(model.diagnostics)
                self.assertEqual(_plan_release(RELEASE, "1.0.0", cases[name]), set())

    def test_invalid_daemon_state_is_rejected_by_raes(self):
        with self.assertRaisesRegex(SDLParseError, "allowed_values"):
            self._compose({"daemon_active_state": "running"})

    def test_backend_without_os_or_unit_support_is_refused(self):
        model = compile_scenario_runtime_model(self._compose({}), parameters={})
        no_os = replace(
            MANIFEST,
            capabilities=replace(
                MANIFEST.capabilities,
                provisioner=replace(MANIFEST.provisioner, operating_systems=()),
            ),
        )
        self.assertIn("provisioner.unsupported-operating-system",
                      {d.code for d in plan(model, no_os).diagnostics})
        kind = "runtime-service-manager-units"
        no_unit = replace(
            MANIFEST,
            realization_support=tuple(replace(
                declaration,
                supported_exact_requirement_kinds=declaration.supported_exact_requirement_kinds - {kind},
                supported_constraint_kinds=declaration.supported_constraint_kinds - {kind},
            ) for declaration in MANIFEST.realization_support),
        )
        self.assertTrue(any(
            d.code.startswith("realization.unsupported-") and kind in d.message
            for d in plan(model, no_unit).diagnostics
        ))

    def test_transaction_materializes_an_ordinary_valid_pack(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = _write_content_identified_pack(Path(directory))
            source = kits.KitSource(id="openrae-env-packs", revision="test-revision", root=str(ROOT))
            release = kits.load_kit_release(RELEASE)
            proposal = kits.propose_add(
                pack_root=pack, release=release, source=source, namespace="protected",
                target_sdl="sdl/example-pack.sdl.yaml",
                parameters={"daemon_active_state": "inactive"},
            )
            self.assertFalse(proposal.diagnostics)
            kits.apply_proposal(proposal)
            scenario = parse_sdl_file(pack / "sdl/example-pack.sdl.yaml", migration_policy="accept")
            self.assertEqual(scenario.content["protected.daemon_binary"].target, "protected.target")
            self.assertEqual(
                scenario.nodes["protected.target"].runtime.service_manager_units[0].active_state.value,
                "inactive",
            )
            lock = json.loads((pack / "sdl/raes.lock.json").read_text())
            self.assertEqual(lock["imports"][0]["namespace"], "protected")
            ledger = json.loads((pack / kits.KIT_MATERIALIZATIONS_PATH).read_text())
            self.assertEqual(ledger["materializations"][0]["kit_id"], KIT_ID)
            self.assertTrue((pack / "assets/kits/owlbear-protected-target/provenance.md").is_file())
            result, _ = _validate_pack_for_author_ci(pack)
            self.assertTrue(result.ok, result.errors)
            validate_pack_content_manifest(pack)
