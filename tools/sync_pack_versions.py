"""Write the package version into every pack and refresh its digests.

Release Please bumps ``[project].version`` in ``pyproject.toml``. Every pack
under ``packs/`` carries that version (ADR 0045) in ``pack.yaml``,
``pack.compatibility.yaml``, its associated-artifact ``manifest_version``, and
each pack-local exact-artifact reference in its SDL. Those files are
checksummed, so after the version scalars change this tool reruns
``refresh_pack_sdl_binding.refresh`` for the pack.

Version scalars are replaced in place at their YAML node positions, so every
other byte of each file is preserved. The tool is idempotent. Usage:

    python tools/sync_pack_versions.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import tomllib

import yaml

_REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from tools.refresh_pack_sdl_binding import refresh  # noqa: E402

_MANIFEST = "associated-artifacts.json"


def package_version(root: pathlib.Path = _REPOSITORY_ROOT) -> str:
    with (root / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


def _scalar(node: yaml.Node, path: tuple[str, ...]) -> yaml.ScalarNode:
    for key in path:
        if not isinstance(node, yaml.MappingNode):
            raise ValueError(f"version path {'/'.join(path)} is not a mapping")
        matches = [value for item, value in node.value if item.value == key]
        if len(matches) != 1:
            raise ValueError(f"version path {'/'.join(path)} is missing or duplicated")
        node = matches[0]
    if not isinstance(node, yaml.ScalarNode):
        raise ValueError(f"version path {'/'.join(path)} is not a scalar")
    return node


def set_yaml_scalars(text: str, paths: list[tuple[str, ...]], value: str) -> str:
    """Replace each scalar at ``paths`` with ``value``; keep every other byte."""

    document = yaml.compose(text, Loader=yaml.SafeLoader)
    nodes = sorted(
        {id(node): node for node in (_scalar(document, path) for path in paths)}.values(),
        key=lambda node: node.start_mark.index,
        reverse=True,
    )
    for node in nodes:
        quote = {"'": "'", '"': '"'}.get(node.style or "", "")
        text = (
            text[: node.start_mark.index]
            + f"{quote}{value}{quote}"
            + text[node.end_mark.index :]
        )
    return text


def _sdl_version_paths(sdl_text: str, artifact_ids: set[str]) -> list[tuple[str, ...]]:
    content = (yaml.safe_load(sdl_text) or {}).get("content") or {}
    paths: list[tuple[str, ...]] = []
    for content_id, item in content.items():
        source = item.get("source") if isinstance(item, dict) else None
        if not isinstance(source, dict):
            continue
        exact = (source.get("artifact_requirement") or {}).get("exact_artifact") or {}
        if exact.get("artifact_id") in artifact_ids:
            paths.append(("content", content_id, "source", "version"))
            paths.append(
                (
                    "content",
                    content_id,
                    "source",
                    "artifact_requirement",
                    "exact_artifact",
                    "version",
                )
            )
    return paths


def sync_pack(pack: pathlib.Path, version: str) -> bool:
    """Write ``version`` into ``pack`` and refresh its digests; return whether it changed."""

    manifest_path = pack / _MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (sdl_path,) = sorted((pack / "sdl").glob("*.sdl.yaml"))
    edits = {
        pack / "pack.yaml": [("version",)],
        pack / "pack.compatibility.yaml": [("pack", "version")],
    }
    sdl_text = sdl_path.read_text(encoding="utf-8")
    sdl_paths = _sdl_version_paths(sdl_text, set(manifest["artifacts"]))
    if sdl_paths:
        edits[sdl_path] = sdl_paths

    changed = False
    for path, paths in edits.items():
        before = path.read_text(encoding="utf-8")
        after = set_yaml_scalars(before, paths, version)
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed = True
    if manifest["manifest_version"] != version:
        manifest["manifest_version"] = version
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        changed = True
    if changed:
        refresh(pack)
    return changed


def main(root: pathlib.Path = _REPOSITORY_ROOT) -> int:
    version = package_version(root)
    for pack_yaml in sorted((root / "packs").glob("*/pack.yaml")):
        if sync_pack(pack_yaml.parent, version):
            print(f"{pack_yaml.parent.name}: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
