"""Regression coverage for the defensive-tooling author walkthrough."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WALKTHROUGH = ROOT / "tests_integration" / "defensive_tooling_composition.py"


class DefensiveToolingWalkthroughTests(unittest.TestCase):
    def test_walkthrough_completes_with_only_static_authoring_claims(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT / "src"), env.get("PYTHONPATH", "")]
        )

        completed = subprocess.run(
            [
                sys.executable,
                str(WALKTHROUGH),
                "--catalog",
                str(ROOT),
                "--source-revision",
                "test-revision",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr or completed.stdout,
        )
        self.assertRegex(completed.stdout, r"\d+ passed, 0 failed")
        self.assertIn("static authoring evidence only", completed.stdout)


if __name__ == "__main__":
    unittest.main()
