"""Regression checks for first-party content in published distributions."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

import yaml

from raes_env_packs import KitSource, build_kit_catalog, source_release
from tests.test_kits import KIT_ID, KIT_VERSION, _write_synthetic_kit

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_PACK_NAMES = ("techvault", "techvault-participant-study", "ai-escape-lab")


def _source_files(root: pathlib.Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }


def _public_kit_files(root: pathlib.Path) -> dict[str, bytes]:
    """Admit only the exact inventory of validated, open kit releases."""

    source = KitSource(id="public-distribution", revision="candidate", root=str(root))
    catalog = build_kit_catalog((source,))
    if not catalog["entries"]:
        raise ValueError("public kit collection is empty")
    files = {}
    for entry in catalog["entries"]:
        release = source_release(source, entry["id"], entry["version"])
        if release.document["license"]["redistribution"] != "open":
            raise ValueError("public kit collection contains a restricted release")
        prefix = f"{release.id}/{release.version}"
        for member in release.inventory:
            files[f"{prefix}/{member}"] = pathlib.Path(release.root, member).read_bytes()
    if _source_files(root / "kits") != files:
        raise ValueError("public kit collection contains files outside admitted releases")
    return files


class PublicKitInventoryTests(unittest.TestCase):
    def test_orphan_file_is_rejected_by_the_distribution_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            _write_synthetic_kit(root / "kits" / KIT_ID / KIT_VERSION)
            self.assertTrue(_public_kit_files(root))
            orphan = root / "kits" / KIT_ID / "private.pem"
            orphan.write_text("synthetic unadmitted content", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside admitted releases"):
                _public_kit_files(root)


class FirstPartyPackDistributionTests(unittest.TestCase):
    def test_wheel_and_sdist_ship_the_exact_complete_packs(self) -> None:
        expected = {
            f"packs/{name}": _source_files(_ROOT / "packs" / name)
            for name in _PACK_NAMES
        }
        for files in expected.values():
            self.assertIn("pack.yaml", files)
            self.assertIn("associated-artifacts.json", files)
        expected["kits"] = _public_kit_files(_ROOT)
        manifests = sorted((_ROOT / "kits").glob("*/*/kit.yaml"))
        self.assertTrue(manifests, "the distribution must contain kit releases")
        digests = {}
        for manifest in manifests:
            document = yaml.safe_load(manifest.read_bytes())
            # The reusable schema also allows private catalogs. This public
            # distribution must not silently ship or omit a restricted release.
            self.assertEqual(document["license"]["redistribution"], "open")
            associated = json.loads(
                (manifest.parent / document["associated_artifact_manifest"]).read_bytes()
            )
            digests[f"{document['id']}@{document['version']}"] = associated["set_digest"]

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
                for resource, files in expected.items():
                    prefix = f"raes_env_packs/resources/{resource}/"
                    wheel_files = {
                        name.removeprefix(prefix): archive.read(name)
                        for name in archive.namelist()
                        if name.startswith(prefix) and not name.endswith("/")
                    }
                    self.assertEqual(wheel_files, files)

            with tarfile.open(sdist, mode="r:gz") as archive:
                root = archive.getnames()[0].split("/", 1)[0]
                for resource, files in expected.items():
                    prefix = f"{root}/{resource}/"
                    sdist_files = {}
                    for member in archive.getmembers():
                        if not member.isfile() or not member.name.startswith(prefix):
                            continue
                        handle = archive.extractfile(member)
                        self.assertIsNotNone(handle)
                        assert handle is not None
                        sdist_files[member.name.removeprefix(prefix)] = handle.read()
                    self.assertEqual(sdist_files, files)

            # The default build above builds a wheel FROM the sdist. Compare
            # it with a direct checkout wheel to cover both acquisition routes.
            direct = output / "direct"
            subprocess.run(
                [sys.executable, "-m", "build", "--wheel", "--no-isolation",
                 "--outdir", str(direct)],
                cwd=_ROOT, check=True, capture_output=True, text=True,
            )
            with zipfile.ZipFile(next(direct.glob("*.whl"))) as archive:
                prefix = "raes_env_packs/resources/kits/"
                self.assertEqual({
                    name.removeprefix(prefix): archive.read(name)
                    for name in archive.namelist()
                    if name.startswith(prefix) and not name.endswith("/")
                }, expected["kits"])

            installed = output / "installed"
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-deps", "--no-index",
                 "--no-compile", "--disable-pip-version-check", "--target",
                 str(installed), str(wheel)],
                cwd=output, check=True, capture_output=True, text=True,
            )
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", _INSTALLED_CONSUMER,
                 str(installed)],
                cwd=output, check=True, capture_output=True, text=True,
            )
            self.assertEqual(json.loads(result.stdout), digests)


_INSTALLED_CONSUMER = """
import json
import shutil
import sys
import tempfile
from pathlib import Path

installed = Path(sys.argv[1])
sys.path.insert(0, str(installed))
import raes_env_packs as packs

assert Path(packs.__file__).is_relative_to(installed)
assert not (Path.cwd() / '.git').exists()
source = packs.bundled_kit_source()
assert Path(source.root).is_relative_to(installed)
assert source.id == 'openrae-env-packs'
assert source.revision == f'raes-env-packs=={packs.__version__}'
catalog = packs.build_kit_catalog((source,))
assert catalog['entries']
digests = {}
for entry in catalog['entries']:
    release = packs.source_release(source, entry['id'], entry['version'])
    assert entry['source'] == {'id': source.id, 'revision': source.revision}
    digests[f'{release.id}@{release.version}'] = release.associated_artifacts.set_digest

# Exercise the same integrity boundary on acquired, released bytes.
entry = catalog['entries'][0]
release = packs.source_release(source, entry['id'], entry['version'])
for change in ('changed', 'missing', 'extra'):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / 'kit'
        shutil.copytree(release.root, root)
        if change == 'changed':
            (root / 'README.md').write_text('tampered')
        elif change == 'missing':
            (root / 'README.md').unlink()
        else:
            (root / 'extra.txt').write_text('undeclared')
        try:
            packs.load_kit_release(root)
        except packs.KitError:
            pass
        else:
            raise AssertionError(f'{change} kit payload passed validation')

assert not list(Path(source.root, 'kits').rglob('__pycache__'))
print(json.dumps(digests, sort_keys=True))
"""


if __name__ == "__main__":
    unittest.main()
