#!/usr/bin/env python3
"""Scenario-pack identity through RAES associated-artifact manifests.

The portable parent/reference/checksum/set model and canonicalization belong to
RAES (ADR-077).  This module supplies only the environment-pack side of that
boundary: pack-local locator resolution, descriptor-anchored materialization,
exact inventory coverage, SDL-parent selection, and small compute/verify
conveniences for consumers.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, cast
from urllib.parse import quote, unquote_to_bytes, urlsplit

import yaml
from raes_contracts.associated_artifacts import (
    AssociatedArtifactValidationLimits,
    associated_artifact_set_digest,
    load_associated_artifact_manifest_json,
    validate_associated_artifact_manifest,
)
from raes_contracts.contracts import AssociatedArtifactManifestModel
from raes_contracts.diagnostics import Diagnostic
from raes import SDLError, parse_sdl_file

from . import _pack_fs

_MANIFEST_POINTER = "associated_artifact_manifest"
_PACK_MANIFEST = "pack.yaml"
_PACK_URI_SCHEME = "raes-environment-pack"
_CANONICAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CACHE_PREFIX = ("sdl", ".raes", "module-cache")
_READ_CHUNK = 64 * 1024
_MAX_PACK_YAML_BYTES = 1024 * 1024
_MAX_MANIFEST_BYTES = 8 * 1024 * 1024
_MAX_PACK_MEMBERS = 1024

_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
_BINARY = getattr(os, "O_BINARY", 0)

_PackContext = tuple[
    int,
    str,
    AssociatedArtifactManifestModel,
    tuple[str, ...],
    dict[str, str],
    tuple[object, ...],
]


class PackDigestError(ValueError):
    """The pack cannot produce or verify one conforming RAES set identity.

    Messages are deliberately bounded and payload-free.  When RAES semantic
    validation ran, its structured diagnostics remain available to callers via
    :attr:`diagnostics` without being flattened into an unbounded exception.
    """

    def __init__(self, message: str, diagnostics: tuple[Diagnostic, ...] = ()) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


def _require_descriptor_platform() -> None:
    """Fail unless the host supports descriptor-anchored, no-follow reads."""

    _pack_fs.require_descriptor_platform(
        error_type=PackDigestError, nofollow=_NOFOLLOW, directory=_DIRECTORY
    )


def _open_root(pack_root: str | os.PathLike[str]) -> tuple[str, int]:
    """Open and return one canonical pack root plus its directory descriptor."""

    return _pack_fs.open_root(
        pack_root, error_type=PackDigestError,
        nofollow=_NOFOLLOW, directory=_DIRECTORY,
    )


def _normalize_relpath(value: str) -> str:
    """Return a canonical slash-separated path relative to the pack root."""

    return _pack_fs.normalize_relpath(value, error_type=PackDigestError)


def _descriptor_flags() -> _pack_fs.DescriptorFlags:
    """Return filesystem flags while preserving digest test overrides."""

    return _pack_fs.DescriptorFlags(
        nofollow=_NOFOLLOW,
        directory=_DIRECTORY,
        nonblock=_NONBLOCK,
        binary=_BINARY,
    )


def _is_cache_path(parts: tuple[str, ...]) -> bool:
    """Return whether path components identify the excluded RAES cache tree."""

    return parts[:len(_CACHE_PREFIX)] == _CACHE_PREFIX


def _inventory(root_fd: int, excluded: str) -> tuple[str, ...]:
    """Return the bounded exact payload inventory below an opened pack root."""

    return _pack_fs.inventory(
        root_fd,
        max_members=_MAX_PACK_MEMBERS,
        excluded_paths=frozenset({excluded}),
        excluded_prefixes=(_CACHE_PREFIX,),
        error_type=PackDigestError,
        flags=_descriptor_flags(),
    )


def _open_member(root_fd: int, rel: str) -> int:
    """Open one canonical pack member through no-follow directory descriptors."""

    return _pack_fs.open_member(
        root_fd,
        rel,
        error_type=PackDigestError,
        flags=_descriptor_flags(),
    )


def _read_member_bytes(root_fd: int, rel: str, *, max_bytes: int) -> bytes:
    """Read bounded metadata bytes from one descriptor-anchored member."""

    return _pack_fs.read_member_bytes(
        root_fd,
        rel,
        max_bytes=max_bytes,
        error_type=PackDigestError,
        flags=_descriptor_flags(),
    )


class _DescriptorReader(object):
    """Lazy, no-follow reader so RAES opens only the payload being validated."""

    def __init__(self, root_fd: int, rel: str) -> None:
        self._root_fd = root_fd
        self._rel = rel
        self._fd: int | None = None
        self._done = False

    def read(self, size: int = -1) -> bytes:
        if self._done:
            return b""
        if self._fd is None:
            self._fd = _open_member(self._root_fd, self._rel)
        read_size = _READ_CHUNK if size is None or size < 0 else size
        try:
            chunk = os.read(self._fd, read_size)
        except OSError as exc:
            self.close()
            raise OSError("pack payload read failed") from exc
        if not chunk:
            self.close()
            self._done = True
        return chunk

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


def _pack_uri_to_rel(uri: str, excluded: str) -> str:
    """Resolve one canonical pack URI to a safe root-relative payload path."""

    parsed = urlsplit(uri)
    if (
        parsed.scheme != _PACK_URI_SCHEME
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise PackDigestError("associated artifact URI is not a canonical pack locator")
    try:
        rel = unquote_to_bytes(parsed.path[1:]).decode("utf-8", errors="strict")
    except ValueError as exc:
        raise PackDigestError("associated artifact URI is not valid UTF-8") from exc
    rel = _normalize_relpath(rel)
    canonical = f"{_PACK_URI_SCHEME}:/{quote(rel, safe='/-._~')}"
    if uri != canonical or rel == excluded or _is_cache_path(tuple(rel.split("/"))):
        raise PackDigestError("associated artifact URI is not a canonical pack locator")
    return rel


def _load_pack_metadata(root_fd: int) -> tuple[str, str, str]:
    """Load the pack identity and associated-artifact manifest pointer."""

    try:
        payload = yaml.safe_load(
            _read_member_bytes(root_fd, _PACK_MANIFEST, max_bytes=_MAX_PACK_YAML_BYTES).decode("utf-8")
        )
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise PackDigestError("pack.yaml is not valid UTF-8 YAML") from exc
    if not isinstance(payload, dict):
        raise PackDigestError("pack.yaml is not a mapping")
    name = payload.get("name")
    version = payload.get("version")
    pointer = payload.get(_MANIFEST_POINTER)
    if not isinstance(name, str) or not name or not isinstance(pointer, str):
        raise PackDigestError("pack identity or associated-artifact manifest pointer is missing")
    if not isinstance(version, (str, int, float)):
        raise PackDigestError("pack version is missing")
    return name, str(version), _normalize_relpath(pointer)


def _load_manifest(root_fd: int, manifest_rel: str) -> AssociatedArtifactManifestModel:
    """Load a bounded manifest through RAES's strict JSON parser."""

    try:
        return load_associated_artifact_manifest_json(
            _read_member_bytes(root_fd, manifest_rel, max_bytes=_MAX_MANIFEST_BYTES)
        )
    except PackDigestError:
        raise
    except (ValueError, TypeError) as exc:
        raise PackDigestError("associated artifact manifest is structurally invalid") from exc


