"""Package metadata and the reviewed RAES dependency seam.

The project version is owned by release-please in ``pyproject.toml``; the
package derives ``__version__`` from installed metadata (ADR 0008).
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import tomllib
import unittest

import raes_env_packs


class VersionTests(unittest.TestCase):
    def test_version_is_a_semver_string(self):
        self.assertIsInstance(raes_env_packs.__version__, str)
        self.assertRegex(raes_env_packs.__version__, r"^\d+\.\d+\.\d+$")


class RaesDependencyTests(unittest.TestCase):
    def test_raes_declares_one_exact_version(self):
        """raes is a single runtime dep with one temporary exact pin.

        The concrete version is deliberately NOT asserted here (ADR 0016).
        Issue #623 restores the ADR 0043 ``>=`` floor and this invariant.
        """
        root = pathlib.Path(__file__).resolve().parents[1]
        with (root / "pyproject.toml").open("rb") as handle:
            dependencies = tomllib.load(handle)["project"]["dependencies"]

        raes_specs = [dep for dep in dependencies
                      if re.match(r"raes(?![\w-])", dep.strip())]
        self.assertEqual(
            len(raes_specs), 1,
            f"expected exactly one raes requirement, got {raes_specs}")

        spec = raes_specs[0].replace(" ", "")
        self.assertRegex(
            spec, r"^raes==\d+(\.\d+)+$",
            f"raes must pin one exact version until issue #623, got {spec!r}")

    def test_bespoke_oracle_package_surface_is_absent(self):
        package_root = pathlib.Path(raes_env_packs.__file__).resolve().parent

        self.assertFalse((package_root / "oracle_model.py").exists())
        self.assertFalse((package_root / "resources" / "oracle").exists())
        self.assertIsNone(importlib.util.find_spec("raes_env_packs.oracle_model"))


if __name__ == "__main__":
    unittest.main()
