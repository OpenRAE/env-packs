"""Author-side native Suricata verification for TechVault issue #283."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tools import verify_techvault_suricata


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACK = _ROOT / "packs" / "techvault"
_IMAGE = (
    "jasonish/suricata@"
    "sha256:d64c491f6eb5d03b6562d873b3c5303e4c17d5dc1d75b3761a68319f11527dc3"
)


class NativeSuricataContractTests(unittest.TestCase):
    def test_native_commands_bind_the_exact_image_and_builtin_file(self) -> None:
        with tempfile.TemporaryDirectory() as staging:
            image_check, config_check = verify_techvault_suricata.native_commands(
                _PACK, pathlib.Path(staging)
            )
            self.assertEqual(image_check[-3:], [_IMAGE, "-s", "/var/lib/suricata/rules/suricata.rules"])
            self.assertEqual(config_check[-4:], [_IMAGE, "-T", "-c", "/etc/suricata/suricata.yaml"])
            self.assertEqual(config_check.count("-v"), 6)
            sources = [
                pathlib.Path(config_check[index + 1].split(":", 1)[0])
                for index, value in enumerate(config_check)
                if value == "-v"
            ]
            self.assertTrue(all(source.parent == pathlib.Path(staging) for source in sources))
            self.assertTrue(all(source.is_file() for source in sources))

    def test_native_verifier_requires_complete_success_evidence(self) -> None:
        calls = 0

        def runner(argv, **kwargs):
            nonlocal calls
            calls += 1
            output = ""
            if calls == 2:
                output = (
                    "3 rule files processed. 52088 rules successfully loaded, "
                    "0 rules failed, 0\n"
                    "Configuration provided was successfully loaded. Exiting.\n"
                )
            return subprocess.CompletedProcess(argv, 0, output)

        self.assertEqual(verify_techvault_suricata.verify(_PACK, runner=runner), [])

    def test_native_verifier_rejects_missing_builtin_file(self) -> None:
        calls = 0

        def runner(argv, **kwargs):
            nonlocal calls
            calls += 1
            return subprocess.CompletedProcess(argv, 1 if calls == 1 else 0, "")

        errors = verify_techvault_suricata.verify(_PACK, runner=runner)
        self.assertIn("suricata.native-built-in-rules-failed", errors)

    def test_native_verifier_rejects_incomplete_engine_output(self) -> None:
        def runner(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, "configuration loaded")

        errors = verify_techvault_suricata.verify(_PACK, runner=runner)
        self.assertIn("suricata.native-configuration-evidence-incomplete", errors)

    def test_native_verifier_rejects_multidigit_count_mismatches(self) -> None:
        outputs = (
            "13 rule files processed. 52088 rules successfully loaded, 0 rules failed, 0\n"
            "Configuration provided was successfully loaded. Exiting.\n",
            "3 rule files processed. 52088 rules successfully loaded, 10 rules failed, 0\n"
            "Configuration provided was successfully loaded. Exiting.\n",
        )
        for output in outputs:
            with self.subTest(output=output):
                calls = 0

                def runner(argv, **kwargs):
                    nonlocal calls
                    calls += 1
                    return subprocess.CompletedProcess(argv, 0, output if calls == 2 else "")

                errors = verify_techvault_suricata.verify(_PACK, runner=runner)
                self.assertIn("suricata.native-configuration-evidence-incomplete", errors)

    def test_native_verifier_rejects_bytes_inconsistent_with_manifest(self) -> None:
        calls = 0

        def runner(argv, **kwargs):
            nonlocal calls
            calls += 1
            return subprocess.CompletedProcess(argv, 0, "")

        with tempfile.TemporaryDirectory() as temp_dir:
            copied_pack = pathlib.Path(temp_dir) / "techvault"
            shutil.copytree(_PACK, copied_pack)
            rules = copied_pack / "assets" / "content" / "suricata-local.rules"
            rules.write_bytes(rules.read_bytes() + b"\n# tampered\n")
            errors = verify_techvault_suricata.verify(copied_pack, runner=runner)

        self.assertEqual(errors, ["suricata.native-content-invalid"])
        self.assertEqual(calls, 0)

    @unittest.skipUnless(
        os.environ.get("TECHVAULT_NATIVE_SURICATA") == "1",
        "set TECHVAULT_NATIVE_SURICATA=1 to run the exact Docker image",
    )
    def test_exact_image_accepts_all_declared_rule_sources(self) -> None:
        self.assertEqual(verify_techvault_suricata.verify(_PACK), [])


if __name__ == "__main__":
    unittest.main()
