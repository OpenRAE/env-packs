"""Rebind a pack's SDL byte digest in associated-artifacts.json after editing it.

Editing ``sdl/<pack>.sdl.yaml`` changes its bytes, so the associated-artifact
manifest's SHA-256 binding of that file and the manifest ``set_digest`` must be
recomputed or the pack fails byte-binding validation.

A semantic SDL edit also changes the digest every external concept binding in
``sdl/<pack>.bindings.json`` pins its subject to. Each binding whose subject
coordinate still exists in the edited SDL is retargeted to the new digest; a
binding whose subject is gone is left untouched, so validation still reports it.

Every read and write is anchored to the pack root descriptor and refuses
symlinks, so a pack cannot redirect the rewrite outside itself. Usage:

    python tools/refresh_pack_sdl_binding.py packs/techvault
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path

from raes import parse_sdl
from raes.external_concept_subjects import external_concept_subjects

from raes_env_packs import _pack_fs
from raes_env_packs.digest import (
    associated_artifact_set_digest,
    load_associated_artifact_manifest_json,
)

_MANIFEST = "associated-artifacts.json"
_MAX_MEMBER_BYTES = 16 * 1024 * 1024
_MAX_MEMBERS = 100_000


def _read(root_fd: int, rel: str) -> bytes:
    return _pack_fs.read_member_bytes(root_fd, rel, max_bytes=_MAX_MEMBER_BYTES)


def _replace(root_fd: int, rel: str, data: bytes) -> None:
    """Atomically replace one existing regular member without following links."""

    directory, _, name = _pack_fs.normalize_relpath(rel).rpartition("/")
    dir_fd = os.dup(root_fd)
    try:
        for part in filter(None, directory.split("/")):
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)
            os.close(dir_fd)
            dir_fd = next_fd
        if not stat.S_ISREG(os.stat(name, dir_fd=dir_fd, follow_symlinks=False).st_mode):
            raise _pack_fs.PackFilesystemError("pack member is not a regular file")
        staged = f".{name}.refresh"
        fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=dir_fd)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(staged, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        except BaseException:
            os.unlink(staged, dir_fd=dir_fd)
            raise
    finally:
        os.close(dir_fd)


def _retarget_bindings(root_fd: int, rel: str, sdl_text: str) -> bytes:
    document = json.loads(_read(root_fd, rel))
    current = {
        (
            subject.subject_kind,
            subject.owning_contract_id,
            subject.lifecycle_phase.value,
            subject.canonical_ref,
        ): subject.artifact_digest
        for subject in external_concept_subjects(parse_sdl(sdl_text))
    }
    for binding in document["bindings"].values():
        subject = binding["subject"]
        coordinate = (
            subject["subject_kind"],
            subject["owning_contract_id"],
            subject["lifecycle_phase"],
            subject["canonical_ref"],
        )
        if coordinate in current:
            subject["artifact_digest"] = current[coordinate]
    return (json.dumps(document, indent=2) + "\n").encode("utf-8")


def refresh(pack_root: Path) -> str:
    _real, root_fd = _pack_fs.open_root(pack_root)
    try:
        inventory = frozenset(_pack_fs.inventory(root_fd, max_members=_MAX_MEMBERS))
        (sdl_rel,) = [
            rel for rel in inventory if rel.startswith("sdl/") and rel.count("/") == 1 and rel.endswith(".sdl.yaml")
        ]
        sdl_bytes = _read(root_fd, sdl_rel)
        bound = {sdl_rel: sdl_bytes}
        bindings_rel = sdl_rel.removesuffix(".sdl.yaml") + ".bindings.json"
        if bindings_rel in inventory:
            bound[bindings_rel] = _retarget_bindings(root_fd, bindings_rel, sdl_bytes.decode("utf-8"))
        manifest = json.loads(_read(root_fd, _MANIFEST))
        for rel, data in bound.items():
            for artifact in manifest["artifacts"].values():
                if artifact.get("uri") == f"raes-environment-pack:/{rel}":
                    artifact["checksum"]["value"] = hashlib.sha256(data).hexdigest()
                    artifact["size_bytes"] = len(data)
        model = load_associated_artifact_manifest_json(json.dumps(manifest))
        manifest["set_digest"] = associated_artifact_set_digest(model)
        if bindings_rel in bound:
            _replace(root_fd, bindings_rel, bound[bindings_rel])
        _replace(root_fd, _MANIFEST, (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        return manifest["set_digest"]
    finally:
        os.close(root_fd)


if __name__ == "__main__":
    print(refresh(Path(sys.argv[1])))
