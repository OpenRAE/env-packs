"""Package metadata and the reviewed ACES dependency seam.

The project version is owned by release-please in ``pyproject.toml``; the
package derives ``__version__`` from installed metadata (ADR 0008).
"""

from __future__ import annotations

import importlib.util
import pathlib
import re
import tomllib
import unittest

import aces_scenario_packs


class VersionTests(unittest.TestCase):
    def test_version_is_a_semver_string(self):
        self.assertIsInstance(aces_scenario_packs.__version__, str)
        self.assertRegex(aces_scenario_packs.__version__, r"^\d+\.\d+\.\d+$")


class AcesDependencyTests(unittest.TestCase):
    def test_aces_sdl_is_exactly_pinned(self):
        """ADR 0011: aces-sdl is a single, exactly (``==``) pinned runtime dep.

        The concrete version is deliberately NOT asserted here. A Dependabot
        bump edits only ``pyproject.toml``; asserting the literal version would
        turn every bump into a manual test edit (ADR 0016).
        This guards the *invariant* — exactly one ``aces-sdl`` requirement,
        pinned with ``==`` — while the version itself advances through the
        reviewed pin (ADR 0011) and the CI compatibility gate.
        """
        root = pathlib.Path(__file__).resolve().parents[1]
        with (root / "pyproject.toml").open("rb") as handle:
            dependencies = tomllib.load(handle)["project"]["dependencies"]

        aces_specs = [dep for dep in dependencies
                      if re.match(r"aces-sdl(?![\w-])", dep.strip())]
        self.assertEqual(
            len(aces_specs), 1,
            f"expected exactly one aces-sdl requirement, got {aces_specs}")

        spec = aces_specs[0].replace(" ", "")
        self.assertTrue(
            spec.startswith("aces-sdl=="),
            f"aces-sdl must be exactly (==) pinned per ADR 0011, got {spec!r}")
        self.assertNotRegex(
            spec, r"[<>~!,]",
            f"aces-sdl must be a single exact pin, no ranges (ADR 0011), got {spec!r}")
        self.assertRegex(
            spec[len("aces-sdl=="):], r"^\d+(\.\d+)+",
            f"aces-sdl pin must carry a concrete version, got {spec!r}")

    def test_bespoke_oracle_package_surface_is_absent(self):
        package_root = pathlib.Path(aces_scenario_packs.__file__).resolve().parent

        self.assertFalse((package_root / "oracle_model.py").exists())
        self.assertFalse((package_root / "resources" / "oracle").exists())
        self.assertIsNone(importlib.util.find_spec("aces_scenario_packs.oracle_model"))


if __name__ == "__main__":
    unittest.main()
