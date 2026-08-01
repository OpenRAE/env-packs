"""Transactional kit proposals and ordinary pack materialization (issue #190)."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote

import yaml
from raes import canonical_sdl_digest, parse_sdl_file
from raes_contracts.associated_artifacts import associated_artifact_set_digest
from raes_contracts.contracts import AssociatedArtifactManifestModel

from raes_env_packs import kits, wizard
from raes_env_packs.digest import validate_pack_content_manifest
from raes_env_packs.validation import _validate_pack_for_author_ci
from tests.test_kits import KIT_ID, KIT_VERSION, _write_synthetic_kit


def _artifact(artifact_id: str, rel: str, body: bytes) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "role": "other",
        "media_type": "application/octet-stream",
        "uri": f"raes-environment-pack:/{quote(rel, safe='/-._~')}",
        "checksum": {
            "algorithm": "sha256",
            "value": hashlib.sha256(body).hexdigest(),
        },
        "size_bytes": len(body),
        "created_at": "2026-08-01T00:00:00Z",
        "source": "environment-pack-author",
        "sensitivity": "internal",
    }


def _write_content_identified_pack(parent: Path) -> Path:
    environments = parent / "environments"
    environments.mkdir()
    proposal = wizard.build_proposal(
        wizard.normalize_inputs(
            {
                "version": wizard.WIZARD_INPUT_VERSION,
                "pack_id": "example-pack",
                "route": "minimal",
                "answers": {
                    "title": "Example Pack",
                    "description": "A kit composition fixture.",
                },
            }
        )
    )
    root = Path(wizard.write_proposal(proposal, str(environments)))
    pack_path = root / "pack.yaml"
    pack = yaml.safe_load(pack_path.read_text(encoding="utf-8"))
    pack["associated_artifact_manifest"] = "associated-artifacts.json"
    pack_path.write_text(yaml.safe_dump(pack, sort_keys=False), encoding="utf-8")

    scenario_path = root / "sdl" / "example-pack.sdl.yaml"
    scenario = parse_sdl_file(scenario_path)
    artifacts: dict[str, object] = {}
    for index, path in enumerate(
        sorted(item for item in root.rglob("*") if item.is_file())
    ):
        rel = path.relative_to(root).as_posix()
        artifact_id = f"initial-{index}"
        artifacts[artifact_id] = _artifact(artifact_id, rel, path.read_bytes())
    manifest = AssociatedArtifactManifestModel.model_validate(
        {
            "schema_version": "associated-artifact-manifest/v1",
            "manifest_id": "example-pack-associated-artifacts",
            "manifest_version": "0.1.0",
            "canonicalization_profile": "associated-artifact-set/v1",
            "scope": "scenario",
            "parent_ref": {
                "ref_kind": "scenario-snapshot",
                "ref_id": "example-pack",
                "ref_digest": canonical_sdl_digest(scenario).value,
            },
            "artifacts": artifacts,
            "set_digest": "sha256:" + "0" * 64,
        }
    )
    manifest = manifest.model_copy(
        update={"set_digest": associated_artifact_set_digest(manifest)}
    )
    (root / "associated-artifacts.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    validate_pack_content_manifest(root)
    return root


class KitProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.pack = _write_content_identified_pack(base)
        self.release = kits.load_kit_release(
            _write_synthetic_kit(base / "catalog" / "kits" / KIT_ID / KIT_VERSION)
        )
        self.source = kits.KitSource(
            id="reference", revision="sha256:catalog", root=str(base / "catalog")
        )

    def _add_proposal(self, **over: object) -> kits.KitProposal:
        arguments: dict[str, object] = {
            "pack_root": self.pack,
            "release": self.release,
            "source": self.source,
            "namespace": "web",
            "target_sdl": "sdl/example-pack.sdl.yaml",
            "parameters": {"hostname": "web.example.test"},
        }
        arguments.update(over)
        return kits.propose_add(**arguments)

    def test_preview_is_networkless_side_effect_free_and_value_free(self) -> None:
        before = {
            path.relative_to(self.pack).as_posix(): path.read_bytes()
            for path in self.pack.rglob("*")
            if path.is_file()
        }
        proposal = self._add_proposal()
        preview = kits.proposal_document(proposal)
        after = {
            path.relative_to(self.pack).as_posix(): path.read_bytes()
            for path in self.pack.rglob("*")
            if path.is_file()
        }

        self.assertEqual(before, after)
        self.assertFalse(proposal.diagnostics)
        self.assertEqual(preview["operation"], "add")
        self.assertEqual(preview["kit"], {"id": KIT_ID, "version": KIT_VERSION})
        self.assertEqual(preview["parameters"], ["hostname"])
        self.assertNotIn("web.example.test", json.dumps(preview))
        self.assertIn("sdl/raes.lock.json", preview["files"])
        self.assertTrue(preview["topology"])

    def test_add_initializes_raes_identity_for_a_minimal_valid_pack(self) -> None:
        environments = Path(self.temp.name) / "fresh" / "environments"
        environments.mkdir(parents=True)
        scaffold = wizard.build_proposal(
            wizard.normalize_inputs(
                {
                    "version": wizard.WIZARD_INPUT_VERSION,
                    "pack_id": "minimal-pack",
                    "route": "minimal",
                    "answers": {
                        "title": "Minimal Pack",
                        "description": "Starts without an artifact manifest.",
                    },
                }
            )
        )
        pack = Path(wizard.write_proposal(scaffold, str(environments)))

        proposal = kits.propose_add(
            pack,
            self.release,
            self.source,
            namespace="web",
            target_sdl="sdl/minimal-pack.sdl.yaml",
            parameters={"hostname": "web.example.test"},
        )
        kits.apply_proposal(proposal)

        manifest = yaml.safe_load((pack / "pack.yaml").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["associated_artifact_manifest"], "associated-artifacts.json"
        )
        validate_pack_content_manifest(pack)

    def test_add_materializes_ordinary_files_lock_ownership_and_identity(self) -> None:
        proposal = self._add_proposal()
        kits.apply_proposal(proposal)

        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(encoding="utf-8")
        )
        self.assertFalse(kits.validate_materializations_document(ledger))
        self.assertEqual(ledger["materializations"][0]["kit_id"], KIT_ID)
        self.assertEqual(ledger["materializations"][0]["kit_version"], KIT_VERSION)
        module_rel = ledger["materializations"][0]["module_path"]
        self.assertTrue((self.pack / module_rel).is_file())
        lock = json.loads(
            (self.pack / "sdl/raes.lock.json").read_text(encoding="utf-8")
        )
        self.assertEqual(lock["imports"][0]["namespace"], "web")
        scenario = yaml.safe_load(
            (self.pack / "sdl/example-pack.sdl.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(scenario["imports"][0]["parameters"]["hostname"], "web.example.test")
        associated = json.loads(
            (self.pack / "associated-artifacts.json").read_text(encoding="utf-8")
        )
        self.assertEqual(associated["parent_ref"]["ref_kind"], "scenario")
        self.assertEqual(associated["parent_ref"]["ref_id"], "example-pack")
        self.assertIsNone(associated["parent_ref"]["ref_digest"])
        result, _scenarios = _validate_pack_for_author_ci(self.pack)
        self.assertTrue(result.ok, result.errors)
        validate_pack_content_manifest(self.pack)

    def test_canonical_pack_validation_enforces_the_materialization_ledger(self) -> None:
        kits.apply_proposal(self._add_proposal())
        ledger_path = self.pack / kits.KIT_MATERIALIZATIONS_PATH
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger["files"][0]["owners"] = ["missing-materialization"]
        ledger_path.write_text(
            json.dumps(ledger, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result, _scenarios = _validate_pack_for_author_ci(self.pack)

        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                item.code.startswith("kit-materializations.")
                for item in result.diagnostics
            )
        )

    def test_remove_uses_ownership_and_preserves_author_files(self) -> None:
        kits.apply_proposal(self._add_proposal())
        author_doc = self.pack / "docs" / "concepts.md"
        author_doc.write_text("keep me\n", encoding="utf-8")

        removal = kits.propose_remove(self.pack, materialization_id="web")
        self.assertFalse(removal.diagnostics)
        kits.apply_proposal(removal)

        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(ledger["materializations"], [])
        self.assertEqual(ledger["files"], [])
        self.assertEqual(author_doc.read_text(encoding="utf-8"), "keep me\n")
        scenario = yaml.safe_load(
            (self.pack / "sdl/example-pack.sdl.yaml").read_text(encoding="utf-8")
        )
        self.assertFalse(scenario.get("imports"))
        validate_pack_content_manifest(self.pack)

    def test_author_modified_owned_file_blocks_removal(self) -> None:
        kits.apply_proposal(self._add_proposal())
        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(encoding="utf-8")
        )
        module_rel = ledger["materializations"][0]["module_path"]
        (self.pack / module_rel).write_text("author changed this\n", encoding="utf-8")

        proposal = kits.propose_remove(self.pack, materialization_id="web")

        self.assertEqual(
            [item.code for item in proposal.diagnostics],
            ["kit.author-modification.conflict"],
        )
        with self.assertRaises(kits.KitError):
            kits.apply_proposal(proposal)

    def test_author_modified_owned_file_blocks_a_later_add(self) -> None:
        kits.apply_proposal(self._add_proposal())
        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(encoding="utf-8")
        )
        module_rel = ledger["materializations"][0]["module_path"]
        (self.pack / module_rel).write_text("author changed this\n", encoding="utf-8")
        second = kits.load_kit_release(
            _write_synthetic_kit(
                Path(self.temp.name)
                / "catalog"
                / "kits"
                / "infrastructure.second-service"
                / KIT_VERSION,
                kit_id="infrastructure.second-service",
                module_id="infrastructure/second-service",
                node_name="second",
                parameter="profile",
            )
        )

        proposal = self._add_proposal(
            release=second,
            namespace="second",
            parameters={"profile": "standard"},
        )

        self.assertIn(
            "kit.author-modification.conflict",
            [item.code for item in proposal.diagnostics],
        )

    def test_dependency_version_is_exact_and_blocks_unsafe_removal(self) -> None:
        kits.apply_proposal(self._add_proposal())
        dependent = kits.load_kit_release(
            _write_synthetic_kit(
                Path(self.temp.name)
                / "catalog"
                / "kits"
                / "infrastructure.dependent-service"
                / KIT_VERSION,
                kit_id="infrastructure.dependent-service",
                module_id="infrastructure/dependent-service",
                node_name="dependent",
                parameter="profile",
                prerequisites=[
                    {
                        "kind": "kit",
                        "id": KIT_ID,
                        "version": KIT_VERSION,
                        "description": "Requires the static web foundation.",
                    }
                ],
            )
        )
        addition = self._add_proposal(
            release=dependent,
            namespace="dependent",
            parameters={"profile": "standard"},
        )
        self.assertFalse(addition.diagnostics)
        kits.apply_proposal(addition)

        removal = kits.propose_remove(self.pack, materialization_id="web")

        self.assertEqual(
            [item.code for item in removal.diagnostics],
            ["kit.dependency.conflict"],
        )

    def test_first_add_initializes_identity_for_existing_local_imports(self) -> None:
        environments = Path(self.temp.name) / "imported" / "environments"
        environments.mkdir(parents=True)
        scaffold = wizard.build_proposal(
            wizard.normalize_inputs(
                {
                    "version": wizard.WIZARD_INPUT_VERSION,
                    "pack_id": "imported-pack",
                    "route": "minimal",
                }
            )
        )
        pack = Path(wizard.write_proposal(scaffold, str(environments)))
        existing_module = pack / "sdl" / "existing" / "module.sdl.yaml"
        existing_module.parent.mkdir(parents=True)
        existing_module.write_bytes((Path(self.release.root) / "module.sdl.yaml").read_bytes())
        root_sdl = pack / "sdl" / "imported-pack.sdl.yaml"
        root_document = yaml.safe_load(root_sdl.read_text(encoding="utf-8"))
        root_document["imports"] = [
            {
                "source": "local:existing/module.sdl.yaml",
                "namespace": "existing",
                "version": KIT_VERSION,
                "parameters": {"hostname": "existing.example.test"},
            }
        ]
        root_sdl.write_text(
            yaml.safe_dump(root_document, sort_keys=False), encoding="utf-8"
        )

        proposal = kits.propose_add(
            pack,
            self.release,
            self.source,
            namespace="web",
            target_sdl="sdl/imported-pack.sdl.yaml",
            parameters={"hostname": "web.example.test"},
        )
        self.assertFalse(proposal.diagnostics)
        kits.apply_proposal(proposal)

        manifest = json.loads(
            (pack / "associated-artifacts.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["parent_ref"]["ref_kind"], "scenario")
        validate_pack_content_manifest(pack)

    def test_new_artifact_ids_cannot_overwrite_existing_manifest_entries(self) -> None:
        manifest_path = self.pack / "associated-artifacts.json"
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        old_id = sorted(document["artifacts"])[0]
        artifact = document["artifacts"].pop(old_id)
        artifact["artifact_id"] = "kit-web-module"
        document["artifacts"]["kit-web-module"] = artifact
        manifest = AssociatedArtifactManifestModel.model_validate(document)
        manifest = manifest.model_copy(
            update={"set_digest": associated_artifact_set_digest(manifest)}
        )
        manifest_path.write_text(
            manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        validate_pack_content_manifest(self.pack)

        kits.apply_proposal(self._add_proposal())

        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(encoding="utf-8")
        )
        module_rel = ledger["materializations"][0]["module_path"]
        module_entry = next(item for item in ledger["files"] if item["path"] == module_rel)
        final_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertNotEqual(module_entry["artifact_id"], "kit-web-module")
        self.assertIn(module_entry["artifact_id"], final_manifest["artifacts"])
        self.assertIn("kit-web-module", final_manifest["artifacts"])

    def test_update_changes_parameters_through_one_successor(self) -> None:
        kits.apply_proposal(self._add_proposal())

        with mock.patch(
            "raes_env_packs.kits._finalize_candidate",
            wraps=kits._finalize_candidate,
        ) as finalize:
            update = kits.propose_update(
                self.pack,
                self.release,
                self.source,
                materialization_id="web",
                parameters={"hostname": "updated.example.test"},
            )
        self.assertEqual(finalize.call_count, 1)
        self.assertEqual(update.operation, "update")
        self.assertNotIn("updated.example.test", json.dumps(kits.proposal_document(update)))
        kits.apply_proposal(update)

        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(
            ledger["materializations"][0]["parameters"]["hostname"],
            "updated.example.test",
        )
        validate_pack_content_manifest(self.pack)

    def test_replace_is_one_remove_plus_add_transaction(self) -> None:
        kits.apply_proposal(self._add_proposal())
        replacement = kits.load_kit_release(
            _write_synthetic_kit(
                Path(self.temp.name)
                / "catalog"
                / "kits"
                / "infrastructure.reverse-proxy"
                / KIT_VERSION,
                kit_id="infrastructure.reverse-proxy",
                module_id="infrastructure/reverse-proxy",
                node_name="proxy",
                parameter="route",
            )
        )

        proposal = kits.propose_replace(
            self.pack,
            replacement,
            self.source,
            materialization_id="web",
            namespace="front",
            target_sdl="sdl/example-pack.sdl.yaml",
            parameters={"route": "app.example.test"},
        )
        self.assertEqual(proposal.operation, "replace")
        kits.apply_proposal(proposal)

        ledger = json.loads(
            (self.pack / kits.KIT_MATERIALIZATIONS_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(ledger["materializations"][0]["id"], "front")
        self.assertEqual(
            ledger["materializations"][0]["kit_id"],
            "infrastructure.reverse-proxy",
        )
        self.assertFalse(any("static-web-service" in item["path"] for item in ledger["files"]))
        validate_pack_content_manifest(self.pack)

    def test_failed_atomic_exchange_preserves_the_original_pack(self) -> None:
        before = (self.pack / "sdl/example-pack.sdl.yaml").read_bytes()
        proposal = self._add_proposal()
        with mock.patch(
            "raes_env_packs._transactions.exchange",
            side_effect=OSError("exchange failed"),
        ):
            with self.assertRaises(kits.KitError):
                kits.apply_proposal(proposal)

        self.assertEqual(
            (self.pack / "sdl/example-pack.sdl.yaml").read_bytes(), before
        )
        self.assertFalse((self.pack / kits.KIT_MATERIALIZATIONS_PATH).exists())

    def test_post_exchange_validation_error_restores_the_original_pack(self) -> None:
        before = (self.pack / "sdl/example-pack.sdl.yaml").read_bytes()
        proposal = self._add_proposal()
        capture = kits._capture_pack
        calls = 0

        def fail_after_exchange(root):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise kits.KitError("post-exchange inspection failed")
            return capture(root)

        with mock.patch(
            "raes_env_packs.kits._capture_pack", side_effect=fail_after_exchange
        ):
            with self.assertRaises(kits.KitError):
                kits.apply_proposal(proposal)

        self.assertEqual(
            (self.pack / "sdl/example-pack.sdl.yaml").read_bytes(), before
        )
        self.assertFalse((self.pack / kits.KIT_MATERIALIZATIONS_PATH).exists())

    def test_failed_rollback_preserves_the_original_recovery_tree(self) -> None:
        before = (self.pack / "sdl/example-pack.sdl.yaml").read_bytes()
        proposal = self._add_proposal()
        capture = kits._capture_pack
        real_exchange = kits._transactions.exchange
        captures = 0
        exchanges = 0

        def fail_after_exchange(root):
            nonlocal captures
            captures += 1
            if captures == 4:
                raise kits.KitError("post-exchange inspection failed")
            return capture(root)

        def fail_rollback(staged, target):
            nonlocal exchanges
            exchanges += 1
            if exchanges == 1:
                return real_exchange(staged, target)
            raise OSError("rollback failed")

        with mock.patch(
            "raes_env_packs.kits._capture_pack", side_effect=fail_after_exchange
        ), mock.patch(
            "raes_env_packs._transactions.exchange", side_effect=fail_rollback
        ):
            with self.assertRaises(kits.KitRecoveryError) as raised:
                kits.apply_proposal(proposal)

        recovery = Path(raised.exception.recovery_path)
        self.assertTrue(recovery.is_dir())
        self.assertEqual(
            (recovery / "sdl/example-pack.sdl.yaml").read_bytes(), before
        )

    def test_asset_target_is_rechecked_at_the_materialization_boundary(self) -> None:
        release = kits.load_kit_release(
            _write_synthetic_kit(
                Path(self.temp.name)
                / "catalog"
                / "kits"
                / "infrastructure.asset-service"
                / KIT_VERSION,
                kit_id="infrastructure.asset-service",
                module_id="infrastructure/asset-service",
                node_name="asset",
                parameter="profile",
                asset_visibility="operator",
            )
        )
        with mock.patch(
            "raes_env_packs.kits._safe_asset_target", side_effect=[True, False]
        ):
            proposal = self._add_proposal(
                release=release,
                namespace="asset",
                parameters={"profile": "standard"},
            )

        self.assertIn(
            "kit.asset-target.invalid",
            [item.code for item in proposal.diagnostics],
        )

    def test_secret_shaped_parameters_are_rejected_on_add_and_update(self) -> None:
        addition = self._add_proposal(parameters={"hostname": "${SOME_VAR}"})
        self.assertIn(
            "kit.parameter.secret", [item.code for item in addition.diagnostics]
        )

        kits.apply_proposal(self._add_proposal())
        update = kits.propose_update(
            self.pack,
            self.release,
            self.source,
            materialization_id="web",
            parameters={"hostname": "env:SOME_VAR"},
        )
        self.assertIn(
            "kit.parameter.secret", [item.code for item in update.diagnostics]
        )

    def test_unknown_parameter_has_exact_diagnostic(self) -> None:
        unknown = self._add_proposal(parameters={"not_declared": "value"})
        self.assertIn("kit.parameter.unknown", [item.code for item in unknown.diagnostics])

    def test_missing_dependency_has_exact_diagnostic(self) -> None:
        dependent = kits.load_kit_release(
            _write_synthetic_kit(
                Path(self.temp.name)
                / "catalog"
                / "kits"
                / "infrastructure.dependent-service"
                / KIT_VERSION,
                kit_id="infrastructure.dependent-service",
                module_id="infrastructure/dependent-service",
                node_name="dependent",
                parameter="profile",
                prerequisites=[
                    {
                        "kind": "kit",
                        "id": "infrastructure.identity-provider",
                        "version": "1.0.0",
                        "description": "Imports an identity facade.",
                    }
                ],
            )
        )
        dependency = self._add_proposal(
            release=dependent,
            namespace="dependent",
            parameters={"profile": "default"},
        )
        self.assertIn("kit.dependency.missing", [item.code for item in dependency.diagnostics])

    def test_visibility_conflict_has_exact_diagnostic(self) -> None:
        restricted = kits.load_kit_release(
            _write_synthetic_kit(
                Path(self.temp.name)
                / "catalog"
                / "kits"
                / "infrastructure.restricted-service"
                / KIT_VERSION,
                kit_id="infrastructure.restricted-service",
                module_id="infrastructure/restricted-service",
                node_name="restricted",
                parameter="profile",
                asset_visibility="restricted",
            )
        )
        visibility = self._add_proposal(
            release=restricted,
            namespace="restricted",
            parameters={"profile": "default"},
        )
        self.assertIn("kit.visibility.conflict", [item.code for item in visibility.diagnostics])

    def test_source_conflict_has_exact_diagnostic(self) -> None:
        wrong_source = self._add_proposal(
            source=kits.KitSource(
                id="other", revision="sha256:other", root=str(Path(self.temp.name) / "other")
            )
        )
        self.assertIn("kit.source.conflict", [item.code for item in wrong_source.diagnostics])

    def test_duplicate_namespace_export_and_path_have_exact_diagnostics(self) -> None:
        kits.apply_proposal(self._add_proposal())
        duplicate = self._add_proposal()
        duplicate_codes = [item.code for item in duplicate.diagnostics]
        self.assertIn("kit.namespace.conflict", duplicate_codes)
        self.assertIn("kit.export.conflict", duplicate_codes)
        self.assertIn("kit.path.conflict", duplicate_codes)

    def test_version_conflict_has_exact_diagnostic(self) -> None:
        kits.apply_proposal(self._add_proposal())
        newer = kits.load_kit_release(
            _write_synthetic_kit(
                Path(self.temp.name) / "catalog" / "kits" / KIT_ID / "2.0.0",
                kit_version="2.0.0",
            )
        )
        version = self._add_proposal(
            release=newer,
            namespace="web2",
            parameters={"hostname": "web2.example.test"},
        )
        self.assertIn("kit.version.conflict", [item.code for item in version.diagnostics])


if __name__ == "__main__":
    unittest.main()
