#!/usr/bin/env python3
"""Validate TechVault delivery projections against the canonical RAES SDL."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from raes import SDLParseError, parse_sdl_file


PROFILES_DIR = Path(__file__).resolve().parent
PACK_ROOT = PROFILES_DIR.parent
MANIFEST_IDENTIFIER = "bundles.yaml"
MANIFEST_PATH = "profiles/bundles.yaml"
PACK_MANIFEST_PATH = "pack.yaml"
COMPATIBILITY_PATH = "pack.compatibility.yaml"
REGULAR_FILE_REQUIRED = "regular contained file required"
REQUIRED_BUNDLE_IDS = ("guided", "unguided", "purple-team", "demo")
EXPECTED_AUDIENCES = {
    "guided": "participant",
    "unguided": "participant",
    "purple-team": "defender",
    "demo": "presenter",
}
COMPATIBILITY_AUDIENCES = {
    "guided": "guided",
    "unguided": "unguided",
    "purple-team": "purple-team",
    "demo": "demo",
}
MANIFEST_FIELDS = {
    "schema_version",
    "name",
    "scenario",
    "description",
    "audiences",
    "required_bundles",
    "bundles",
}
BUNDLE_FIELDS = {
    "id",
    "title",
    "audience",
    "summary",
    "runtime_profiles",
    "shared_includes",
    "participant_entrypoints",
    "operator_entrypoints",
}
STRUCTURAL_FILES = {"README.md", MANIFEST_IDENTIFIER, "validate_profiles.py"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
RESTRICTED_PARTICIPANT_PHRASES = (
    "operator-only",
    "oracle-only",
    "proof predicate",
    "management-plane",
)
RESTRICTED_PARTICIPANT_KEYS = {
    "answer",
    "credential",
    "flag_id",
    "negative_gate",
    "points",
    "predicate",
    "token",
}


@dataclass(frozen=True)
class Issue:
    object_type: str
    identifier: str
    field: str
    invariant: str

    def __str__(self) -> str:
        location = f"{self.object_type}:{self.identifier}"
        if self.field:
            location += f".{self.field}"
        return f"{location}: {self.invariant}"


def _issue(
    issues: list[Issue], object_type: str, identifier: str, field: str, invariant: str
) -> None:
    issues.append(Issue(object_type, identifier, field, invariant))


def _canonical_relative_path(value: str) -> PurePosixPath | None:
    if not value or "\\" in value:
        return None
    candidate = PurePosixPath(value)
    if candidate.is_absolute() or ".." in candidate.parts or str(candidate) != value:
        return None
    return candidate


def _pack_file(root: Path, relative: str) -> Path | None:
    canonical = _canonical_relative_path(relative)
    if canonical is None:
        return None
    candidate = root.joinpath(*canonical.parts)
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    if candidate.is_symlink() or not candidate.is_file():
        return None
    return candidate


def _load_yaml(root: Path, relative: str, issues: list[Issue]) -> Any:
    path = _pack_file(root, relative)
    if path is None:
        _issue(issues, "file", relative, "", REGULAR_FILE_REQUIRED)
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        _issue(issues, "file", relative, "", "safe YAML parse required")
        return None


def _string_list(
    value: Any, issues: list[Issue], identifier: str, field: str
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        _issue(issues, "manifest", identifier, field, "string list required")
        return []
    if len(value) != len(set(value)):
        _issue(issues, "manifest", identifier, field, "unique entries required")
    return value


def _profile_file(
    root: Path, bundle_id: str, visibility: str, relative: str, issues: list[Issue]
) -> Path | None:
    canonical = _canonical_relative_path(relative)
    if canonical is None:
        _issue(
            issues, "bundle", bundle_id, relative, "canonical contained path required"
        )
        return None
    parts = canonical.parts
    valid_root = (
        visibility == "shared" and len(parts) >= 2 and parts[0] == "_shared"
    ) or (
        visibility != "shared"
        and len(parts) >= 3
        and parts[0] == bundle_id
        and parts[1] == visibility
    )
    if not valid_root:
        _issue(
            issues,
            "bundle",
            bundle_id,
            relative,
            f"{visibility} visibility root required",
        )
        return None
    path = _pack_file(root, f"profiles/{relative}")
    if path is None:
        _issue(issues, "bundle", bundle_id, relative, REGULAR_FILE_REQUIRED)
    return path


def _scan_structured_keys(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in RESTRICTED_PARTICIPANT_KEYS for key in value):
            return True
        return any(_scan_structured_keys(child) for child in value.values())
    if isinstance(value, list):
        return any(_scan_structured_keys(child) for child in value)
    return False


def _has_pack_local_extension(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower().startswith("x-techvault") for key in value):
            return True
        return any(_has_pack_local_extension(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_pack_local_extension(child) for child in value)
    return False


def _scan_participant(path: Path, relative: str, issues: list[Issue]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _issue(issues, "participant", relative, "", "UTF-8 readable content required")
        return
    lowered = text.lower()
    if any(phrase in lowered for phrase in RESTRICTED_PARTICIPANT_PHRASES):
        _issue(
            issues,
            "participant",
            relative,
            "",
            "restricted participant content forbidden",
        )
    if path.suffix.lower() in {".yaml", ".yml", ".json"}:
        try:
            if _scan_structured_keys(yaml.safe_load(text)):
                _issue(
                    issues,
                    "participant",
                    relative,
                    "",
                    "restricted participant key forbidden",
                )
        except yaml.YAMLError:
            _issue(
                issues, "participant", relative, "", "safe structured parse required"
            )


def _validate_aces(root: Path, scenario_path: Any, issues: list[Issue]) -> None:
    if scenario_path != "sdl/techvault.sdl.yaml":
        _issue(
            issues,
            "manifest",
            MANIFEST_IDENTIFIER,
            "scenario",
            "canonical TechVault SDL path required",
        )
        return
    path = _pack_file(root, scenario_path)
    if path is None:
        _issue(issues, "ACES", "techvault", "sdl", REGULAR_FILE_REQUIRED)
        return
    raw = _load_yaml(root, scenario_path, issues)
    if _has_pack_local_extension(raw):
        _issue(
            issues,
            "ACES",
            "techvault",
            "extensions",
            "pack-local scenario contract forbidden",
        )
    try:
        scenario = parse_sdl_file(path)
    except (OSError, SDLParseError, ValueError):
        _issue(issues, "ACES", "techvault", "sdl", "parseable ACES scenario required")
        return
    if scenario.name != "techvault":
        _issue(
            issues, "ACES", "techvault", "name", "TechVault scenario identity required"
        )
    if not scenario.nodes or not scenario.infrastructure:
        _issue(
            issues, "ACES", "techvault", "resources", "non-empty ACES topology required"
        )


def _compatibility_rows(
    document: Any, issues: list[Issue]
) -> dict[str, dict[str, Any]]:
    if not isinstance(document, dict):
        _issue(issues, "compatibility", COMPATIBILITY_PATH, "", "mapping required")
        return {}
    rows = document.get("delivery_bundles")
    if not isinstance(rows, list):
        _issue(
            issues,
            "compatibility",
            COMPATIBILITY_PATH,
            "delivery_bundles",
            "list required",
        )
        return {}
    return {
        row.get("bundle_id"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("bundle_id"), str)
    }


def _path_refs(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        row["path"]
        for row in value
        if isinstance(row, dict) and isinstance(row.get("path"), str)
    }


def _validate_bundle_shape(row: dict[str, Any], issues: list[Issue]) -> str | None:
    bundle_id = row.get("id")
    if not isinstance(bundle_id, str) or not ID_PATTERN.fullmatch(bundle_id):
        _issue(issues, "bundle", str(bundle_id), "id", "kebab-case id required")
        return None
    unknown = set(row) - BUNDLE_FIELDS
    if unknown:
        _issue(issues, "bundle", bundle_id, "fields", "unknown fields forbidden")
    if set(row) != BUNDLE_FIELDS:
        _issue(issues, "bundle", bundle_id, "fields", "complete bundle fields required")
    expected_audience = EXPECTED_AUDIENCES.get(bundle_id)
    if expected_audience is None or row.get("audience") != expected_audience:
        _issue(issues, "bundle", bundle_id, "audience", "expected audience required")
    if row.get("runtime_profiles") != ["operational"]:
        _issue(
            issues,
            "bundle",
            bundle_id,
            "runtime_profiles",
            "single operational runtime required",
        )
    return bundle_id


def _validate_bundle_entries(
    root: Path,
    bundle_id: str,
    row: dict[str, Any],
    declared_files: set[str],
    issues: list[Issue],
) -> dict[str, list[str]]:
    projected: dict[str, list[str]] = {}
    for field, visibility in (
        ("shared_includes", "shared"),
        ("participant_entrypoints", "participant"),
        ("operator_entrypoints", "operator"),
    ):
        entries = _string_list(row.get(field), issues, bundle_id, field)
        projected[field] = entries
        for relative in entries:
            path = _profile_file(root, bundle_id, visibility, relative, issues)
            if path is None:
                continue
            declared_files.add(relative)
            if visibility in {"shared", "participant"}:
                _scan_participant(path, relative, issues)
    return projected


def _validate_bundle_compatibility(
    bundle_id: str,
    projected: dict[str, list[str]],
    compatibility: dict[str, dict[str, Any]],
    issues: list[Issue],
) -> None:
    compatible = compatibility.get(bundle_id)
    if not isinstance(compatible, dict):
        _issue(
            issues,
            "bundle",
            bundle_id,
            "compatibility",
            "supported compatibility row required",
        )
        return
    compatibility_audience = COMPATIBILITY_AUDIENCES.get(bundle_id)
    if (
        compatibility_audience is None
        or compatible.get("status") != "supported"
        or compatible.get("audience") != compatibility_audience
    ):
        _issue(
            issues,
            "bundle",
            bundle_id,
            "compatibility",
            "supported bundle projection required",
        )
    expected_participant = (
        {f"profiles/{bundle_id}/participant/"}
        if projected["participant_entrypoints"]
        else set()
    )
    expected_operator = (
        {f"profiles/{bundle_id}/operator/"}
        if projected["operator_entrypoints"]
        else set()
    )
    if _path_refs(compatible.get("participant_paths")) != expected_participant:
        _issue(
            issues,
            "bundle",
            bundle_id,
            "participant_paths",
            "matching compatibility projection required",
        )
    if _path_refs(compatible.get("operator_paths")) != expected_operator:
        _issue(
            issues,
            "bundle",
            bundle_id,
            "operator_paths",
            "matching compatibility projection required",
        )


def _validate_bundle(
    root: Path,
    row: dict[str, Any],
    compatibility: dict[str, dict[str, Any]],
    declared_files: set[str],
    issues: list[Issue],
) -> None:
    bundle_id = _validate_bundle_shape(row, issues)
    if bundle_id is None:
        return
    projected = _validate_bundle_entries(root, bundle_id, row, declared_files, issues)
    _validate_bundle_compatibility(bundle_id, projected, compatibility, issues)


def _manifest_rows(
    root: Path, manifest: dict[str, Any], issues: list[Issue]
) -> tuple[list[dict[str, Any]], list[str]]:
    if set(manifest) != MANIFEST_FIELDS:
        _issue(
            issues,
            "manifest",
            MANIFEST_IDENTIFIER,
            "fields",
            "exact manifest fields required",
        )
    if manifest.get("schema_version") != 1:
        _issue(
            issues,
            "manifest",
            MANIFEST_IDENTIFIER,
            "schema_version",
            "version 1 required",
        )
    _validate_aces(root, manifest.get("scenario"), issues)
    audiences = _string_list(
        manifest.get("audiences"), issues, MANIFEST_IDENTIFIER, "audiences"
    )
    if set(audiences) != set(EXPECTED_AUDIENCES.values()):
        _issue(
            issues,
            "manifest",
            MANIFEST_IDENTIFIER,
            "audiences",
            "declared audiences must match bundles",
        )

    rows = manifest.get("bundles")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        _issue(
            issues,
            "manifest",
            MANIFEST_IDENTIFIER,
            "bundles",
            "mapping list required",
        )
        rows = []
    ids = [row.get("id") for row in rows if isinstance(row.get("id"), str)]
    required = _string_list(
        manifest.get("required_bundles"),
        issues,
        MANIFEST_IDENTIFIER,
        "required_bundles",
    )
    if ids != list(REQUIRED_BUNDLE_IDS) or required != list(REQUIRED_BUNDLE_IDS):
        _issue(
            issues,
            "manifest",
            MANIFEST_IDENTIFIER,
            "bundles",
            "required bundle order and ids must match",
        )
    return rows, ids


def _pack_bundle_ids(pack: dict[str, Any], issues: list[Issue]) -> list[Any]:
    profile_index = pack.get("profile_bundles")
    if not isinstance(profile_index, dict):
        _issue(
            issues, "pack", PACK_MANIFEST_PATH, "profile_bundles", "mapping required"
        )
        profile_index = {}
    rows = profile_index.get("bundles")
    if not isinstance(rows, list):
        _issue(
            issues,
            "pack",
            PACK_MANIFEST_PATH,
            "profile_bundles.bundles",
            "list required",
        )
        return []
    return [row.get("id") for row in rows if isinstance(row, dict)]


def _scan_profile_tree(
    root: Path, declared_files: set[str], issues: list[Issue]
) -> None:
    for path in (root / "profiles").rglob("*"):
        if not path.is_file() or "tests" in path.parts or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root / "profiles").as_posix()
        if relative in STRUCTURAL_FILES or relative in declared_files:
            continue
        _issue(issues, "profile", relative, "", "undeclared profile content forbidden")
        if "/participant/" in f"/{relative}" or relative.startswith("_shared/"):
            _scan_participant(path, relative, issues)


def validate_pack(root: Path = PACK_ROOT) -> list[str]:
    issues: list[Issue] = []
    manifest = _load_yaml(root, MANIFEST_PATH, issues)
    pack = _load_yaml(root, PACK_MANIFEST_PATH, issues)
    compatible_document = _load_yaml(root, COMPATIBILITY_PATH, issues)
    if not isinstance(manifest, dict) or not isinstance(pack, dict):
        return sorted(str(issue) for issue in issues)
    rows, ids = _manifest_rows(root, manifest, issues)
    compatibility = _compatibility_rows(compatible_document, issues)
    pack_ids = _pack_bundle_ids(pack, issues)
    if set(ids) != set(pack_ids) or set(ids) != set(compatibility):
        _issue(
            issues,
            "manifest",
            MANIFEST_IDENTIFIER,
            "joins",
            "manifest pack and compatibility ids must agree",
        )

    declared_files: set[str] = set()
    for row in rows:
        _validate_bundle(root, row, compatibility, declared_files, issues)
    _scan_profile_tree(root, declared_files, issues)

    return sorted({str(issue) for issue in issues})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("validate",), default="validate")
    args = parser.parse_args()
    del args
    failures = validate_pack()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("TechVault ACES authority and delivery bundles: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
