"""Regression coverage for the two-audience bundle walkthrough."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WALKTHROUGH = ROOT / "tests_integration" / "two_audience_bundles.py"


class TwoAudienceBundlesWalkthroughTests(unittest.TestCase):
    def test_walkthrough_proves_distinct_safe_views_over_unchanged_sdl(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT / "src"), env.get("PYTHONPATH", "")]
        )

        completed = subprocess.run(
            [sys.executable, str(WALKTHROUGH)],
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
        self.assertIn("minimal SDL remains byte-for-byte unchanged", completed.stdout)
        self.assertIn("guided and unguided participant content differs", completed.stdout)
        self.assertIn("facilitator material stays operator-only", completed.stdout)
        self.assertIn("restricted participant content is rejected", completed.stdout)
        self.assertIn("malformed bundle selection is rejected", completed.stdout)

    def test_explicit_workspace_retains_only_the_valid_example(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT / "src"), env.get("PYTHONPATH", "")]
        )
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "walkthrough"
            completed = subprocess.run(
                [sys.executable, str(WALKTHROUGH), "--workspace", str(workspace)],
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
            self.assertTrue(
                (workspace / "catalog" / "environments" / "two-audience-example")
                .is_dir()
            )
            self.assertTrue(
                (workspace / "release" / "two-audience-example-0.1.0").is_dir()
            )
            self.assertFalse((workspace / "negative-cases").exists())


if __name__ == "__main__":
    unittest.main()
