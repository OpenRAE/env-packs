"""Pack-local resolution smoke tests."""

from __future__ import annotations

import pathlib
import unittest

import yaml

from raes_env_packs import resolve_pack_artifact, validate_pack


_ROOT = pathlib.Path(__file__).resolve().parents[2]


class ResolutionTests(unittest.TestCase):
    def test_every_sdl_content_artifact_resolves_exactly(self) -> None:
        result = validate_pack(_ROOT)
        self.assertTrue(result.ok, result.errors)
        sdl = yaml.safe_load(
            (_ROOT / "sdl" / "techvault.sdl.yaml").read_text(encoding="utf-8")
        )
        for content_id, item in sdl["content"].items():
            if "source" not in item:
                continue
            with self.subTest(content_id=content_id):
                exact = item["source"]["artifact_requirement"]["exact_artifact"]
                resolved = resolve_pack_artifact(_ROOT, item["source"]["name"])
                self.assertEqual(resolved.identity.artifact_id, exact["artifact_id"])
                self.assertEqual(resolved.identity.version, exact["version"])
                self.assertEqual(resolved.identity.media_type, exact["media_type"])
                self.assertEqual(resolved.identity.digest, exact["digest"])


if __name__ == "__main__":
    unittest.main()
