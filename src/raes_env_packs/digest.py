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
import io
import os
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
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
from raes_contracts.contracts import (
    AssociatedArtifactManifestModel,
    ExperimentArtifactRefModel,
)
from raes_contracts.diagnostics import Diagnostic
from raes import SDLError, parse_sdl, parse_sdl_file
from raes.artifact_requirements import ArtifactIdentity

from . import _pack_fs
from .validation import PackValidationLimits

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


def _inventory(root_fd: int, excluded: str, *, max_members: int | None = None) -> tuple[str, ...]:
    """Return the bounded exact payload inventory below an opened pack root."""

    return _pack_fs.inventory(
        root_fd,
        max_members=_MAX_PACK_MEMBERS if max_members is None else max_members,
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


def _load_pack_metadata(root_fd: int, *, max_bytes: int | None = None) -> tuple[str, str, str]:
    """Load the pack identity and associated-artifact manifest pointer."""

    try:
        payload = yaml.safe_load(
            _read_member_bytes(
                root_fd,
                _PACK_MANIFEST,
                max_bytes=_MAX_PACK_YAML_BYTES if max_bytes is None else max_bytes,
            ).decode("utf-8")
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


def _load_manifest(
    root_fd: int, manifest_rel: str, *, max_bytes: int | None = None
) -> AssociatedArtifactManifestModel:
    """Load a bounded manifest through RAES's strict JSON parser."""

    try:
        return load_associated_artifact_manifest_json(
            _read_member_bytes(
                root_fd,
                manifest_rel,
                max_bytes=_MAX_MANIFEST_BYTES if max_bytes is None else max_bytes,
            )
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
def _pack_context(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
    defer_parents: bool = False,
) -> Iterator[_PackContext]:
    """Open and validate pack-owned projection data for one identity operation.

    When ``limits`` is ``None`` (the authoring callers) the historical module
    constants govern pack metadata, member count, and SDL bounds unchanged; a
    supplied ``PackValidationLimits`` overrides them for the consumer boundary.
    ``defer_parents`` yields ``candidates=None`` and leaves direct-SDL-parent
    parsing to the caller — the consumer boundary defers it so the selected
    payload is materialized exactly once and reused when it is itself a parent.
    """

    metadata_kwargs = {} if limits is None else {"max_bytes": limits.max_metadata_bytes}
    inventory_kwargs = {} if limits is None else {"max_members": limits.max_members}
    root, root_fd = _open_root(pack_root)
    try:
        name, version, manifest_rel = _load_pack_metadata(root_fd, **metadata_kwargs)
        manifest = _load_manifest(root_fd, manifest_rel)
        _validate_pack_manifest_identity(manifest, name, version)
        inventory = _inventory(root_fd, manifest_rel, **inventory_kwargs)
        paths = _artifact_paths(manifest, manifest_rel)
        if set(paths.values()) != set(inventory):
            raise PackDigestError("associated artifact manifest does not cover the exact pack inventory")
        candidates = None if defer_parents else _parse_parent_candidates(root, inventory)
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


# --- Public consumer artifact resolver (issue #208, ADR 0033) ---

# Upstream binding-presence codes are emitted when a manifest artifact has no
# supplied reader. Parent selection runs with no readers on purpose, so these
# are the expected, filtered-out noise for that pass.
_PRESENCE_CODES = frozenset(
    {
        "associated-artifact.payload-binding-missing",
        "associated-artifact.payload-binding-unexpected",
    }
)


@dataclass(frozen=True)
class ResolvedPackArtifact(object):
    """One resolved pack artifact: verified immutable bytes plus RAES identity.

    ``identity`` is the canonical upstream ``ArtifactIdentity``; ``data`` is the
    artifact's payload, already byte-bound against the validated manifest, so its
    ``sha256:`` identity digest is provably the identity of these exact bytes.
    """

    identity: ArtifactIdentity
    data: bytes


def _consumer_parent_candidates(
    root_fd: int,
    inventory: tuple[str, ...],
    limits: PackValidationLimits,
    *,
    selected_rel: str | None = None,
    selected_bytes: bytes | None = None,
) -> tuple[object, ...]:
    """Parse direct SDL parents from bounded descriptor bytes, imports denied.

    The consumer boundary reads each ``sdl/*.sdl.yaml`` through the descriptor-
    anchored, size-bounded member reader and parses it with the public RAES
    ``parse_sdl`` (which denies file-backed imports), never the pathname-based
    author parser. When the selected artifact is itself a parent document, its
    already-materialized bytes are reused so the selected payload is opened
    exactly once (ADR 0033).
    """

    sdl_docs = [
        rel
        for rel in inventory
        if rel.startswith("sdl/") and rel.count("/") == 1 and rel.endswith(".sdl.yaml")
    ]
    if not sdl_docs:
        raise PackDigestError("pack has no direct SDL parent document")
    candidates: list[object] = []
    for rel in sdl_docs:
        if rel == selected_rel and selected_bytes is not None:
            raw = selected_bytes
        else:
            raw = _read_member_bytes(root_fd, rel, max_bytes=limits.max_sdl_bytes)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PackDigestError("pack SDL parent is not valid UTF-8") from exc
        try:
            candidates.append(parse_sdl(text, limits=limits.sdl))
        except SDLError as exc:
            raise PackDigestError("pack SDL parent is invalid") from exc
    return tuple(candidates)


def _resolve_selector(
    manifest: AssociatedArtifactManifestModel, artifact: object
) -> tuple[str, ExperimentArtifactRefModel]:
    """Resolve an opaque id or descriptor to one manifest-bound artifact entry.

    A supplied descriptor must equal the manifest entry its id selects; it is not
    an alternative source of URI, size, checksum, or media-type claims.
    """

    if isinstance(artifact, ExperimentArtifactRefModel):
        artifact_id = artifact.artifact_id
    elif isinstance(artifact, str):
        artifact_id = artifact
    else:
        raise PackDigestError("artifact selector must be an id or associated-artifact descriptor")
    descriptor = manifest.artifacts.get(artifact_id)
    if descriptor is None:
        raise PackDigestError("artifact id is not declared in the pack manifest")
    if isinstance(artifact, ExperimentArtifactRefModel) and artifact != descriptor:
        raise PackDigestError("supplied descriptor does not match the pack manifest entry")
    return artifact_id, descriptor


def _select_single_parent(
    manifest: AssociatedArtifactManifestModel,
    candidates: tuple[object, ...],
    limits: AssociatedArtifactValidationLimits | None,
) -> object:
    """Select the one parent RAES identity-binds, reading no payload bytes.

    Runs the upstream validator's parent/set verdict with an empty reader map
    and ignores the expected binding-presence noise. Exactly one match is
    required; no match or an ambiguous match fails closed, preserving RAES's best
    structured diagnostics.
    """

    matched: list[object] = []
    best: tuple[Diagnostic, ...] | None = None
    for parent in candidates:
        diagnostics = validate_associated_artifact_manifest(
            manifest, parent=parent, artifact_readers={}, limits=limits
        )
        residual = tuple(item for item in diagnostics if item.code not in _PRESENCE_CODES)
        if not residual:
            matched.append(parent)
        elif best is None or len(residual) < len(best):
            best = residual
    if len(matched) == 1:
        return matched[0]
    if not matched:
        raise PackDigestError("associated artifact set has no matching pack parent", best or ())
    raise PackDigestError("associated artifact set has more than one matching pack parent")


def _materialize_member(root_fd: int, rel: str, *, max_bytes: int) -> bytes:
    """Copy one descriptor-anchored member into bounded immutable bytes."""

    fd = _open_member(root_fd, rel)
    chunks: list[bytes] = []
    total = 0
    try:
        while chunk := os.read(fd, min(_READ_CHUNK, max_bytes + 1 - total)):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise PackDigestError("artifact bytes exceed the resolver limit")
    except OSError as exc:
        raise PackDigestError("pack member could not be read") from exc
    finally:
        os.close(fd)
    return b"".join(chunks)


def _bind_artifact_set(
    root_fd: int,
    manifest: AssociatedArtifactManifestModel,
    paths: Mapping[str, str],
    parent: object,
    artifact_id: str,
    data: bytes,
    limits: AssociatedArtifactValidationLimits | None,
) -> None:
    """Run one full byte-binding pass for the selected parent.

    The already-materialized selected bytes are byte-bound through an in-memory
    reader while siblings use the existing lazy descriptor readers, so the whole
    set is validated in one pass without reopening the selected payload.
    """

    readers: dict[str, object] = {}
    for aid, rel in paths.items():
        readers[aid] = io.BytesIO(data) if aid == artifact_id else _DescriptorReader(root_fd, rel)
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
    if diagnostics:
        raise PackDigestError("associated artifact manifest failed RAES byte binding", diagnostics)


def _project_artifact_identity(
    descriptor: ExperimentArtifactRefModel, pack_version: str
) -> ArtifactIdentity:
    """Project one byte-bound descriptor + pack version into the RAES identity.

    env-packs owns this projection so consumers never choose the version rule
    locally. The identity is constructed through the pinned upstream model; a
    descriptor that cannot construct a canonical identity fails closed.
    """

    try:
        return ArtifactIdentity(
            artifact_id=descriptor.artifact_id,
            version=pack_version,
            media_type=descriptor.media_type,
            digest=f"sha256:{descriptor.checksum.value}",
        )
    # pydantic ValidationError is a ValueError
    except ValueError as exc:
        raise PackDigestError("resolved artifact identity is not canonical") from exc


def resolve_pack_artifact(
    pack_root: str | os.PathLike[str],
    artifact: str | ExperimentArtifactRefModel,
    *,
    limits: PackValidationLimits | None = None,
    artifact_limits: AssociatedArtifactValidationLimits | None = None,
) -> ResolvedPackArtifact:
    """Resolve one associated-artifact id to verified bytes and canonical identity.

    ``artifact`` is an opaque associated-artifact id or the upstream
    ``ExperimentArtifactRefModel`` descriptor; a supplied descriptor must equal
    the manifest entry its id selects and cannot override any of its claims. The
    pack root must already be immutably staged and validated by the caller
    (``validate_pack`` / ``validate_pack_content_manifest``); this is the
    post-validation byte-open step, not a replacement for it.

    One pack root descriptor is opened; the selected regular file is opened
    exactly once within that lifetime, copied into immutable ``bytes``, and
    byte-bound against the validated manifest, so the returned identity's
    ``sha256:`` digest is provably the identity of the returned bytes. No
    network, ambient path, or subprocess is used and the library does not log;
    failures raise :class:`PackDigestError` with bounded, payload-free
    diagnostics.

    ``limits`` bounds pack metadata, member count, and SDL parsing;
    ``artifact_limits`` bounds artifact count and the selected/total byte
    budgets. The two policy domains stay distinct (ADR 0033).
    """

    active_limits = limits or PackValidationLimits()
    artifact_active = artifact_limits or AssociatedArtifactValidationLimits()
    with _pack_context(pack_root, limits=active_limits, defer_parents=True) as (
        root_fd,
        manifest_rel,
        manifest,
        inventory,
        paths,
        _candidates,
    ):
        artifact_id, descriptor = _resolve_selector(manifest, artifact)
        # Open the selected payload exactly once; its bytes are reused for parent
        # parsing (when the selection is itself a parent), byte binding, and the
        # returned result.
        if descriptor.size_bytes > artifact_active.max_artifact_bytes:
            raise PackDigestError("artifact size exceeds the resolver limit")
        selected_rel = paths[artifact_id]
        data = _materialize_member(root_fd, selected_rel, max_bytes=artifact_active.max_artifact_bytes)
        candidates = _consumer_parent_candidates(
            root_fd,
            inventory,
            active_limits,
            selected_rel=selected_rel,
            selected_bytes=data,
        )
        parent = _select_single_parent(manifest, candidates, artifact_limits)
        _bind_artifact_set(root_fd, manifest, paths, parent, artifact_id, data, artifact_limits)
        if _inventory(root_fd, manifest_rel, max_members=active_limits.max_members) != inventory:
            raise PackDigestError("pack file set changed during artifact resolution")
        # pack.yaml.version is validated equal to manifest_version, so the
        # manifest version is the authoritative pack version for the identity.
        identity = _project_artifact_identity(descriptor, manifest.manifest_version)
        return ResolvedPackArtifact(identity=identity, data=data)


__all__ = [
    "PackDigestError",
    "ResolvedPackArtifact",
    "derive_pack_content_manifest",
    "pack_content_digest",
    "resolve_pack_artifact",
    "validate_pack_content_manifest",
    "verify_pack_content_digest",
]
