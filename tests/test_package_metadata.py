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
        """ADR 0047: raes is a single runtime dep pinned with ``==``.

        The concrete version is deliberately NOT asserted here. A version change
        edits ``pyproject.toml``, ``requirements/runtime.in``, and the locks;
        asserting the literal version would turn every change into a manual test
        edit (ADR 0016). This guards the *invariant*: exactly one ``raes``
        requirement, pinned to one exact version.
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
            f"raes must pin one exact version per ADR 0047, got {spec!r}")

    def test_bespoke_oracle_package_surface_is_absent(self):
        package_root = pathlib.Path(raes_env_packs.__file__).resolve().parent

        self.assertFalse((package_root / "oracle_model.py").exists())
        self.assertFalse((package_root / "resources" / "oracle").exists())
        self.assertIsNone(importlib.util.find_spec("raes_env_packs.oracle_model"))


if __name__ == "__main__":
    unittest.main()
