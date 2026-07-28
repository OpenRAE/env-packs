"""Descriptor-anchored reads for untrusted environment-pack directories.

This is shared internal infrastructure for validation and content identity.  It
keeps path containment anchored to an opened root descriptor instead of relying
on string normalization followed by race-prone pathname reads.
"""

from __future__ import annotations

import os
import stat
import unicodedata
from collections.abc import Iterator

_READ_CHUNK = 64 * 1024
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
_BINARY = getattr(os, "O_BINARY", 0)


class PackFilesystemError(ValueError):
    """A pack cannot be read through the safe filesystem boundary."""


class DescriptorFlags(object):
    """OS flags used for descriptor-anchored traversal and member reads."""

    __slots__ = ("nofollow", "directory", "nonblock", "binary")

    def __init__(
        self,
        nofollow: int = _NOFOLLOW,
        directory: int = _DIRECTORY,
        nonblock: int = _NONBLOCK,
        binary: int = _BINARY,
    ) -> None:
        self.nofollow = nofollow
        self.directory = directory
        self.nonblock = nonblock
        self.binary = binary


class _WalkState(object):
    """Shared policy and budget state for one recursive inventory walk."""

    __slots__ = (
        "excluded_paths",
        "excluded_prefixes",
        "seen_casefold",
        "error_type",
        "flags",
        "seen_members",
        "max_members",
    )

    def __init__(
        self,
        excluded_paths: frozenset[str],
        excluded_prefixes: tuple[tuple[str, ...], ...],
        error_type: type[ValueError],
        flags: DescriptorFlags,
        max_members: int,
    ) -> None:
        self.excluded_paths = excluded_paths
        self.excluded_prefixes = excluded_prefixes
        self.seen_casefold: dict[str, str] = {}
        self.error_type = error_type
        self.flags = flags
        self.seen_members = 0
        self.max_members = max_members


def _fail(error_type: type[ValueError], message: str, cause: BaseException | None = None) -> None:
    """Raise one caller-selected bounded filesystem exception."""

    error = error_type(message)
    if cause is None:
        raise error
    raise error from cause


def require_descriptor_platform(
    *,
    error_type: type[ValueError] = PackFilesystemError,
    nofollow: int = _NOFOLLOW,
    directory: int = _DIRECTORY,
) -> None:
    """Fail unless descriptor-relative no-follow reads are supported."""

    if (not nofollow or not directory or os.open not in os.supports_dir_fd
            or os.stat not in os.supports_dir_fd):
        _fail(error_type, "descriptor-anchored pack reads are unsupported on this platform")


def open_root(
    pack_root: str | os.PathLike[str],
    *,
    error_type: type[ValueError] = PackFilesystemError,
    nofollow: int = _NOFOLLOW,
    directory: int = _DIRECTORY,
) -> tuple[str, int]:
    """Open one canonical pack root and return its real path and descriptor."""

    require_descriptor_platform(error_type=error_type, nofollow=nofollow, directory=directory)
    root = os.fspath(pack_root)
    if not root:
        _fail(error_type, "pack root is empty")
    fd: int | None = None
    try:
        if os.path.islink(root):
            _fail(error_type, "pack root is a symlink")
        fd = os.open(root, os.O_RDONLY | directory | nofollow)
        root_stat = os.fstat(fd)
    except error_type:
        raise
    except (OSError, TypeError, ValueError) as exc:
        if fd is not None:
            os.close(fd)
        _fail(error_type, "pack root is not an accessible directory", exc)
    assert fd is not None
    if not stat.S_ISDIR(root_stat.st_mode):
        os.close(fd)
        _fail(error_type, "pack root is not a directory")
    return os.path.realpath(root), fd


def _normalize_component(name: str, error_type: type[ValueError]) -> str:
    """Return one canonical UTF-8 NFC path component."""

    normalized = unicodedata.normalize("NFC", name)
    if (name != normalized or not name or name in {".", ".."}
            or "/" in name or "\\" in name):
        _fail(error_type, "pack member name is not canonical")
    try:
        name.encode("utf-8")
    except UnicodeEncodeError as exc:
        _fail(error_type, "pack member name is not valid UTF-8", exc)
    return name


def normalize_relpath(
    value: str,
    *,
    error_type: type[ValueError] = PackFilesystemError,
) -> str:
    """Return one canonical slash-separated path relative to the pack root."""

    if not isinstance(value, str) or not value or os.path.isabs(value) or "\\" in value:
        _fail(error_type, "pack-relative path is not canonical")
    parts = value.split("/")
    normalized = "/".join(_normalize_component(part, error_type) for part in parts)
    if normalized != value:
        _fail(error_type, "pack-relative path is not canonical")
    return normalized


def _directory_names(
    directory_fd: int,
    state: _WalkState,
) -> list[str]:
    """Return sorted child names while consuming the global member budget."""

    try:
        names: list[str] = []
        with os.scandir(directory_fd) as entries:
            for entry in entries:
                state.seen_members += 1
                if state.seen_members > state.max_members:
                    _fail(
                        state.error_type,
                        "pack member count exceeds the validation limit",
                    )
                names.append(entry.name)
        return sorted(names)
    except OSError as exc:
        _fail(state.error_type, "pack directory could not be traversed", exc)


