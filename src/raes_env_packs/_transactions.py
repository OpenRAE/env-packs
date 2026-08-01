"""Linux atomic directory primitives shared by pack authoring workflows."""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path

from . import _pack_fs

_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAME_EXCHANGE = 2


class TransactionError(ValueError):
    """A staged tree could not be committed with the required guarantees."""


class TargetExistsError(TransactionError):
    """A no-replace transaction found an occupied target."""


def write_member(root: Path, rel: str, content: bytes | str) -> None:
    """Write one canonical member below a fresh private staging root."""

    _pack_fs.normalize_relpath(rel, error_type=TransactionError)
    destination = root.joinpath(*rel.split("/"))
    resolved_root = root.resolve(strict=True)
    resolved = destination.resolve(strict=False)
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise TransactionError("staged member escapes the transaction root")
    current = root
    for part in rel.split("/")[:-1]:
        current = current / part
        current.mkdir(mode=0o755, exist_ok=True)
        current.chmod(0o755)
    payload = content if isinstance(content, bytes) else content.encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(destination, flags, 0o600)
        try:
            os.fchmod(descriptor, 0o644)
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(payload)
                stream.flush()
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise TransactionError("staged member could not be written safely") from exc


def _renameat2(src: str, dst: str, flag: int) -> None:
    """Invoke renameat2 with one explicit atomicity flag."""

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise TransactionError("atomic directory transactions are unsupported")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    ctypes.set_errno(0)
    if renameat2(
        _AT_FDCWD,
        os.fsencode(src),
        _AT_FDCWD,
        os.fsencode(dst),
        flag,
    ) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))


def publish_noreplace(staged: Path, target: Path) -> None:
    """Atomically move a complete staged tree into one absent target."""

    try:
        _renameat2(str(staged), str(target), _RENAME_NOREPLACE)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise TargetExistsError("transaction target already exists") from exc
        raise TransactionError("staged tree could not be published") from exc


def exchange(staged: Path, target: Path) -> None:
    """Atomically exchange a complete staged successor and existing target."""
    try:
        _renameat2(str(staged), str(target), _RENAME_EXCHANGE)
    except OSError as exc:
        raise TransactionError("staged tree could not replace the target") from exc


__all__ = [
    "TransactionError",
    "TargetExistsError",
    "exchange",
    "publish_noreplace",
    "write_member",
]
