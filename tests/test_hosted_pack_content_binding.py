"""Byte binding of every hosted pack's associated-artifact manifest (#470).

Every directory under ``packs/`` is published first-party content (ADR 0036), and
verified install requires its RAES associated-artifact manifest to bind the
pack's exact bytes (ADR 0037). This gate runs the RAES validator (ADR 0012,
ADR 0031) on each one, so a content change that skips re-deriving the manifest
fails the ``tests`` job instead of a later install.
"""

from __future__ import annotations

import pathlib
import unittest

from raes_env_packs import content_ci
from raes_env_packs.digest import validate_pack_content_manifest

_PACKS = pathlib.Path(__file__).resolve().parents[1] / "packs"


def _hosted_packs() -> tuple[str, ...]:
    """Return every pack directory with the discovery the hosted-pack gates use."""

    failures: list[str] = []
    names = content_ci._packs(str(_PACKS), failures, require_root=True)
    if failures:
        raise AssertionError(f"pack discovery failed under {_PACKS}: {failures}")
    return names


class HostedPackContentBindingTests(unittest.TestCase):
    def test_discovery_finds_hosted_packs(self) -> None:
        self.assertIn("ai-escape-lab", _hosted_packs())

    def test_every_hosted_pack_manifest_binds_its_bytes(self) -> None:
        for name in _hosted_packs():
            with self.subTest(pack=name):
                validate_pack_content_manifest(_PACKS / name)


if __name__ == "__main__":
    unittest.main()
