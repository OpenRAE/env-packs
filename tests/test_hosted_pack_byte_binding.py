"""Every hosted pack's associated-artifact manifest byte-binds its current files."""

from __future__ import annotations

import pathlib
import unittest

from raes_env_packs import validate_pack_content_manifest


_PACKS = pathlib.Path(__file__).resolve().parents[1] / "packs"


class HostedPackByteBindingTests(unittest.TestCase):
    def test_every_hosted_pack_manifest_byte_binds(self) -> None:
        packs = sorted(path.parent for path in _PACKS.glob("*/pack.yaml"))
        self.assertTrue(packs, "no hosted packs found under packs/")
        for pack in packs:
            with self.subTest(pack=pack.name):
                validate_pack_content_manifest(pack)


if __name__ == "__main__":
    unittest.main()