def _validate_pack_manifest_identity(
    manifest: AssociatedArtifactManifestModel, name: str, version: str
) -> None:
    """Require the scenario-scoped manifest identity to match its pack."""

    if (
        manifest.scope != "scenario"
        or manifest.parent_ref.ref_id != name
        or manifest.manifest_id != f"{name}-associated-artifacts"
        or manifest.manifest_version != version
    ):
        raise PackDigestError("associated artifact manifest does not match pack identity")


def _artifact_paths(manifest: AssociatedArtifactManifestModel, excluded: str) -> dict[str, str]:
    """Map opaque artifact ids to validated pack-relative payload paths."""

    paths: dict[str, str] = {}
    for artifact_id, artifact in manifest.artifacts.items():
        if artifact.checksum.algorithm != "sha256":
            raise PackDigestError("environment-pack artifacts must use sha256 checksums")
        paths[artifact_id] = _pack_uri_to_rel(artifact.uri, excluded)
    return paths


def _parse_parent_candidates(root: str, inventory: tuple[str, ...]) -> tuple[object, ...]:
    """Parse every direct SDL document that may satisfy the manifest parent."""

    sdl_docs = [
        rel
        for rel in inventory
        if rel.startswith("sdl/") and rel.count("/") == 1 and rel.endswith(".sdl.yaml")
    ]
    if not sdl_docs:
        raise PackDigestError("pack has no direct SDL parent document")
    candidates: list[object] = []
    for rel in sdl_docs:
        try:
            candidates.append(parse_sdl_file(Path(root, *rel.split("/"))))
        except (SDLError, OSError) as exc:
            raise PackDigestError("pack SDL parent is invalid") from exc
    return tuple(candidates)


def _reader_map(root_fd: int, paths: Mapping[str, str]) -> dict[str, _DescriptorReader]:
    """Build lazy descriptor readers keyed by opaque manifest artifact id."""

    return {artifact_id: _DescriptorReader(root_fd, rel) for artifact_id, rel in paths.items()}


def _validate_with_parent_candidates(
    manifest: AssociatedArtifactManifestModel,
    candidates: tuple[object, ...],
    root_fd: int,
    paths: Mapping[str, str],
    limits: AssociatedArtifactValidationLimits | None,
) -> None:
    """Validate bytes against each candidate, retaining RAES's best diagnostics."""

    best: tuple[Diagnostic, ...] = ()
    for parent in candidates:
        readers = _reader_map(root_fd, paths)
        try:
            diagnostics = validate_associated_artifact_manifest(
                manifest,
                parent=parent,
                artifact_readers=cast(Mapping[str, BinaryIO], readers),
                limits=limits,
            )
        finally:
            for reader in readers.values():
                reader.close()
        if not diagnostics:
            return
        if not best or sum(item.code == "associated-artifact.parent-mismatch" for item in diagnostics) < sum(
            item.code == "associated-artifact.parent-mismatch" for item in best
        ):
            best = diagnostics
    raise PackDigestError("associated artifact manifest failed RAES byte binding", best)


