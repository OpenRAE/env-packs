"""Rebind a pack's SDL byte digest in associated-artifacts.json after editing it.

Editing ``sdl/<pack>.sdl.yaml`` changes its bytes, so the associated-artifact
manifest's SHA-256 binding of that file and the manifest ``set_digest`` must be
recomputed or the pack fails byte-binding validation. Usage:

    python tools/refresh_pack_sdl_binding.py packs/techvault
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from raes_env_packs.digest import (
    associated_artifact_set_digest,
    load_associated_artifact_manifest_json,
)


def refresh(pack_root: Path) -> str:
    sdl = next((pack_root / "sdl").glob("*.sdl.yaml"))
    manifest_path = pack_root / "associated-artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sdl_bytes = sdl.read_bytes()
    uri_suffix = f"/sdl/{sdl.name}"
    for artifact in manifest["artifacts"].values():
        if str(artifact.get("uri", "")).endswith(uri_suffix):
            artifact["checksum"]["value"] = hashlib.sha256(sdl_bytes).hexdigest()
            artifact["size_bytes"] = len(sdl_bytes)
    model = load_associated_artifact_manifest_json(json.dumps(manifest))
    manifest["set_digest"] = associated_artifact_set_digest(model)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest["set_digest"]


if __name__ == "__main__":
    print(refresh(Path(sys.argv[1])))
