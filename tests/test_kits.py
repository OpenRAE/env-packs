"""Infrastructure-kit contracts and authoring workflow (issue #190)."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from raes import canonical_sdl_digest, parse_sdl_file
from raes_contracts.associated_artifacts import associated_artifact_set_digest
from raes_contracts.contracts import AssociatedArtifactManifestModel

from raes_env_packs import kits


KIT_ID = "infrastructure.static-web-service"
KIT_VERSION = "1.0.0"


def _write_synthetic_kit(
    root: Path,
    *,
    kit_id: str = KIT_ID,
    kit_version: str = KIT_VERSION,
    module_id: str = "infrastructure/static-web-service",
    node_name: str = "web",
    parameter: str = "hostname",
    prerequisites: list[dict[str, str]] | None = None,
    asset_visibility: str | None = None,
) -> Path:
    """Create one closed, byte-bound kit release for contract tests."""

    root.mkdir(parents=True)
    module = root / "module.sdl.yaml"
    module.write_text(
        f"""name: {node_name}-service
version: {kit_version}
module:
  id: {module_id}
  version: {kit_version}
  parameters: [{parameter}]
  exports:
    nodes: [{node_name}]
variables:
  {parameter}:
    type: string
    default: {node_name}
nodes:
  {node_name}:
    type: vm
    description: ${{{parameter}}}
    resources:
      cpu: 1
      ram: 256 MiB
