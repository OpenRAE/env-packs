"""Public single-open pack artifact resolver (issue #208, ADR 0033)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote

from raes_contracts.associated_artifacts import AssociatedArtifactValidationLimits
from raes_contracts.contracts import AssociatedArtifactManifestModel, ExperimentArtifactRefModel
from raes_contracts.associated_artifacts import associated_artifact_set_digest
from raes.artifact_requirements import ArtifactIdentity

from raes_env_packs import (
    PackDigestError,
    PackValidationLimits,
    ResolvedPackArtifact,
    resolve_pack_artifact,
    validate_pack_content_manifest,
)
from raes_env_packs import _pack_fs, digest


_VALID_SDL = "\n".join(
    [
        "name: example-pack",
        "nodes:",
        "  target:",
        "    type: vm",
        "",
    ]
)

_GUIDE_BODY = b"operator guide\n"


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


def _write_declared_manifest(root: Path) -> None:
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
    model = AssociatedArtifactManifestModel.model_validate(payload)
    model = model.model_copy(update={"set_digest": associated_artifact_set_digest(model)})
    (root / "associated-artifacts.json").write_text(
        model.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )


class PackFixture(unittest.TestCase):
    # artifact-0 -> pack.yaml, artifact-1 -> sdl/example.sdl.yaml,
    # artifact-2 -> docs/guide.md
    GUIDE_ID = "artifact-2"

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
        _write(self.root, "docs/guide.md", _GUIDE_BODY)
        _write_declared_manifest(self.root)

    def _descriptor(self, artifact_id: str) -> ExperimentArtifactRefModel:
        return validate_pack_content_manifest(self.root).artifacts[artifact_id]


class HappyPathTests(PackFixture):
    def test_resolves_by_opaque_id(self):
        resolved = resolve_pack_artifact(self.root, self.GUIDE_ID)
        self.assertIsInstance(resolved, ResolvedPackArtifact)
        self.assertEqual(resolved.data, _GUIDE_BODY)

    def test_resolves_by_descriptor(self):
        descriptor = self._descriptor(self.GUIDE_ID)
        resolved = resolve_pack_artifact(self.root, descriptor)
        self.assertEqual(resolved.data, _GUIDE_BODY)
        self.assertEqual(resolved.identity, resolve_pack_artifact(self.root, self.GUIDE_ID).identity)

    def test_projects_canonical_identity(self):
        resolved = resolve_pack_artifact(self.root, self.GUIDE_ID)
        identity = resolved.identity
        self.assertIsInstance(identity, ArtifactIdentity)
        self.assertEqual(identity.artifact_id, self.GUIDE_ID)
        self.assertEqual(identity.version, "0.1.0")
        self.assertEqual(identity.media_type, "application/octet-stream")
        self.assertEqual(identity.digest, "sha256:" + hashlib.sha256(_GUIDE_BODY).hexdigest())

    def test_digest_matches_returned_bytes(self):
        resolved = resolve_pack_artifact(self.root, self.GUIDE_ID)
        recomputed = "sha256:" + hashlib.sha256(resolved.data).hexdigest()
        self.assertEqual(resolved.identity.digest, recomputed)

    def test_result_is_immutable(self):
        resolved = resolve_pack_artifact(self.root, self.GUIDE_ID)
        self.assertTrue(dataclasses.is_dataclass(resolved))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            resolved.data = b"tampered"  # type: ignore[misc]

    def test_every_declared_artifact_resolves(self):
        for artifact_id in ("artifact-0", "artifact-1", "artifact-2"):
            with self.subTest(artifact_id=artifact_id):
                resolved = resolve_pack_artifact(self.root, artifact_id)
                self.assertEqual(
                    resolved.identity.digest,
                    "sha256:" + hashlib.sha256(resolved.data).hexdigest(),
                )

    def test_selected_sdl_parent_is_opened_exactly_once(self):
        # artifact-1 is sdl/example.sdl.yaml, which is also the pack parent.
        # Parent parsing must reuse the materialized bytes, not reopen the member.
        opened: list[str] = []
        real_open_member = _pack_fs.open_member

        def counting(root_fd, rel, **kwargs):
            opened.append(rel)
            return real_open_member(root_fd, rel, **kwargs)

        with mock.patch.object(_pack_fs, "open_member", side_effect=counting):
            resolve_pack_artifact(self.root, "artifact-1")
        self.assertEqual(opened.count("sdl/example.sdl.yaml"), 1)


class SelectorTests(PackFixture):
    def test_unknown_id_is_rejected(self):
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, "artifact-404")

    def test_non_selector_type_is_rejected(self):
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, 123)  # type: ignore[arg-type]

    def test_descriptor_cannot_override_manifest_claims(self):
        descriptor = self._descriptor(self.GUIDE_ID)
        tampered = descriptor.model_copy(update={"media_type": "text/x-injected"})
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, tampered)

    def test_descriptor_cannot_override_checksum(self):
        descriptor = self._descriptor(self.GUIDE_ID)
        forged = descriptor.checksum.model_copy(update={"value": "a" * 64})
        tampered = descriptor.model_copy(update={"checksum": forged})
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, tampered)


class ByteIdentityTests(PackFixture):
    def test_tampered_bytes_fail_closed(self):
        _write(self.root, "docs/guide.md", b"tampered guide\n")
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)

    def test_undeclared_file_is_rejected(self):
        _write(self.root, "assets/extra.bin", b"undeclared")
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)

    def test_declared_missing_file_is_rejected(self):
        (self.root / "docs/guide.md").unlink()
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)

    def test_escaping_uri_is_rejected(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["artifacts"][self.GUIDE_ID]["uri"] = "raes-environment-pack:/../outside"
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)

    def test_set_digest_mismatch_is_rejected(self):
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["set_digest"] = "sha256:" + "1" * 64
        (self.root / "associated-artifacts.json").write_text(json.dumps(payload))
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)


class ParentSelectionTests(PackFixture):
    def test_missing_sdl_parent_is_rejected(self):
        (self.root / "sdl/example.sdl.yaml").unlink()
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)

    def test_ambiguous_sdl_parent_is_rejected(self):
        # Two same-named SDL parents both identity-bind; selection must refuse
        # rather than pick one.
        _write(self.root, "sdl/variant.sdl.yaml", _VALID_SDL.encode())
        payload = json.loads((self.root / "associated-artifacts.json").read_text())
        payload["artifacts"]["artifact-3"] = _artifact(
            "artifact-3", "sdl/variant.sdl.yaml", _VALID_SDL.encode()
        )
        model = AssociatedArtifactManifestModel.model_validate(payload)
        model = model.model_copy(update={"set_digest": associated_artifact_set_digest(model)})
        (self.root / "associated-artifacts.json").write_text(model.model_dump_json(indent=2))
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)


class SafetyTests(PackFixture):
    def test_symlinked_member_is_rejected(self):
        target = self.root / "outside"
        target.write_bytes(b"x")
        link = self.root / "assets/link"
        link.parent.mkdir()
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)

    def test_hardlink_is_rejected(self):
        link = self.root / "guide-link"
        try:
            os.link(self.root / "docs/guide.md", link)
        except (OSError, NotImplementedError):
            self.skipTest("hardlinks unavailable")
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID)

    def test_unsupported_descriptor_platform_is_rejected(self):
        with mock.patch.object(digest, "_NOFOLLOW", 0):
            with self.assertRaises(PackDigestError):
                resolve_pack_artifact(self.root, self.GUIDE_ID)


class LimitTests(PackFixture):
    def test_selected_byte_budget_is_enforced(self):
        limits = AssociatedArtifactValidationLimits(
            max_artifacts=8, max_artifact_bytes=4, max_total_bytes=4096
        )
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID, artifact_limits=limits)

    def test_member_count_limit_is_enforced(self):
        limits = PackValidationLimits(max_members=2)
        with self.assertRaises(PackDigestError):
            resolve_pack_artifact(self.root, self.GUIDE_ID, limits=limits)

    def test_default_limits_resolve(self):
        resolved = resolve_pack_artifact(
            self.root,
            self.GUIDE_ID,
            limits=PackValidationLimits(),
            artifact_limits=AssociatedArtifactValidationLimits(),
        )
        self.assertEqual(resolved.data, _GUIDE_BODY)


if __name__ == "__main__":
    unittest.main()
