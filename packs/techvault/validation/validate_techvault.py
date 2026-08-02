#!/usr/bin/env python3
"""Pack-local static entrypoint used by the environment-pack content gate."""

from __future__ import annotations

import pathlib
import sys

from raes_env_packs import validate_pack, validate_pack_content_manifest


def validate() -> list[str]:
    root = pathlib.Path(__file__).resolve().parents[1]
    result = validate_pack(root)
    errors = list(result.errors)
    if not errors:
        try:
            validate_pack_content_manifest(root)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


if __name__ == "__main__":
    if sys.argv[1:] != ["validate"]:
        raise SystemExit("usage: validate_techvault.py validate")
    failures = validate()
    for failure in failures:
        print(failure)
    raise SystemExit(1 if failures else 0)
