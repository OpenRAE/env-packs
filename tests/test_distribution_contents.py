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
_TECHVAULT = _ROOT / "packs" / "techvault"
_WHEEL_PREFIX = "raes_env_packs/resources/packs/techvault/"


def _source_files() -> dict[str, bytes]:
    return {
        path.relative_to(_TECHVAULT).as_posix(): path.read_bytes()
        for path in _TECHVAULT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }


class TechVaultDistributionTests(unittest.TestCase):
    def test_wheel_and_sdist_ship_the_exact_complete_pack(self) -> None:
        expected = _source_files()
        self.assertIn("pack.yaml", expected)
        self.assertIn("sdl/techvault.sdl.yaml", expected)
        self.assertIn("associated-artifacts.json", expected)

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
                wheel_files = {
                    name.removeprefix(_WHEEL_PREFIX): archive.read(name)
                    for name in archive.namelist()
                    if name.startswith(_WHEEL_PREFIX) and not name.endswith("/")
                }
            self.assertEqual(wheel_files, expected)

            with tarfile.open(sdist, mode="r:gz") as archive:
                root = archive.getnames()[0].split("/", 1)[0]
                prefix = f"{root}/packs/techvault/"
                sdist_files = {}
                for member in archive.getmembers():
                    if not member.isfile() or not member.name.startswith(prefix):
                        continue
                    handle = archive.extractfile(member)
                    self.assertIsNotNone(handle)
                    assert handle is not None
                    sdist_files[member.name.removeprefix(prefix)] = handle.read()
            self.assertEqual(sdist_files, expected)


if __name__ == "__main__":
    unittest.main()
