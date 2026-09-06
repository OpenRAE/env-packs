"""Lossless, bounded review of changes; never truncates approved content."""
import hashlib
from collections.abc import Mapping


def _member(data: bytes | None) -> dict[str, object] | None:
    if data is None:
        return None
    result: dict[str, object] = {
        "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
    }
    try:
        result["text"] = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        result["binary"] = True
    return result


def changes(before: Mapping[str, bytes], after: Mapping[str, bytes]) -> list[dict[str, object]]:
    """Present exact text and binary identity for every changed member."""
    return [
        {"path": path, "before": _member(before.get(path)), "after": _member(after.get(path))}
        for path in sorted(before.keys() | after.keys())
        if before.get(path) != after.get(path)
    ]
