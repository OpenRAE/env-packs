"""The installed first-party source uses the existing kit contracts."""

from __future__ import annotations

import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path
from unittest.mock import Mock, patch

import raes_env_packs
from raes_env_packs import kits


class BundledKitSourceTests(unittest.TestCase):
    def test_source_names_the_installed_distribution_and_resource_root(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            (package / "resources" / "kits").mkdir(parents=True)
            with patch("importlib.resources.files", return_value=package):
                source = kits.bundled_kit_source()
            self.assertEqual(source, kits.KitSource(
                id="openrae-env-packs",
                revision=f"raes-env-packs=={version('raes-env-packs')}",
                root=str(package / "resources"),
            ))
            self.assertIs(raes_env_packs.bundled_kit_source, kits.bundled_kit_source)

    def test_missing_resources_fail_without_a_checkout_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("importlib.resources.files", return_value=Path(directory)):
                with self.assertRaisesRegex(kits.KitError, "bundled kit resources"):
                    kits.bundled_kit_source()

    def test_non_filesystem_resources_fail_without_extraction(self):
        with patch("importlib.resources.files", return_value=Mock()):
            with self.assertRaisesRegex(kits.KitError, "filesystem"):
                kits.bundled_kit_source()


if __name__ == "__main__":
    unittest.main()
