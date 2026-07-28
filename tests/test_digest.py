"""RAES-associated environment-pack content identity (issue #95, ADR 0012)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote

from raes_contracts.associated_artifacts import (
    AssociatedArtifactValidationLimits,
    associated_artifact_set_digest,
)
from raes_contracts.contracts import AssociatedArtifactManifestModel
from raes import canonical_sdl_digest, parse_sdl_file

from raes_env_packs import (
    PackDigestError,
    derive_pack_content_manifest,
    pack_content_digest,
    validate_pack_content_manifest,
    verify_pack_content_digest,
)
from raes_env_packs import digest


_VALID_SDL = "\n".join(
    [
        "name: example-pack",
        "nodes:",
        "  target:",
        "    type: vm",
        "",
    ]
)


def _write(root: Path, rel: str, body: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _artifact(artifact_id: str, rel: str, body: bytes) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "role": "other",
        "media_type": "application/octet-stream",
        "uri": f"raes-environment-pack:/{quote(rel, safe='/-._~')}",
        "checksum": {"algorithm": "sha256", "value": hashlib.sha256(body).hexdigest()},
        "size_bytes": len(body),
        "created_at": "2026-07-12T00:00:00Z",
        "source": "environment-pack-author",
        "sensitivity": "internal",
    }


def _write_declared_manifest(root: Path, *, mutate: object | None = None) -> None:
    rels = [
        rel
        for rel in ("pack.yaml", "sdl/example.sdl.yaml", "docs/guide.md")
        if (root / rel).exists()
    ]
    artifacts = {
        f"artifact-{index}": _artifact(f"artifact-{index}", rel, (root / rel).read_bytes())
        for index, rel in enumerate(rels)
    }
    payload: dict[str, object] = {
        "schema_version": "associated-artifact-manifest/v1",
        "manifest_id": "example-pack-associated-artifacts",
        "manifest_version": "0.1.0",
        "canonicalization_profile": "associated-artifact-set/v1",
        "scope": "scenario",
        "parent_ref": {"ref_kind": "scenario", "ref_id": "example-pack"},
        "artifacts": artifacts,
        "set_digest": "sha256:" + "0" * 64,
    }
    if callable(mutate):
        mutate(payload)
    model = AssociatedArtifactManifestModel.model_validate(payload)
    model = model.model_copy(update={"set_digest": associated_artifact_set_digest(model)})
    (root / "associated-artifacts.json").write_text(
        model.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


def _refresh_manifest(root: Path) -> None:
    model = derive_pack_content_manifest(root)
    (root / "associated-artifacts.json").write_text(
        model.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


class PackFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        _write(
            self.root,
            "pack.yaml",
            b"name: example-pack\nversion: 0.1.0\n"
            b"associated_artifact_manifest: associated-artifacts.json\n",
        )
        _write(self.root, "sdl/example.sdl.yaml", _VALID_SDL.encode())
        _write(self.root, "docs/guide.md", b"operator guide\n")
        _write_declared_manifest(self.root)

class DerivationTests(PackFixture):
    def test_derives_the_declared_aces_manifest(self):
        derived = derive_pack_content_manifest(self.root)
        declared = validate_pack_content_manifest(self.root)
        self.assertEqual(derived, declared)
        self.assertEqual(pack_content_digest(self.root), derived.set_digest)

    def test_raw_byte_change_changes_derived_identity_and_invalidates_declaration(self):
        before = pack_content_digest(self.root)
        _write(self.root, "docs/guide.md", b"changed guide\n")
        after = derive_pack_content_manifest(self.root).set_digest
        self.assertNotEqual(before, after)
        with self.assertRaises(PackDigestError) as raised:
            validate_pack_content_manifest(self.root)
        self.assertIn(
            "associated-artifact.payload",
            " ".join(item.code for item in raised.exception.diagnostics),
        )

    def test_descriptor_metadata_changes_set_identity(self):
        before = pack_content_digest(self.root)
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["artifacts"]["artifact-2"]["role"] = "documentation"
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        derived = derive_pack_content_manifest(self.root)
        self.assertNotEqual(before, derived.set_digest)

    def test_refresh_makes_changed_pack_valid_again(self):
        _write(self.root, "docs/guide.md", b"changed guide\n")
        _refresh_manifest(self.root)
        self.assertEqual(pack_content_digest(self.root), validate_pack_content_manifest(self.root).set_digest)

    def test_module_cache_is_not_part_of_inventory(self):
        _write(self.root, "sdl/.raes/module-cache/fetched.yaml", b"mutable")
        self.assertEqual(pack_content_digest(self.root), validate_pack_content_manifest(self.root).set_digest)

    def test_same_named_cache_elsewhere_is_not_excluded(self):
        _write(self.root, "docs/.raes/module-cache/note.txt", b"content")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)


class InventoryTests(PackFixture):
    def test_undeclared_file_is_rejected(self):
        _write(self.root, "assets/extra.bin", b"undeclared")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_declared_missing_file_is_rejected(self):
        (self.root / "docs/guide.md").unlink()
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_noncanonical_pack_uri_is_rejected(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["artifacts"]["artifact-2"]["uri"] = "raes-environment-pack:/docs/%67uide.md"
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_non_utf8_pack_uri_is_rejected(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["artifacts"]["artifact-2"]["uri"] = "raes-environment-pack:/docs/%FF.md"
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_escaping_pack_uri_is_rejected(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["artifacts"]["artifact-2"]["uri"] = "raes-environment-pack:/../outside"
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_duplicate_json_member_is_rejected(self):
        body = (self.root / "associated-artifacts.json").read_text()
        body = body.replace('"scope": "scenario",', '"scope": "scenario",\n  "scope": "scenario",')
        (self.root / "associated-artifacts.json").write_text(body)
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_file_set_change_during_validation_is_rejected(self):
        real_inventory = digest._inventory
        calls = {"count": 0}

        def changed(root, excluded):
            result = real_inventory(root, excluded)
            calls["count"] += 1
            if calls["count"] == 2:
                return result + ("late-file",)
            return result

        with mock.patch.object(digest, "_inventory", side_effect=changed):
            with self.assertRaises(PackDigestError):
                derive_pack_content_manifest(self.root)

    def test_case_insensitive_collision_is_rejected(self):
        _write(self.root, "Guide", b"one")
        _write(self.root, "guide", b"two")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_member_count_is_bounded(self):
        with mock.patch.object(digest, "_MAX_PACK_MEMBERS", 2):
            with self.assertRaises(PackDigestError):
                derive_pack_content_manifest(self.root)


class ParentAndManifestTests(PackFixture):
    def test_sealed_scenario_snapshot_parent_is_supported(self):
        scenario = parse_sdl_file(self.root / "sdl/example.sdl.yaml")
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["parent_ref"] = {
            "ref_kind": "scenario-snapshot",
            "ref_id": "example-pack",
            "ref_digest": canonical_sdl_digest(scenario).value,
        }
        model = AssociatedArtifactManifestModel.model_validate(payload)
        model = model.model_copy(update={"set_digest": associated_artifact_set_digest(model)})
        (self.root / "associated-artifacts.json").write_text(model.model_dump_json(indent=2))
        self.assertEqual(pack_content_digest(self.root), model.set_digest)

    def test_pack_name_must_equal_parent_id(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["parent_ref"]["ref_id"] = "other-pack"
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_experiment_scope_is_rejected_for_scenario_pack(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["scope"] = "experiment"
        payload["parent_ref"] = {"ref_kind": "task", "ref_id": "task", "ref_version": "1"}
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_missing_manifest_pointer_is_rejected(self):
        (self.root / "pack.yaml").write_text("name: example-pack\nversion: 0.1.0\n")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_missing_pack_version_is_rejected(self):
        (self.root / "pack.yaml").write_text(
            "name: example-pack\nassociated_artifact_manifest: associated-artifacts.json\n"
        )
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_nonmapping_and_invalid_pack_yaml_are_rejected(self):
        for body in ("- not-a-mapping\n", "name: [invalid"):
            with self.subTest(body=body):
                (self.root / "pack.yaml").write_text(body)
                with self.assertRaises(PackDigestError):
                    derive_pack_content_manifest(self.root)

    def test_absolute_manifest_pointer_is_rejected(self):
        (self.root / "pack.yaml").write_text(
            "name: example-pack\nversion: 0.1.0\nassociated_artifact_manifest: /tmp/manifest.json\n"
        )
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_structurally_invalid_manifest_is_rejected(self):
        (self.root / "associated-artifacts.json").write_text("{}")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_manifest_identity_and_version_are_pack_bound(self):
        for field, value in (("manifest_id", "other"), ("manifest_version", "9.9.9")):
            with self.subTest(field=field):
                _write_declared_manifest(self.root)
                payload = json.loads((self.root / "associated-artifacts.json").read_text())
                payload[field] = value
                (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
                with self.assertRaises(PackDigestError):
                    derive_pack_content_manifest(self.root)

    def test_non_sha256_descriptor_is_rejected(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["artifacts"]["artifact-2"]["checksum"] = {
            "algorithm": "sha384",
            "value": hashlib.sha384(b"operator guide\n").hexdigest(),
        }
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_invalid_sdl_parent_is_rejected(self):
        _write(self.root, "sdl/example.sdl.yaml", b"name: [invalid")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_metadata_reads_are_bounded(self):
        with mock.patch.object(digest, "_MAX_PACK_YAML_BYTES", 4):
            with self.assertRaises(PackDigestError):
                derive_pack_content_manifest(self.root)

    def test_missing_sdl_parent_is_rejected(self):
        (self.root / "sdl/example.sdl.yaml").unlink()
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)


class FilesystemSafetyTests(PackFixture):
    def test_empty_and_missing_roots_are_rejected(self):
        for root in ("", self.root / "missing"):
            with self.subTest(root=root), self.assertRaises(PackDigestError):
                derive_pack_content_manifest(root)

    def test_unsupported_descriptor_platform_is_rejected(self):
        with mock.patch.object(digest, "_NOFOLLOW", 0):
            with self.assertRaises(PackDigestError):
                derive_pack_content_manifest(self.root)

    def test_symlinked_file_is_rejected(self):
        target = self.root / "outside"
        target.write_bytes(b"x")
        link = self.root / "assets/link"
        link.parent.mkdir()
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_symlinked_directory_is_rejected(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        link = self.root / "assets"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_hardlink_is_rejected(self):
        link = self.root / "guide-link"
        try:
            os.link(self.root / "docs/guide.md", link)
        except (OSError, NotImplementedError):
            self.skipTest("hardlinks unavailable")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_fifo_is_rejected(self):
        fifo = self.root / "named-pipe"
        try:
            os.mkfifo(fifo)
        except (OSError, AttributeError):
            self.skipTest("FIFOs unavailable")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root)

    def test_symlinked_root_is_rejected(self):
        link = self.root.parent / f"{self.root.name}-link"
        self.addCleanup(link.unlink, missing_ok=True)
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(link)


class VerifyTests(PackFixture):
    def test_match_and_mismatch(self):
        actual = pack_content_digest(self.root)
        self.assertTrue(verify_pack_content_digest(self.root, actual))
        self.assertFalse(verify_pack_content_digest(self.root, "sha256:" + "f" * 64))

    def test_noncanonical_expected_digest_is_rejected(self):
        for value in ("", "SHA256:" + "0" * 64, "sha256:" + "A" * 64, "sha256:" + "0" * 63):
            with self.subTest(value=value), self.assertRaises(PackDigestError):
                verify_pack_content_digest(self.root, value)

    def test_derivation_enforces_caller_limits_before_success(self):
        limits = AssociatedArtifactValidationLimits(
            max_artifacts=3,
            max_artifact_bytes=8,
            max_total_bytes=100,
        )
        with self.assertRaises(PackDigestError):
            derive_pack_content_manifest(self.root, limits=limits)

    def test_validation_preserves_aces_resource_limit_diagnostic(self):
        limits = AssociatedArtifactValidationLimits(
            max_artifacts=2,
            max_artifact_bytes=1024,
            max_total_bytes=4096,
        )
        with self.assertRaises(PackDigestError) as raised:
            validate_pack_content_manifest(self.root, limits=limits)
        self.assertEqual(
            {item.code for item in raised.exception.diagnostics},
            {"associated-artifact.resource-limit-exceeded"},
        )


if __name__ == "__main__":
    unittest.main()