def _member_path(
    raw_name: str,
    prefix: tuple[str, ...],
    state: _WalkState,
) -> tuple[str, tuple[str, ...], str]:
    """Canonicalize and collision-check one inventory member path."""

    name = _normalize_component(raw_name, state.error_type)
    parts = (*prefix, name)
    rel = "/".join(parts)
    folded = rel.casefold()
    prior = state.seen_casefold.get(folded)
    if prior is not None and prior != rel:
        _fail(state.error_type, "pack contains a case-insensitive path collision")
    state.seen_casefold[folded] = rel
    return name, parts, rel


def _member_stat(
    directory_fd: int, name: str, error_type: type[ValueError]
) -> os.stat_result:
    """Inspect one member without following a symbolic link."""

    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError as exc:
        _fail(error_type, "pack member could not be inspected", exc)


def _walk_child_directory(
    directory_fd: int,
    name: str,
    parts: tuple[str, ...],
    state: _WalkState,
) -> Iterator[str]:
    """Yield safe regular files below one non-excluded child directory."""

    if any(
        parts[:len(excluded)] == excluded
        for excluded in state.excluded_prefixes
    ):
        return
    try:
        child_fd = os.open(
            name,
            os.O_RDONLY | state.flags.directory | state.flags.nofollow,
            dir_fd=directory_fd,
        )
    except OSError as exc:
        _fail(state.error_type, "pack directory could not be opened", exc)
    try:
        yield from _walk_directory(child_fd, parts, state)
    finally:
        os.close(child_fd)


def _walk_payload(
    member_stat: os.stat_result,
    rel: str,
    state: _WalkState,
) -> Iterator[str]:
    """Yield one safe, included regular payload."""

    if not stat.S_ISREG(member_stat.st_mode):
        _fail(state.error_type, "pack contains a non-regular file")
    if member_stat.st_nlink > 1:
        _fail(state.error_type, "pack contains a multiply-linked file")
    if rel not in state.excluded_paths:
        yield rel


def _walk_directory(
    directory_fd: int,
    prefix: tuple[str, ...],
    state: _WalkState,
) -> Iterator[str]:
    """Yield the deterministic safe inventory below one open directory."""

    for raw_name in _directory_names(directory_fd, state):
        name, parts, rel = _member_path(raw_name, prefix, state)
        member_stat = _member_stat(directory_fd, name, state.error_type)
        if stat.S_ISLNK(member_stat.st_mode):
            _fail(state.error_type, "pack contains a symlink")
        if stat.S_ISDIR(member_stat.st_mode):
            yield from _walk_child_directory(directory_fd, name, parts, state)
        else:
            yield from _walk_payload(member_stat, rel, state)


def inventory(
    root_fd: int,
    *,
    max_members: int,
    excluded_paths: frozenset[str] = frozenset(),
    excluded_prefixes: tuple[tuple[str, ...], ...] = (),
    error_type: type[ValueError] = PackFilesystemError,
    flags: DescriptorFlags | None = None,
) -> tuple[str, ...]:
    """Return a deterministic, bounded inventory of safe regular files."""

    state = _WalkState(
        excluded_paths,
        excluded_prefixes,
        error_type,
        flags or DescriptorFlags(),
        max_members,
    )
    return tuple(_walk_directory(root_fd, (), state))


def open_member(
    root_fd: int,
    rel: str,
    *,
    error_type: type[ValueError] = PackFilesystemError,
    flags: DescriptorFlags | None = None,
) -> int:
    """Open one canonical regular member through root-anchored descriptors."""

    active_flags = flags or DescriptorFlags()
    parts = normalize_relpath(rel, error_type=error_type).split("/")
    current_fd = os.dup(root_fd)
    file_fd: int | None = None
    try:
        for part in parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | active_flags.directory | active_flags.nofollow,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(
            parts[-1],
            os.O_RDONLY
            | active_flags.nofollow
            | active_flags.nonblock
            | active_flags.binary,
            dir_fd=current_fd,
        )
    except OSError as exc:
        _fail(error_type, "pack member could not be opened", exc)
    finally:
        os.close(current_fd)
    assert file_fd is not None
    try:
        member_stat = os.fstat(file_fd)
    except OSError as exc:
        os.close(file_fd)
        _fail(error_type, "pack member could not be inspected", exc)
    if not stat.S_ISREG(member_stat.st_mode) or member_stat.st_nlink > 1:
        os.close(file_fd)
        _fail(error_type, "pack member is not a singly-linked regular file")
    return file_fd


def read_member_bytes(
    root_fd: int,
    rel: str,
    *,
    max_bytes: int,
    error_type: type[ValueError] = PackFilesystemError,
    flags: DescriptorFlags | None = None,
) -> bytes:
    """Read one descriptor-anchored member up to a strict byte limit."""

    fd = open_member(
        root_fd, rel, error_type=error_type, flags=flags,
    )
    chunks: list[bytes] = []
    try:
        total = 0
        while chunk := os.read(fd, min(_READ_CHUNK, max_bytes + 1 - total)):
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                _fail(error_type, "pack metadata exceeds the validation limit")
    except OSError as exc:
        _fail(error_type, "pack member could not be read", exc)
    finally:
        os.close(fd)
    return b"".join(chunks)


__all__ = [
    "DescriptorFlags",
    "PackFilesystemError",
    "inventory",
    "normalize_relpath",
    "open_member",
    "open_root",
    "read_member_bytes",
    "require_descriptor_platform",
]
