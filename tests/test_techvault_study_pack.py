"""The study copy preserves TechVault's authored scenario and content."""

from __future__ import annotations

import hashlib
import pathlib
import unittest

import yaml

from raes_env_packs import validate_pack
from raes_env_packs.digest import pack_content_digest

_ROOT = pathlib.Path(__file__).resolve().parents[1] / "packs"
_BASE = _ROOT / "techvault"
_STUDY = _ROOT / "techvault-participant-study"


class StudyPackTests(unittest.TestCase):
    def test_study_pack_is_valid_and_has_distinct_identity(self) -> None:
        result = validate_pack(_STUDY)
        self.assertTrue(result.ok, result.errors)
        self.assertNotEqual(pack_content_digest(_BASE), pack_content_digest(_STUDY))

    def test_sdl_diff_is_limited_to_scenario_name(self) -> None:
        base = yaml.safe_load((_BASE / "sdl/techvault.sdl.yaml").read_text())
        study = yaml.safe_load(
            (_STUDY / "sdl/techvault-participant-study.sdl.yaml").read_text()
        )
        self.assertEqual(study.pop("name"), "techvault-participant-study")
        self.assertEqual(base.pop("name"), "techvault")
        self.assertEqual(study, base)

    def test_exact_content_assets_are_identical(self) -> None:
        for source in (_BASE / "assets/content").iterdir():
            if not source.is_file():
                continue
            with self.subTest(asset=source.name):
                target = _STUDY / "assets/content" / source.name
                self.assertEqual(
                    hashlib.sha256(target.read_bytes()).digest(),
                    hashlib.sha256(source.read_bytes()).digest(),
                )
