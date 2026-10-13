"""Pack-local AI Escape Lab smoke contract."""

from __future__ import annotations

import json
import pathlib
import unittest

import yaml

from raes_env_packs import validate_pack


_PACK = pathlib.Path(__file__).resolve().parents[2]


class PackSmokeTests(unittest.TestCase):
    def test_pack_validates_and_inventories_match(self) -> None:
        result = validate_pack(_PACK)
        self.assertTrue(result.ok, result.errors)
        challenges = yaml.safe_load((_PACK / "challenges/challenges.yaml").read_text())["challenges"]
        flags = yaml.safe_load((_PACK / "flags/placement.yaml").read_text())["flags"]
        readiness = json.loads((_PACK / "build/runtime/readiness.json").read_text())
        self.assertEqual([row["flag_id"] for row in flags], [row["flag_id"] for row in challenges])
        self.assertEqual(readiness["flag_count"], len(flags))
        self.assertEqual(readiness["hint_count"], sum(len(row["hints"]) for row in challenges))


if __name__ == "__main__":
    unittest.main()
