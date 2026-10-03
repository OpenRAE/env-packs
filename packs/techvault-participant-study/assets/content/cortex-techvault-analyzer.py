#!/usr/bin/python3
"""Offline Cortex analyzer for the fixed TechVault scenario context."""

from __future__ import annotations

import json
import pathlib
import sys


ATTACKER_IP = "172.20.1.30"
ANALYZER_ID = "TechVaultScenarioContext_1_0"


def analyze(observable: str) -> dict[str, object]:
    matched = observable == ATTACKER_IP
    verdict = "malicious" if matched else "unknown"
    level = "malicious" if matched else "info"
    value = "1" if matched else "0"
    return {
        "success": True,
        "summary": {
            "taxonomies": [
                {
                    "namespace": "TechVault",
                    "predicate": "ScenarioAttacker",
                    "value": value,
                    "level": level,
                }
            ]
        },
        "artifacts": [],
        "full": {
            "analyzer": ANALYZER_ID,
            "offline": True,
            "observable": observable,
            "scenario_role": "attacker" if matched else "unclassified",
            "verdict": verdict,
        },
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        return 64
    job_directory = pathlib.Path(argv[1])
    input_path = job_directory / "input" / "input.json"
    output_path = job_directory / "output" / "output.json"
    try:
        request = json.loads(input_path.read_text(encoding="utf-8"))
        observable = request["data"]
        if not isinstance(observable, str) or not observable:
            raise ValueError("observable must be a non-empty string")
        report = analyze(observable)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        report = {"success": False, "errorMessage": "invalid analyzer input"}
    output_path.write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return 0 if report["success"] else 65


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
