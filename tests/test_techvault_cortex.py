"""Executable test for TechVault's portable offline Cortex analyzer."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile
import unittest


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_ANALYZER = (
    _ROOT
    / "packs"
    / "techvault"
    / "assets"
    / "content"
    / "cortex-techvault-analyzer.py"
)


class TechVaultCortexTests(unittest.TestCase):
    def test_offline_analyzer_emits_the_expected_bounded_report(self) -> None:
        self.assertTrue(os.access(_ANALYZER, os.X_OK))
        cases = (
            ("172.20.1.30", "attacker", "malicious", "malicious"),
            ("172.20.1.31", "unclassified", "unknown", "info"),
        )
        for observable, role, verdict, level in cases:
            with self.subTest(observable=observable), tempfile.TemporaryDirectory() as directory:
                job = pathlib.Path(directory)
                (job / "input").mkdir()
                (job / "output").mkdir()
                (job / "input" / "input.json").write_text(
                    json.dumps({"data": observable, "dataType": "ip"}),
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [str(_ANALYZER), str(job)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                report = json.loads(
                    (job / "output" / "output.json").read_text(encoding="utf-8")
                )

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertTrue(report["success"])
                self.assertEqual(report["full"]["scenario_role"], role)
                self.assertEqual(report["full"]["verdict"], verdict)
                self.assertTrue(report["full"]["offline"])
                self.assertEqual(report["summary"]["taxonomies"][0]["level"], level)


if __name__ == "__main__":
    unittest.main()
