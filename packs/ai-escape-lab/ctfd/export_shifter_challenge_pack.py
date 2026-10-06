#!/usr/bin/env python3
"""Render AI Escape Lab content for Shifter's CTFd-compatible importer."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml


PACK_ROOT = Path(__file__).resolve().parents[1]
FLAG_ID = re.compile(r"^flag-[1-7]$")
DIFFICULTIES = {"easy", "medium", "hard", "insane"}


class ChallengePackError(ValueError):
    """Raised when the canonical challenge sources cannot be projected."""


def _load(relative: str) -> dict[str, Any]:
    value = yaml.safe_load((PACK_ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ChallengePackError("challenge source is not a mapping")
    return value


def _index(rows: object, *, source: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ChallengePackError(f"{source} must be a non-empty list")
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ChallengePackError(f"{source} rows must be mappings")
        flag_id = row.get("flag_id")
        if not isinstance(flag_id, str) or FLAG_ID.fullmatch(flag_id) is None or flag_id in result:
            raise ChallengePackError(f"{source} has a duplicate or malformed flag id")
        result[flag_id] = row
    return result


def build_import_pack() -> dict[str, Any]:
    """Return the closed document accepted by Shifter's challenge importer."""

    placements = _index(_load("flags/placement.yaml").get("flags"), source="placement")
    challenges = _index(_load("challenges/challenges.yaml").get("challenges"), source="challenge")
    expected = [f"flag-{number}" for number in range(1, 8)]
    if set(placements) != set(expected) or set(challenges) != set(expected):
        raise ChallengePackError("the seven-flag inventory is incomplete")

    rows: list[dict[str, Any]] = []
    for flag_id in expected:
        placement = placements[flag_id]
        challenge = challenges[flag_id]
        flag = placement.get("value")
        difficulty = challenge.get("difficulty")
        hints = challenge.get("hints")
        if placement.get("source") != "value" or not isinstance(flag, str) or not flag.startswith("FLAG-"):
            raise ChallengePackError(f"{flag_id} does not carry one static flag")
        if difficulty not in DIFFICULTIES or not isinstance(hints, list) or not all(isinstance(x, str) for x in hints):
            raise ChallengePackError(f"{flag_id} challenge metadata is invalid")
        rows.append(
            {
                "name": challenge["title"],
                "description": challenge["question"],
                "category": "AI Escape Lab",
                "value": challenge["points"],
                "type": "standard",
                "state": "visible",
                "flags": [{"type": "static", "content": flag}],
                "hints": [
                    {"title": f"Hint {index}", "content": content, "cost": 0}
                    for index, content in enumerate(hints, start=1)
                ],
                "tags": [f"difficulty:{difficulty}"],
            }
        )
    return {"format": "ctfd", "challenges": rows}


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write answer-bearing content with owner-only permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the private AI Escape Lab challenge pack.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build_import_pack()
    write_private_json(args.output, payload)
    print(f"wrote {len(payload['challenges'])} challenges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
