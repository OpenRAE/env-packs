"""Archive-ingestion safety for the distribution route (ADR 0037, ASP-0004)."""

from __future__ import annotations

import io
import os
import tarfile
import tempfile
import unittest

from raes_env_packs import distribution as dist

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_TECHVAULT = os.path.join(_REPO, "packs", "techvault")


def _tar(members, path: str) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for info, data in members:
            if data is None:
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))


class ArchiveSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.staging = os.path.join(self.tmp.name, "out", "techvault")

    def _reject(self, members, *, limits=None) -> None:
        archive = os.path.join(self.tmp.name, "bad.tar.gz")
        _tar(members, archive)
        with self.assertRaises(dist.DistributionError):
            dist.stage_pack_archive(archive, self.staging, limits=limits)

    def test_good_archive_extracts(self) -> None:
        archive = os.path.join(self.tmp.name, "good.tar.gz")
        dist.export_pack_archive(_TECHVAULT, archive)
        dist.stage_pack_archive(archive, self.staging)
        self.assertTrue(os.path.isfile(os.path.join(self.staging, "pack.yaml")))

    def test_deterministic_export(self) -> None:
        a = os.path.join(self.tmp.name, "a.tgz")
        b = os.path.join(self.tmp.name, "b.tgz")
        self.assertEqual(
            dist.export_pack_archive(_TECHVAULT, a),
            dist.export_pack_archive(_TECHVAULT, b),
        )
        self.assertRegex(dist.export_pack_archive(_TECHVAULT, a), r"^sha256:[0-9a-f]{64}$")

    def test_path_traversal_is_rejected(self) -> None:
        self._reject([(tarfile.TarInfo("../evil.txt"), b"x")])

    def test_absolute_path_is_rejected(self) -> None:
        self._reject([(tarfile.TarInfo("/etc/evil"), b"x")])

    def test_symlink_member_is_rejected(self) -> None:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        self._reject([(info, None)])

    def test_hardlink_member_is_rejected(self) -> None:
        info = tarfile.TarInfo("hard")
        info.type = tarfile.LNKTYPE
        info.linkname = "pack.yaml"
        self._reject([(info, None)])

    def test_special_file_member_is_rejected(self) -> None:
        info = tarfile.TarInfo("dev")
        info.type = tarfile.CHRTYPE
        self._reject([(info, None)])

    def test_duplicate_member_is_rejected(self) -> None:
        self._reject([
            (tarfile.TarInfo("pack.yaml"), b"a"),
            (tarfile.TarInfo("pack.yaml"), b"b"),
        ])

    def test_oversized_member_is_rejected(self) -> None:
        self._reject(
            [(tarfile.TarInfo("big.bin"), b"x" * 4096)],
            limits=dist.ArchiveLimits(max_member_bytes=16),
        )

    def test_member_count_limit_is_enforced(self) -> None:
        self._reject(
            [(tarfile.TarInfo(f"f{i}.txt"), b"x") for i in range(10)],
            limits=dist.ArchiveLimits(max_members=3),
        )

    def test_total_size_limit_is_enforced(self) -> None:
        self._reject(
            [(tarfile.TarInfo(f"f{i}.txt"), b"x" * 100) for i in range(10)],
            limits=dist.ArchiveLimits(max_total_bytes=150),
        )


if __name__ == "__main__":
    unittest.main()
