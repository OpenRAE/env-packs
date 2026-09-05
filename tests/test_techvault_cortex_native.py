"""Opt-in exact-image integration gate for TechVault Cortex enrichment."""

from __future__ import annotations

import os
import pathlib
import subprocess
import unittest


_ROOT = pathlib.Path(__file__).resolve().parents[1]


class NativeCortexContractTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("TECHVAULT_NATIVE_CORTEX") == "1",
        "set TECHVAULT_NATIVE_CORTEX=1 to run the exact-image Cortex gate",
    )
    def test_exact_images_execute_enrichment_and_connect_thehive(self) -> None:
        result = subprocess.run(
            [str(_ROOT / "tools" / "verify_techvault_cortex.py")],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"job_status": "Success"', result.stdout)
        self.assertIn('"thehive_cortex_status": "OK"', result.stdout)


if __name__ == "__main__":
    unittest.main()