@contextmanager
def _pack_context(pack_root: str | os.PathLike[str]) -> Iterator[_PackContext]:
    """Open and validate pack-owned projection data for one identity operation."""

    root, root_fd = _open_root(pack_root)
    try:
        name, version, manifest_rel = _load_pack_metadata(root_fd)
        manifest = _load_manifest(root_fd, manifest_rel)
        _validate_pack_manifest_identity(manifest, name, version)
        inventory = _inventory(root_fd, manifest_rel)
        paths = _artifact_paths(manifest, manifest_rel)
        if set(paths.values()) != set(inventory):
            raise PackDigestError("associated artifact manifest does not cover the exact pack inventory")
        candidates = _parse_parent_candidates(root, inventory)
        yield root_fd, manifest_rel, manifest, inventory, paths, candidates
    finally:
        os.close(root_fd)


def _derived_manifest(
    manifest: AssociatedArtifactManifestModel,
    root_fd: int,
    paths: Mapping[str, str],
    limits: AssociatedArtifactValidationLimits | None,
) -> AssociatedArtifactManifestModel:
    """Recompute payload checksums, sizes, and RAES set identity from bytes."""

    active_limits = limits or AssociatedArtifactValidationLimits()
    if len(manifest.artifacts) > active_limits.max_artifacts:
        raise PackDigestError("artifact count exceeds the derivation limit")
    artifacts = {}
    total_size = 0
    for artifact_id, artifact in manifest.artifacts.items():
        fd = _open_member(root_fd, paths[artifact_id])
        digest_value = hashlib.sha256()
        size = 0
        try:
            while chunk := os.read(fd, _READ_CHUNK):
                digest_value.update(chunk)
                size += len(chunk)
                total_size += len(chunk)
                if size > active_limits.max_artifact_bytes or total_size > active_limits.max_total_bytes:
                    raise PackDigestError("artifact bytes exceed the derivation limits")
        except OSError as exc:
            raise PackDigestError("pack member could not be read") from exc
        finally:
            os.close(fd)
        checksum = artifact.checksum.model_copy(update={"value": digest_value.hexdigest()})
        artifacts[artifact_id] = artifact.model_copy(update={"checksum": checksum, "size_bytes": size})
    derived = manifest.model_copy(update={"artifacts": artifacts, "set_digest": "sha256:" + "0" * 64})
    return derived.model_copy(update={"set_digest": associated_artifact_set_digest(derived)})


def derive_pack_content_manifest(
    pack_root: str | os.PathLike[str],
    *,
    limits: AssociatedArtifactValidationLimits | None = None,
) -> AssociatedArtifactManifestModel:
    """Derive a fully byte-bound RAES manifest from one immutably staged pack.

    Descriptor metadata and pack-local locators come from the declared manifest;
    checksum values, sizes, and the set digest are recomputed from current bytes.
    The returned model is suitable for authoring/release tooling to persist.
    """

    with _pack_context(pack_root) as (root_fd, excluded, manifest, inventory, paths, candidates):
        derived = _derived_manifest(manifest, root_fd, paths, limits)
        _validate_with_parent_candidates(derived, candidates, root_fd, paths, limits)
        if _inventory(root_fd, excluded) != inventory:
            raise PackDigestError("pack file set changed during identity derivation")
        return derived


def validate_pack_content_manifest(
    pack_root: str | os.PathLike[str],
    *,
    limits: AssociatedArtifactValidationLimits | None = None,
) -> AssociatedArtifactManifestModel:
    """Return the declared manifest after full RAES parent/set/byte validation."""

    with _pack_context(pack_root) as (root_fd, excluded, manifest, inventory, paths, candidates):
        _validate_with_parent_candidates(manifest, candidates, root_fd, paths, limits)
        if _inventory(root_fd, excluded) != inventory:
            raise PackDigestError("pack file set changed during manifest validation")
        return manifest


def pack_content_digest(pack_root: str | os.PathLike[str]) -> str:
    """Return the validated RAES associated-artifact set digest for a pack."""

    return validate_pack_content_manifest(pack_root).set_digest


def verify_pack_content_digest(pack_root: str | os.PathLike[str], expected_digest: str) -> bool:
    """Return whether current validated pack bytes have ``expected_digest``."""

    if not isinstance(expected_digest, str) or _CANONICAL_DIGEST_RE.fullmatch(expected_digest) is None:
        raise PackDigestError("expected digest is not canonical sha256")
    return hmac.compare_digest(pack_content_digest(pack_root), expected_digest)


__all__ = [
    "PackDigestError",
    "derive_pack_content_manifest",
    "pack_content_digest",
    "validate_pack_content_manifest",
    "verify_pack_content_digest",
]
