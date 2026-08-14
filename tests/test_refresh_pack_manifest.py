"""Tests for the pack-author manifest refresh tool (tools/refresh_pack_manifest.py).

Editing any byte-bound pack file must be followed by a manifest refresh or the
pack fails byte-binding validation (issue #282 touched three such files at
once: a content script, the SDL, and the README).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_TOOL = _ROOT / "tools" / "refresh_pack_manifest.py"
_PACK = _ROOT / "packs" / "techvault"

_spec = importlib.util.spec_from_file_location("refresh_pack_manifest", _TOOL)
refresh_pack_manifest = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = refresh_pack_manifest
_spec.loader.exec_module(refresh_pack_manifest)

from raes_env_packs.digest import validate_pack_content_manifest


class RefreshPackManifestTests(unittest.TestCase):
    def test_refresh_recomputes_every_changed_artifact_and_the_set_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            pack_root = pathlib.Path(directory) / "techvault"
            shutil.copytree(_PACK, pack_root)

            wrapper = pack_root / "assets" / "content" / "kali-wrap-shell.sh"
            wrapper.write_bytes(wrapper.read_bytes() + b"\n# perturbed for test\n")
            readme = pack_root / "README.md"
            readme.write_text(readme.read_text(encoding="utf-8") + "\nperturbed\n", encoding="utf-8")

            manifest_before = json.loads((pack_root / "associated-artifacts.json").read_text(encoding="utf-8"))
            set_digest_before = manifest_before["set_digest"]

            with self.assertRaises(Exception):
                validate_pack_content_manifest(pack_root)

            new_set_digest = refresh_pack_manifest.refresh(pack_root)

            manifest_after = json.loads((pack_root / "associated-artifacts.json").read_text(encoding="utf-8"))
            self.assertEqual(new_set_digest, manifest_after["set_digest"])
            self.assertNotEqual(new_set_digest, set_digest_before)
            self.assertEqual(
                manifest_after["artifacts"]["techvault-kali-wrap-shell"]["checksum"]["value"],
                hashlib.sha256(wrapper.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                manifest_after["artifacts"]["techvault-pack-README-md"]["checksum"]["value"],
                hashlib.sha256(readme.read_bytes()).hexdigest(),
            )

            validate_pack_content_manifest(pack_root)  # no raise: byte-binding is clean again


if __name__ == "__main__":
    unittest.main()