""",
        encoding="utf-8",
    )
    readme = root / "README.md"
    readme.write_text("# Static web service\n", encoding="utf-8")
    if asset_visibility is not None:
        (root / "seed.txt").write_text("seed content\n", encoding="utf-8")
    kit_document = {
        "schema_version": kits.KIT_SCHEMA_VERSION,
        "id": kit_id,
        "version": kit_version,
        "title": "Static web service",
        "summary": "A configurable HTTP content service.",
        "concern": "network-shared",
        "released_at": "2026-08-01T00:00:00Z",
        "module": {"path": "module.sdl.yaml"},
        "assets": (
            [
                {
                    "source": "seed.txt",
                    "target": "assets/content/seed.txt",
                    "visibility": asset_visibility,
                    "artifact_id": "seed",
                }
            ]
            if asset_visibility is not None
            else []
        ),
        "resources": {
            "cpu_cores": 1,
            "memory_mib": 256,
            "storage_mib": 64,
            "notes": "Single lightweight service.",
        },
        "prerequisites": prerequisites or [],
        "limitations": ["TLS termination is optional."],
        "license": {
            "expression": "MIT",
            "redistribution": "open",
            "attribution": "OpenRAE contributors",
        },
        "tests": [
            {"path": "module.sdl.yaml", "kind": "validate"},
            {"path": "module.sdl.yaml", "kind": "parameter-variation"},
            {"path": "module.sdl.yaml", "kind": "multi-kit"},
        ],
        "component_inventory": [
            {
                "scope": "pinned",
                "authority": "raes-source",
                "ref": "/nodes/web/source",
                "description": "The service image identity is carried by RAES when selected.",
            },
            {
                "scope": "external",
                "authority": "author-declared-external",
                "ref": "runtime-network",
                "description": "The runtime network is selected outside the pack.",
            },
        ],
        "associated_artifact_manifest": "associated-artifacts.json",
    }
    (root / "kit.yaml").write_text(
        yaml.safe_dump(kit_document, sort_keys=False), encoding="utf-8"
    )

    scenario = parse_sdl_file(module)
    parent_digest = canonical_sdl_digest(scenario).value
    artifacts: dict[str, object] = {}
    artifact_specs = [
        ("kit-manifest", "kit.yaml", "manifest", "application/yaml"),
        ("module", "module.sdl.yaml", "configuration", "application/yaml"),
        ("readme", "README.md", "documentation", "text/markdown"),
    ]
    if asset_visibility is not None:
        artifact_specs.append(("seed", "seed.txt", "dataset", "text/plain"))
    for artifact_id, rel, role, media_type in artifact_specs:
        data = (root / rel).read_bytes()
        artifacts[artifact_id] = {
            "artifact_id": artifact_id,
            "role": role,
            "media_type": media_type,
            "uri": f"raes-environment-kit:/{rel}",
            "checksum": {
                "algorithm": "sha256",
                "value": hashlib.sha256(data).hexdigest(),
            },
            "size_bytes": len(data),
            "created_at": "2026-08-01T00:00:00Z",
            "source": f"{kit_id}@{kit_version}",
            "sensitivity": "public",
        }
    manifest = AssociatedArtifactManifestModel.model_validate(
        {
            "schema_version": "associated-artifact-manifest/v1",
            "manifest_id": f"{kit_id}-associated-artifacts",
            "manifest_version": kit_version,
            "canonicalization_profile": "associated-artifact-set/v1",
            "scope": "scenario",
            "parent_ref": {
                "ref_kind": "scenario-snapshot",
                "ref_id": scenario.name,
                "ref_digest": parent_digest,
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
    return root


class KitContractTests(unittest.TestCase):
    def test_shared_library_contract_is_exported_from_the_package(self) -> None:
        import raes_env_packs

        for name in (
            "build_kit_catalog",
            "inspect_kit",
            "propose_add",
            "propose_update",
            "propose_replace",
            "propose_remove",
            "proposal_document",
            "apply_proposal",
        ):
            self.assertTrue(callable(getattr(raes_env_packs, name)))

    def test_contract_versions_are_independent_and_raes_style(self) -> None:
        self.assertEqual(kits.KIT_SCHEMA_VERSION, "environment-pack-kit/v1")
        self.assertEqual(
            kits.KIT_CATALOG_SCHEMA_VERSION, "environment-pack-kit-catalog/v1"
        )
        self.assertEqual(
            kits.KIT_MATERIALIZATIONS_SCHEMA_VERSION,
            "environment-pack-kit-materializations/v1",
        )

    def test_closed_manifest_rejects_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            document = yaml.safe_load((root / "kit.yaml").read_text(encoding="utf-8"))
            document["backend"] = "forbidden"
            violations = kits.validate_kit_document(document)
            self.assertTrue(any("backend" in item for item in violations))

    def test_manifest_rejects_behavior_and_backend_vocabulary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            document = yaml.safe_load((root / "kit.yaml").read_text(encoding="utf-8"))
            document["concern"] = "lateral-movement"
            violations = kits.validate_kit_document(document)
            self.assertTrue(violations)

    def test_manifest_rejects_secret_shaped_keys_and_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            document = yaml.safe_load((root / "kit.yaml").read_text(encoding="utf-8"))
            document["resources"]["notes"] = "-----BEGIN PRIVATE KEY-----"
            document["license"]["api-token"] = "redacted"
            violations = kits.validate_kit_document(document)

        self.assertIn("secret-key", violations)
        self.assertIn("secret-value", violations)

    def test_manifest_rejects_executable_asset_targets_and_terminal_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(
                Path(tmp) / "kit", asset_visibility="operator"
            )
            document = yaml.safe_load(
                (root / "kit.yaml").read_text(encoding="utf-8")
            )
            document["assets"][0]["target"] = "validators/validate_catalog.py"
            document["title"] = "trusted\x1b]52;c;Zm9yZ2Vk\x07"
            violations = kits.validate_kit_document(document)

        self.assertTrue(any("assets[0].target" in item for item in violations))
        self.assertIn("terminal-control:$.title", violations)


class KitInspectionTests(unittest.TestCase):
    def test_inspection_derives_module_facts_from_raes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            release = kits.load_kit_release(root)
            inspected = kits.inspect_kit(release)

        self.assertEqual(inspected["id"], KIT_ID)
        self.assertEqual(inspected["version"], KIT_VERSION)
        self.assertEqual(
            inspected["module"],
            {
                "id": "infrastructure/static-web-service",
                "version": "1.0.0",
                "parameters": ["hostname"],
                "parameter_defaults": {"hostname": "web"},
                "exports": {"nodes": ["web"]},
            },
        )

    def test_release_rejects_an_unbound_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(kits.KitError):
                kits.load_kit_release(root)

    def test_release_rejects_an_extra_file_outside_the_exact_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            (root / "extra.txt").write_text("not declared\n", encoding="utf-8")
            with self.assertRaises(kits.KitError):
                kits.load_kit_release(root)

    def test_release_rejects_behavior_even_when_raes_accepts_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            module = root / "module.sdl.yaml"
            module.write_text(
                module.read_text(encoding="utf-8")
                + "conditions:\n  ready:\n    proposition: 'true'\n"
                + "    command: echo ready\n    interval: 1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(kits.KitError, "behavior"):
                kits.load_kit_release(root)

    def test_release_rejects_secret_shaped_raes_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            module = root / "module.sdl.yaml"
            module.write_text(
                module.read_text(encoding="utf-8").replace(
                    "parameters: [hostname]", "parameters: [api_token]"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(kits.KitError, "secret"):
                kits.load_kit_release(root)

    def test_release_rejects_test_kinds_without_declared_component_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_synthetic_kit(Path(tmp) / "kit")
            document = yaml.safe_load((root / "kit.yaml").read_text(encoding="utf-8"))
            document["tests"] = [{"path": "module.sdl.yaml", "kind": "validate"}]
            document["component_inventory"] = []
            violations = kits.validate_kit_document(document)

        self.assertTrue(any("tests" in item for item in violations))
        self.assertTrue(any("component_inventory" in item for item in violations))


class KitCatalogTests(unittest.TestCase):
    def test_catalog_is_deterministic_and_uses_stable_source_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            release_root = source_root / "kits" / KIT_ID / KIT_VERSION
            _write_synthetic_kit(release_root)
            source = kits.KitSource(
                id="reference", revision="sha256:abc", root=str(source_root)
            )
            first = kits.build_kit_catalog((source,))
            second = kits.build_kit_catalog((source,))

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], kits.KIT_CATALOG_SCHEMA_VERSION)
        self.assertEqual(first["entries"][0]["source"], {
            "id": "reference", "revision": "sha256:abc"
        })
        self.assertNotIn("supported", json.dumps(first))

    def test_catalog_discovery_is_scoped_to_the_kits_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            release_root = source_root / "kits" / KIT_ID / KIT_VERSION
            _write_synthetic_kit(release_root)
            (source_root / "unrelated").mkdir()
            (source_root / "unrelated" / "link").symlink_to(release_root)
            source = kits.KitSource(
                id="reference", revision="sha256:abc", root=str(source_root)
            )

            document = kits.build_kit_catalog((source,))

        self.assertEqual(len(document["entries"]), 1)

    def test_exact_release_lookup_rejects_path_selectors_and_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            wrong_root = source_root / "kits" / "infrastructure.other" / KIT_VERSION
            _write_synthetic_kit(wrong_root)
            source = kits.KitSource(
                id="reference", revision="sha256:abc", root=str(source_root)
            )
            with self.assertRaises(kits.KitError):
                kits.source_release(source, "../escape", KIT_VERSION)
            with self.assertRaisesRegex(kits.KitError, "path"):
                kits.build_kit_catalog((source,))

    def test_source_revision_and_search_are_bounded_non_secret_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = kits.KitSource(
                id="reference", revision="${CATALOG_TOKEN}", root=tmp
            )
            with self.assertRaises(kits.KitError):
                kits.build_kit_catalog((source,))
        with self.assertRaises(kits.KitError):
            kits.search_catalog({"entries": []}, "x" * 4097)


if __name__ == "__main__":
    unittest.main()
