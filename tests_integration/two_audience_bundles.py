#!/usr/bin/env python3
"""Executable two-audience delivery-bundle walkthrough for issue #379.

The walkthrough creates one synthetic pack in a temporary catalog. It exercises
authoring and release exposure only; it does not start a runtime or make an
educational-effectiveness claim.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

import yaml

from raes_env_packs.release import (
    build_release,
    bundle_participant_views,
    lint_pack,
    smoke_pack,
)

from kit_author_walkthrough import Result, _run


_PACK_ID = "two-audience-example"
_BUNDLES = ("guided", "unguided")
_SHARED = "_shared/objective.md"
_GUIDED = "guided/participant/hint.md"
_UNGUIDED = "unguided/participant/briefing.md"
_GUIDED_FACILITATOR = "guided/operator/facilitator.md"
_UNGUIDED_FACILITATOR = "unguided/operator/facilitator.md"


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_yaml(path: Path, body: object) -> None:
    _write(path, yaml.safe_dump(body, sort_keys=False))


def _pack_yaml() -> dict[str, object]:
    return {
        "name": _PACK_ID,
        "title": "Two-audience example",
        "version": "0.1.0",
        "status": "draft",
        "description": (
            "A synthetic incident-triage scenario packaged for guided and "
            "unguided participants."
        ),
        "authors": ["OpenRAE contributors"],
        "license": "Apache-2.0",
        "requirement": "OpenRAE/env-packs#379",
        "contents": {
            "flag_layer": False,
            "reference_triangle": False,
            "profile_bundles": True,
        },
        "provenance_ledger": "docs/provenance-ledger.yaml",
        "compatibility_manifest": "pack.compatibility.yaml",
        "profile_bundles": {
            "manifest": "profiles/bundles.yaml",
            "bundles": [{"id": bundle_id} for bundle_id in _BUNDLES],
        },
    }


def _compatibility() -> dict[str, object]:
    return {
        "schema_version": "environment-pack-compatibility/v2",
        "pack": {
            "name": _PACK_ID,
            "title": "Two-audience example",
            "version": "0.1.0",
            "status": "draft",
            "provenance_ledger": "docs/provenance-ledger.yaml",
            "source": {
                "requirement": "OpenRAE/env-packs#379",
                "issues": [379],
                "upstream_references": [],
            },
        },
        "artifact_boundaries": {
            "participant_visible": [
                {
                    "path": "README.md",
                    "export": "public",
                    "description": "Participant-safe example overview.",
                },
                {
                    "path": f"profiles/{_SHARED}",
                    "export": "public",
                    "description": "Objective shared by both audiences.",
                },
                {
                    "path": f"profiles/{_GUIDED}",
                    "export": "public",
                    "description": "Guided participant hint.",
                },
                {
                    "path": f"profiles/{_UNGUIDED}",
                    "export": "public",
                    "description": "Unguided participant briefing.",
                },
            ],
            "operator_only": [
                {
                    "path": f"profiles/{_GUIDED_FACILITATOR}",
                    "export": "operator",
                    "description": "Guided facilitator notes.",
                },
                {
                    "path": f"profiles/{_UNGUIDED_FACILITATOR}",
                    "export": "operator",
                    "description": "Unguided facilitator notes.",
                },
            ],
            "oracle_only": [],
            "commercial": [],
        },
        "runtime_profiles": [],
        "delivery_bundles": [
            {
                "bundle_id": "guided",
                "status": "supported",
                "audience": "guided",
                "manifest": {"path": "profiles/bundles.yaml"},
                "participant_paths": [
                    {"path": "profiles/_shared/"},
                    {"path": "profiles/guided/participant/"},
                ],
                "operator_paths": [
                    {"path": "profiles/guided/operator/"},
                ],
                "validation": [{"path": "profiles/validate_profiles.py"}],
            },
            {
                "bundle_id": "unguided",
                "status": "supported",
                "audience": "unguided",
                "manifest": {"path": "profiles/bundles.yaml"},
                "participant_paths": [
                    {"path": "profiles/_shared/"},
                    {"path": "profiles/unguided/participant/"},
                ],
                "operator_paths": [
                    {"path": "profiles/unguided/operator/"},
                ],
                "validation": [{"path": "profiles/validate_profiles.py"}],
            },
        ],
        "platform_features": [],
        "assets": [
            {
                "asset_id": "shared-objective",
                "path": f"profiles/{_SHARED}",
                "visibility": "participant",
                "status": "shipped",
            },
            {
                "asset_id": "guided-hint",
                "path": f"profiles/{_GUIDED}",
                "visibility": "participant",
                "status": "shipped",
            },
            {
                "asset_id": "unguided-briefing",
                "path": f"profiles/{_UNGUIDED}",
                "visibility": "participant",
                "status": "shipped",
            },
        ],
        "operator_surfaces": [
            {
                "surface_id": "guided-facilitator",
                "path": f"profiles/{_GUIDED_FACILITATOR}",
                "role": "facilitator",
                "visibility": "operator",
                "status": "shipped",
            },
            {
                "surface_id": "unguided-facilitator",
                "path": f"profiles/{_UNGUIDED_FACILITATOR}",
                "role": "facilitator",
                "visibility": "operator",
                "status": "shipped",
            },
        ],
        "validation": {
            "commands": [
                {
                    "id": "pack-contract",
                    "command": "raes-pack-validate --pack .",
                    "validates": ["manifest", "pack-layout", "leak-scan", "sdl"],
                },
                {
                    "id": "pack-release",
                    "command": "raes-pack-release check --pack .",
                    "validates": ["release", "delivery-bundles"],
                },
            ],
            "gates": [
                {
                    "id": "profile-contract",
                    "kind": "unit-test",
                    "paths": [{"path": "profiles/tests/test_profiles.py"}],
                }
            ],
        },
    }


def _bundles() -> dict[str, object]:
    return {
        "schema_version": "environment-pack-profile-bundles/v1",
        "bundles": [
            {
                "id": "guided",
                "audience": "participant",
                "runtime_profiles": [],
                "shared_includes": [_SHARED],
                "participant_entrypoints": [_GUIDED],
                "operator_entrypoints": [_GUIDED_FACILITATOR],
            },
            {
                "id": "unguided",
                "audience": "participant",
                "runtime_profiles": [],
                "shared_includes": [_SHARED],
                "participant_entrypoints": [_UNGUIDED],
                "operator_entrypoints": [_UNGUIDED_FACILITATOR],
            },
        ],
    }


def _provenance() -> dict[str, object]:
    return {
        "schema_version": "environment-pack-provenance/v3",
        "pack": {"name": _PACK_ID},
        "sources": [
            {
                "source_id": "original-design",
                "name": "OpenRAE synthetic two-audience example",
                "license": "Apache-2.0",
                "usage": "reused",
                "attribution_required": False,
                "used": "All scenario, participant, and facilitator material.",
            }
        ],
        "artifacts": [
            {
                "artifact_id": "scenario",
                "path": "sdl/",
                "classification": "open",
                "sources": ["original-design"],
                "description": "Wizard-generated hydrated scenario.",
            },
            {
                "artifact_id": "documentation",
                "path": "docs/",
                "classification": "open",
                "sources": ["original-design"],
                "description": "Participant-safe pack documentation.",
            },
            {
                "artifact_id": "audience-bundles",
                "path": "profiles/",
                "classification": "open",
                "sources": ["original-design"],
                "description": "Synthetic audience and facilitator material.",
            },
        ],
        "content_safety": {
            "no_real_malware": True,
            "no_real_third_party_targets": True,
            "no_real_credentials": True,
            "no_sensitive_data": True,
            "offensive_tooling_boundary": True,
            "notes": "Synthetic local authoring example only.",
        },
        "review": {
            "status": "approved",
            "gates": [
                {"gate_id": "licensing", "status": "approved"},
                {"gate_id": "attribution", "status": "approved"},
                {"gate_id": "sensitive-data", "status": "approved"},
                {"gate_id": "offensive-tooling", "status": "approved"},
            ],
        },
    }


_PROFILE_VALIDATOR = '''#!/usr/bin/env python3
"""Thin adapter over the canonical pack and release checks."""

from __future__ import annotations

import sys
from pathlib import Path

from raes_env_packs import validate_pack
from raes_env_packs.release import lint_pack, smoke_pack


ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    if argv != ["validate"]:
        print("usage: validate_profiles.py validate", file=sys.stderr)
        return 2
    failures = list(validate_pack(ROOT).errors)
    failures.extend(lint_pack(str(ROOT)))
    failures.extend(smoke_pack(str(ROOT)))
    for failure in failures:
        print(f"profile validation: {failure}", file=sys.stderr)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


_PROFILE_TEST = '''"""Pack-local checks for the authored bundle projection."""

from __future__ import annotations

import unittest
from pathlib import Path

from raes_env_packs.release import bundle_participant_views


ROOT = Path(__file__).resolve().parents[2]


class ProfileProjectionTests(unittest.TestCase):
    def test_shared_objective_and_distinct_overlays(self) -> None:
        views = bundle_participant_views(str(ROOT))
        self.assertEqual(set(views), {"guided", "unguided"})
        self.assertIn("profiles/_shared/objective.md", views["guided"])
        self.assertIn("profiles/_shared/objective.md", views["unguided"])
        self.assertNotEqual(views["guided"], views["unguided"])

    def test_operator_material_is_not_participant_exposed(self) -> None:
        exposed = {
            path
            for paths in bundle_participant_views(str(ROOT)).values()
            for path in paths
        }
        self.assertFalse(any("/operator/" in path for path in exposed))


if __name__ == "__main__":
    unittest.main()
'''


def _create_pack(result: Result, workspace: Path) -> tuple[Path, bytes]:
    author_repo = workspace / "catalog"
    (author_repo / ".git").mkdir(parents=True)
    (author_repo / "environments").mkdir()
    created = _run(
        "raes_env_packs.wizard",
        [_PACK_ID, "--route", "minimal", "--repo", str(author_repo), "--yes"],
    )
    result.command("ordinary minimal pack created", created)
    pack = author_repo / "environments" / _PACK_ID
    sdl = pack / "sdl" / f"{_PACK_ID}.sdl.yaml"
    return pack, sdl.read_bytes()


def _author_profiles(pack: Path) -> None:
    _write_yaml(pack / "pack.yaml", _pack_yaml())
    _write_yaml(pack / "pack.compatibility.yaml", _compatibility())
    _write_yaml(pack / "profiles" / "bundles.yaml", _bundles())
    _write_yaml(pack / "docs" / "provenance-ledger.yaml", _provenance())

    _write(
        pack / "README.md",
        "# Two-audience example\n\n"
        "Investigate a synthetic service interruption and report the likely "
        "cause. Audience bundles change guidance only.\n",
    )
    _write(
        pack / "docs" / "concepts.md",
        "# Concepts\n\nUse timestamps and service health observations to form a "
        "testable incident hypothesis.\n",
    )
    _write(
        pack / "docs" / "attack-path.md",
        "# Investigation path\n\nThe environment pack owns this synthetic scenario. "
        "Its wizard-generated RAES SDL remains unchanged while the delivery "
        "bundle selects participant prose.\n",
    )
    _write(
        pack / "docs" / "golden-readiness-checklist.md",
        "# Golden readiness checklist\n\n"
        "This static authoring example makes no runtime claim.\n\n"
        "## Golden Definition Of Done\n\n"
        "- [ ] Runtime realization is outside this walkthrough.\n\n"
        "## Final Manual Participant Walkthrough Protocol\n\n"
        "- [ ] No participant execution is claimed.\n",
    )
    _write(
        pack / "profiles" / _SHARED,
        "# Shared objective\n\nDetermine the likely cause of the synthetic service "
        "interruption and support the conclusion with participant-visible "
        "observations.\n",
    )
    _write(
        pack / "profiles" / _GUIDED,
        "# Guided hint\n\nStart by comparing the most recent health change with "
        "the interruption timestamp, then test one alternative explanation.\n",
    )
    _write(
        pack / "profiles" / _UNGUIDED,
        "# Unguided briefing\n\nInvestigate the interruption using the available "
        "participant observations. Report a supported conclusion.\n",
    )
    _write(
        pack / "profiles" / _GUIDED_FACILITATOR,
        "# Guided facilitator notes\n\nKeep the resolution notes on this operator "
        "surface. Offer the authored hint only after the participant records an "
        "initial hypothesis.\n",
    )
    _write(
        pack / "profiles" / _UNGUIDED_FACILITATOR,
        "# Unguided facilitator notes\n\nKeep the resolution notes on this operator "
        "surface. Do not provide progressive hints during the participant run.\n",
    )
    _write(pack / "profiles" / "validate_profiles.py", _PROFILE_VALIDATOR)
    _write(pack / "profiles" / "tests" / "test_profiles.py", _PROFILE_TEST)


def _positive_checks(result: Result, pack: Path, original_sdl: bytes, out: Path) -> None:
    current_sdl = (pack / "sdl" / f"{_PACK_ID}.sdl.yaml").read_bytes()
    result.check(
        "minimal SDL remains byte-for-byte unchanged",
        current_sdl == original_sdl,
    )

    validation = _run("raes_env_packs.content_ci", ["--pack", str(pack)])
    result.command("trusted author validation passes", validation)
    release_check = _run("raes_env_packs.release", ["check", "--pack", str(pack)])
    result.command("release lint and smoke checks pass", release_check)

    views = bundle_participant_views(str(pack))
    guided = views.get("guided", [])
    unguided = views.get("unguided", [])
    result.check(
        "both audience bundles reuse one shared participant objective",
        set(views) == set(_BUNDLES)
        and f"profiles/{_SHARED}" in guided
        and f"profiles/{_SHARED}" in unguided,
    )
    result.check(
        "guided and unguided participant content differs",
        guided != unguided
        and (pack / "profiles" / _GUIDED).read_text(encoding="utf-8")
        != (pack / "profiles" / _UNGUIDED).read_text(encoding="utf-8"),
    )
    result.check(
        "facilitator material stays operator-only",
        all("/operator/" not in path for paths in views.values() for path in paths),
    )

    metadata, failures = build_release(str(pack), str(out))
    result.check("boundary-split release builds", not failures, "; ".join(failures))
    release_root = out / f"{_PACK_ID}-0.1.0"
    participant = release_root / "participant" / "profiles"
    operator = release_root / "operator" / "profiles"
    result.check(
        "participant release contains only participant bundle material",
        (participant / _SHARED).is_file()
        and (participant / _GUIDED).is_file()
        and (participant / _UNGUIDED).is_file()
        and not (participant / _GUIDED_FACILITATOR).exists()
        and not (participant / _UNGUIDED_FACILITATOR).exists(),
    )
    result.check(
        "operator release contains both facilitator surfaces",
        (operator / _GUIDED_FACILITATOR).is_file()
        and (operator / _UNGUIDED_FACILITATOR).is_file()
        and metadata["release"]["pack"]["name"] == _PACK_ID,
    )


def _negative_checks(result: Result, pack: Path, workspace: Path) -> None:
    rejected: list[bool] = []
    for bundle_id, rel in (("guided", _GUIDED), ("unguided", _UNGUIDED)):
        mutated = workspace / f"leak-{bundle_id}" / _PACK_ID
        shutil.copytree(pack, mutated)
        with (mutated / "profiles" / rel).open("a", encoding="utf-8") as handle:
            handle.write("\nRestricted check token: T1059\n")
        rejected.append(
            any(
                "participant view leaks" in item
                for item in smoke_pack(str(mutated))
            )
        )
    result.check("restricted participant content is rejected", all(rejected))

    malformed = workspace / "malformed" / _PACK_ID
    shutil.copytree(pack, malformed)
    manifest = _bundles()
    manifest["bundles"] = [manifest["bundles"][0]]
    _write_yaml(malformed / "profiles" / "bundles.yaml", manifest)
    failures = lint_pack(str(malformed)) + smoke_pack(str(malformed))
    result.check(
        "malformed bundle selection is rejected",
        any("unguided" in item and "bundles.yaml" in item for item in failures),
    )


def _walk(result: Result, workspace: Path) -> None:
    pack, original_sdl = _create_pack(result, workspace)
    _author_profiles(pack)
    _positive_checks(result, pack, original_sdl, workspace / "release")
    with tempfile.TemporaryDirectory(prefix="two-audience-negative-") as temporary:
        _negative_checks(result, pack, Path(temporary))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        help="empty directory in which to retain the valid pack and release tree",
    )
    args = parser.parse_args(argv)
    print("Two audiences — static content-exposure evidence only")
    result = Result()
    if args.workspace is not None:
        workspace = args.workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        if any(workspace.iterdir()):
            parser.error("--workspace must be empty")
        _walk(result, workspace)
    else:
        with tempfile.TemporaryDirectory(
            prefix="two-audience-bundles-"
        ) as temporary:
            _walk(result, Path(temporary))
    print(f"\n{result.passed} passed, {result.failed} failed")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
