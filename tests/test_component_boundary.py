"""Tests for the pack-controlled component boundary gate (ADR 0037, ASP-0004)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest

import yaml

from raes_env_packs import component_boundary as cb
from raes_env_packs import digest as digest_module

_HERE = os.path.dirname(os.path.abspath(__file__))
_TECHVAULT = os.path.join(os.path.dirname(_HERE), "packs", "techvault")


def _techvault_with_associated_component(tmp: str, ref: str) -> str:
    """Copy TechVault, opt it into a component boundary with an associated-artifact
    row, and rebind its content-identity manifest so the pack still byte-binds.

    This is the only way to exercise the ``authority: associated-artifact``
    reconciliation branch of ``pack_component_boundary`` against a real
    content-identified pack, where ``_associated_artifact_ids`` is non-empty.
    """

    pack = os.path.join(tmp, "techvault")
    shutil.copytree(_TECHVAULT, pack)
    supply = {
        "schema_version": cb.SUPPLY_SCHEMA_VERSION,
        "component_boundary": [{
            "id": "assoc-c1", "scope": "shipped", "kind": "other",
            "authority": "associated-artifact", "ref": ref,
            "digest": "sha256:" + "0" * 64, "description": "an associated artifact",
        }],
    }
    with open(os.path.join(pack, "publication-supply.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump(supply, fh)
    pack_yaml = os.path.join(pack, "pack.yaml")
    with open(pack_yaml, encoding="utf-8") as fh:
        manifest_yaml = yaml.safe_load(fh)
    manifest_yaml["publication_supply"] = "publication-supply.yaml"
    with open(pack_yaml, "w", encoding="utf-8") as fh:
        yaml.safe_dump(manifest_yaml, fh, sort_keys=False)
    # Cover the new file in the associated-artifact manifest, then rebind
    # checksums/sizes/set-digest from the actual bytes so the pack byte-binds.
    aa_path = os.path.join(pack, "associated-artifacts.json")
    with open(aa_path, encoding="utf-8") as fh:
        aa = json.load(fh)
    raw = open(os.path.join(pack, "publication-supply.yaml"), "rb").read()
    aa["artifacts"]["techvault-publication-supply"] = {
        "artifact_id": "techvault-publication-supply", "role": "other",
        "media_type": "application/yaml",
        "uri": "raes-environment-pack:/publication-supply.yaml",
        "checksum": {"algorithm": "sha256", "value": hashlib.sha256(raw).hexdigest()},
        "size_bytes": len(raw), "created_at": "2026-08-02T00:00:00Z",
        "source": "environment-pack-author", "satisfies_refs": [],
        "sensitivity": "public", "description": None,
    }
    with open(aa_path, "w", encoding="utf-8") as fh:
        json.dump(aa, fh)
    derived = digest_module.derive_pack_content_manifest(pack)
    with open(aa_path, "w", encoding="utf-8") as fh:
        fh.write(derived.model_dump_json(indent=2) + "\n")
    return pack


def _codes(diagnostics) -> set[str]:
    return {d.code for d in diagnostics}


def _component(**overrides) -> dict:
    row = {
        "id": "comp-a",
        "scope": "pinned",
        "kind": "container-image",
        "authority": "raes-artifact",
        "ref": "registry.example/app",
        "digest": "sha256:" + "a" * 64,
        "description": "the application image",
    }
    row.update(overrides)
    return row


def _supply(**overrides) -> dict:
    document = {"schema_version": cb.SUPPLY_SCHEMA_VERSION}
    document.update(overrides)
    return document


class SchemaValidationTests(unittest.TestCase):
    def test_valid_minimal_document_has_no_diagnostics(self) -> None:
        diagnostics, components = cb.validate_publication_supply_document(_supply())
        self.assertEqual(diagnostics, [])
        self.assertEqual(components, ())

    def test_missing_schema_version_is_a_required_violation(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document({})
        self.assertIn("publication-supply.schema.required", _codes(diagnostics))

    def test_wrong_schema_version_is_a_const_violation(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document(
            {"schema_version": "environment-pack-publication-supply/v99"}
        )
        self.assertIn("publication-supply.schema.const", _codes(diagnostics))

    def test_unknown_top_level_field_is_rejected(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document(_supply(sbom="x"))
        self.assertIn("publication-supply.schema.unknown", _codes(diagnostics))

    def test_unknown_component_scope_is_rejected(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[_component(scope="whenever")])
        )
        self.assertIn("publication-supply.schema.enum", _codes(diagnostics))

    def test_component_missing_required_field_is_rejected(self) -> None:
        row = _component()
        del row["description"]
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[row])
        )
        self.assertIn("publication-supply.schema.required", _codes(diagnostics))

    def test_valid_component_parses(self) -> None:
        diagnostics, components = cb.validate_publication_supply_document(
            _supply(component_boundary=[_component()])
        )
        self.assertEqual(diagnostics, [])
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0].ref, "registry.example/app")


class ComponentSemanticsTests(unittest.TestCase):
    def test_controlled_component_without_digest_is_blocked(self) -> None:
        row = _component(scope="shipped", authority="raes-source")
        del row["digest"]
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[row])
        )
        self.assertIn("component-boundary.missing-digest", _codes(diagnostics))

    def test_controlled_component_declared_external_is_blocked(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[
                _component(scope="pinned", authority="author-declared-external")
            ])
        )
        self.assertIn(
            "component-boundary.external-authority-on-controlled", _codes(diagnostics)
        )

    def test_external_component_may_lack_a_digest(self) -> None:
        row = _component(scope="external", authority="author-declared-external")
        del row["digest"]
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[row])
        )
        self.assertEqual(diagnostics, [])

    def test_malformed_digest_is_rejected(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[_component(digest="sha256:nothex")])
        )
        self.assertIn("component-boundary.digest-invalid", _codes(diagnostics))

    def test_duplicate_component_id_is_rejected(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[_component(), _component(ref="other")])
        )
        self.assertIn("component-boundary.duplicate-id", _codes(diagnostics))

    def test_empty_description_is_rejected(self) -> None:
        diagnostics, _ = cb.validate_publication_supply_document(
            _supply(component_boundary=[_component(description="   ")])
        )
        self.assertIn("component-boundary.empty-field", _codes(diagnostics))


class _FakeLockRecord(object):
    def __init__(self, module_id: str, module_version: str, content_digest: str) -> None:
        self.module_id = module_id
        self.module_version = module_version
        self.content_digest = content_digest


class _FakeLockfile(object):
    def __init__(self, imports) -> None:
        self.imports = imports


class IncumbentTests(unittest.TestCase):
    def test_lock_module_becomes_a_pinned_incumbent(self) -> None:
        components = cb.incumbent_components(
            lockfile=_FakeLockfile([_FakeLockRecord("infra.identity", "1.0.0", "b" * 64)]),
            kit_inventories=[],
            scenarios=(),
        )
        self.assertEqual(len(components), 1)
        module = components[0]
        self.assertEqual(module.ref, "infra.identity")
        self.assertEqual(module.scope, "pinned")
        self.assertEqual(module.authority, "module-lock")
        self.assertEqual(module.digest, "sha256:" + "b" * 64)

    def test_shipped_kit_component_is_included_but_external_is_not(self) -> None:
        components = cb.incumbent_components(
            lockfile=None,
            kit_inventories=[
                {"scope": "shipped", "authority": "raes-source",
                 "ref": "kit.file.a", "description": "shipped file", "__kit_id": "k"},
                {"scope": "external", "authority": "author-declared-external",
                 "ref": "kit.file.b", "description": "external", "__kit_id": "k"},
            ],
            scenarios=(),
        )
        refs = {c.ref for c in components}
        self.assertIn("kit.file.a", refs)
        self.assertNotIn("kit.file.b", refs)


class MergeTests(unittest.TestCase):
    def _declared(self, **overrides) -> cb.Component:
        _diag, components = cb.validate_publication_supply_document(
            _supply(component_boundary=[_component(**overrides)])
        )
        return components[0]

    def _incumbent(self, ref: str, digest: str) -> cb.Component:
        return cb.Component(
            id="artifact-x", scope="pinned", kind="container-image",
            authority="raes-artifact", ref=ref, version=None, digest=digest,
            license=None, provenance="sdl-source", upstream_sbom=None,
            description="pinned",
        )

    def test_author_only_component_is_added(self) -> None:
        declared = self._declared(
            scope="external", authority="author-declared-external",
            ref="pypi/example", digest=None,
        )
        components, diagnostics = cb.merge_components([], [declared])
        self.assertEqual(diagnostics, [])
        self.assertIn("pypi/example", {c.ref for c in components})

    def test_author_digest_contradicting_incumbent_is_rejected(self) -> None:
        incumbent = self._incumbent("registry.example/app", "sha256:" + "b" * 64)
        declared = self._declared(
            ref="registry.example/app", authority="raes-artifact",
            digest="sha256:" + "c" * 64,
        )
        _components, diagnostics = cb.merge_components([incumbent], [declared])
        self.assertIn("component-boundary.digest-mismatch", _codes(diagnostics))

    def test_author_enrichment_keeps_incumbent_identity(self) -> None:
        incumbent = self._incumbent("registry.example/app", "sha256:" + "b" * 64)
        declared = self._declared(
            ref="registry.example/app", authority="raes-artifact",
            digest="sha256:" + "b" * 64, license="Apache-2.0",
        )
        components, diagnostics = cb.merge_components([incumbent], [declared])
        self.assertEqual(diagnostics, [])
        self.assertEqual(len(components), 1)
        self.assertEqual(components[0].digest, "sha256:" + "b" * 64)
        self.assertEqual(components[0].license, "Apache-2.0")


class PackLoaderTests(unittest.TestCase):
    def _write_pack(self, tmp: str, supply: dict | None) -> str:
        pack = os.path.join(tmp, "demo")
        os.makedirs(pack)
        manifest = {"name": "demo", "version": "0.1.0"}
        if supply is not None:
            manifest["publication_supply"] = "publication-supply.yaml"
            with open(os.path.join(pack, "publication-supply.yaml"), "w",
                      encoding="utf-8") as fh:
                yaml.safe_dump(supply, fh)
        with open(os.path.join(pack, "pack.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(manifest, fh)
        return pack

    def test_pack_without_publication_supply_has_no_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._write_pack(tmp, None)
            components, diagnostics = cb.pack_component_boundary(pack, scenarios=())
            self.assertEqual(components, ())
            self.assertEqual(diagnostics, [])

    def test_pack_with_valid_boundary_and_no_incumbents_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._write_pack(
                tmp, _supply(component_boundary=[
                    _component(scope="external",
                               authority="author-declared-external",
                               digest=None)
                ])
            )
            components, diagnostics = cb.pack_component_boundary(pack, scenarios=())
            self.assertEqual(diagnostics, [])
            self.assertEqual(len(components), 1)

    def test_materializations_without_resolver_report_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = self._write_pack(tmp, _supply())
            with open(os.path.join(pack, "kit.materializations.json"), "w",
                      encoding="utf-8") as fh:
                fh.write(yaml.safe_dump({
                    "schema_version": "environment-pack-kit-materializations/v1",
                    "materializations": [{
                        "kit_id": "infra.identity", "kit_version": "1.0.0",
                        "source": {"id": "first-party", "revision": "abc"},
                    }],
                }))
            components, diagnostics = cb.pack_component_boundary(pack, scenarios=())
            self.assertIn(
                "component-boundary.kit-source-unavailable", _codes(diagnostics)
            )

    def test_declared_associated_artifact_ref_must_exist_in_the_manifest(self) -> None:
        # The exact mechanism ADR 0037 leans on to stop an author claiming a
        # component maps to byte-identified content the pack does not contain.
        with tempfile.TemporaryDirectory() as tmp:
            pack = _techvault_with_associated_component(tmp, "ghost-not-in-manifest")
            _components, diagnostics = cb.pack_component_boundary(pack, scenarios=())
            self.assertIn("component-boundary.artifact-unknown", _codes(diagnostics))

    def test_declared_associated_artifact_ref_that_exists_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pack = _techvault_with_associated_component(tmp, "techvault-publication-supply")
            _components, diagnostics = cb.pack_component_boundary(pack, scenarios=())
            self.assertNotIn("component-boundary.artifact-unknown", _codes(diagnostics))


if __name__ == "__main__":
    unittest.main()
