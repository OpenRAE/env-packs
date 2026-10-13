"""Regression checks for first-party content in published distributions."""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile


_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACK_NAMES = ("techvault", "techvault-participant-study", "ai-escape-lab")


def _source_files(pack_name: str) -> dict[str, bytes]:
    pack = _ROOT / "packs" / pack_name
    return {
        path.relative_to(pack).as_posix(): path.read_bytes()
        for path in pack.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }


class FirstPartyPackDistributionTests(unittest.TestCase):
    def test_wheel_and_sdist_ship_the_exact_complete_packs(self) -> None:
        expected = {name: _source_files(name) for name in _PACK_NAMES}
        for files in expected.values():
            self.assertIn("pack.yaml", files)
            self.assertIn("associated-artifacts.json", files)

        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--no-isolation",
                    "--outdir",
                    directory,
                ],
                cwd=_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            output = pathlib.Path(directory)
            wheel = next(output.glob("*.whl"))
            sdist = next(output.glob("*.tar.gz"))

            with zipfile.ZipFile(wheel) as archive:
                for pack_name, files in expected.items():
                    prefix = f"raes_env_packs/resources/packs/{pack_name}/"
                    wheel_files = {
                        name.removeprefix(prefix): archive.read(name)
                        for name in archive.namelist()
                        if name.startswith(prefix) and not name.endswith("/")
                    }
                    self.assertEqual(wheel_files, files)

            with tarfile.open(sdist, mode="r:gz") as archive:
                root = archive.getnames()[0].split("/", 1)[0]
                for pack_name, files in expected.items():
                    prefix = f"{root}/packs/{pack_name}/"
                    sdist_files = {}
                    for member in archive.getmembers():
                        if not member.isfile() or not member.name.startswith(prefix):
                            continue
                        handle = archive.extractfile(member)
                        self.assertIsNotNone(handle)
                        assert handle is not None
                        sdist_files[member.name.removeprefix(prefix)] = handle.read()
                    self.assertEqual(sdist_files, files)


if __name__ == "__main__":
    unittest.main()
