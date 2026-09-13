"""Tests for the author-side SDL rebinding tool (tools/refresh_pack_sdl_binding.py)."""

from __future__ import annotations

import importlib.util
import pathlib
import shutil
import sys
import tempfile
import unittest

from raes_env_packs import validate_pack
from raes_env_packs.digest import validate_pack_content_manifest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_TOOL = _ROOT / "tools" / "refresh_pack_sdl_binding.py"
_spec = importlib.util.spec_from_file_location("refresh_pack_sdl_binding", _TOOL)
tool = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = tool
_spec.loader.exec_module(tool)


class RefreshPackSdlBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.pack = tmp / "techvault"
        shutil.copytree(_ROOT / "packs" / "techvault", self.pack)
        self.sdl = self.pack / "sdl" / "techvault.sdl.yaml"

    def _edit_sdl_semantically(self) -> None:
        text = self.sdl.read_text(encoding="utf-8")
        marker = "    description: Built-in domain administrator.\n"
        self.assertEqual(text.count(marker), 1)
        self.sdl.write_text(
            text.replace(marker, "    description: Built-in domain administrator account.\n"),
            encoding="utf-8",
        )

    def _binding_errors(self) -> list[str]:
        return [
            error
            for error in validate_pack(self.pack).errors
            if error.startswith("sdl.bindings")
        ]

    def test_refresh_retargets_bindings_and_rebinds_the_manifest(self) -> None:
        self._edit_sdl_semantically()
        self.assertEqual(
            self._binding_errors(),
            ["sdl.bindings-unresolved: sdl/techvault.bindings.json"],
        )

        tool.refresh(self.pack)

        self.assertEqual(self._binding_errors(), [])
        validate_pack_content_manifest(self.pack)

    def test_refresh_is_idempotent_on_an_unchanged_pack(self) -> None:
        bindings = self.pack / "sdl" / "techvault.bindings.json"
        manifest = self.pack / "associated-artifacts.json"
        before = (bindings.read_bytes(), manifest.read_bytes())

        tool.refresh(self.pack)

        self.assertEqual((bindings.read_bytes(), manifest.read_bytes()), before)

    def test_refresh_refuses_symlinked_pack_members(self) -> None:
        for rel in (
            "sdl/techvault.bindings.json",
            "associated-artifacts.json",
            "sdl/techvault.sdl.yaml",
        ):
            with self.subTest(member=rel):
                pack = self.pack.parent / f"linked-{rel.replace('/', '-')}"
                shutil.copytree(self.pack, pack)
                member = pack / rel
                outside = self.pack.parent / f"outside-{member.name}"
                shutil.copy(member, outside)
                if rel.endswith(".sdl.yaml"):
                    text = outside.read_text(encoding="utf-8")
                    outside.write_text(
                        text.replace(
                            "    description: Built-in domain administrator.\n",
                            "    description: Built-in domain administrator account.\n",
                        ),
                        encoding="utf-8",
                    )
                member.unlink()
                member.symlink_to(outside)
                before = {
                    path: path.read_bytes()
                    for path in (outside, pack / "associated-artifacts.json")
                    if not path.is_symlink()
                }

                with self.assertRaises(ValueError):
                    tool.refresh(pack)

                for path, data in before.items():
                    self.assertEqual(path.read_bytes(), data)

    def test_refresh_does_not_invent_a_subject_the_sdl_lost(self) -> None:
        text = self.sdl.read_text(encoding="utf-8")
        self.sdl.write_text(
            text.replace("route_id: debug\n", "route_id: diagnostics\n"),
            encoding="utf-8",
        )

        tool.refresh(self.pack)

        self.assertEqual(
            self._binding_errors(),
            ["sdl.bindings-unresolved: sdl/techvault.bindings.json"],
        )


if __name__ == "__main__":
    unittest.main()
