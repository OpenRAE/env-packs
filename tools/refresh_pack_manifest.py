"""Rebind a pack's associated-artifacts.json after editing any tracked content.

Editing any byte-bound pack file (the SDL, a script, the README, ...) changes
its bytes, so that artifact's checksum/size in the associated-artifact
manifest and the manifest ``set_digest`` must be recomputed or the pack fails
byte-binding validation. Usage:

    python tools/refresh_pack_manifest.py packs/techvault
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from raes_env_packs.digest import derive_pack_content_manifest


def refresh(pack_root: Path) -> str:
    manifest_path = pack_root / "associated-artifacts.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    derived = derive_pack_content_manifest(pack_root)
    for artifact_id, descriptor in derived.artifacts.items():
        manifest["artifacts"][artifact_id]["checksum"]["value"] = descriptor.checksum.value
        manifest["artifacts"][artifact_id]["size_bytes"] = descriptor.size_bytes
    manifest["set_digest"] = derived.set_digest
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest["set_digest"]


if __name__ == "__main__":
    print(refresh(Path(sys.argv[1])))
