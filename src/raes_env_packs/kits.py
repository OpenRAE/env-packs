"""Catalog-owned infrastructure kits and deterministic discovery projections.

Kits are authoring-time pack content, never runtime plugins.  This module owns
only the pack-domain carrier, safe local inspection, and generated discovery
projection.  The referenced SDL module is parsed by RAES; module identity,
parameters, exports, composition, trust, and lock records are not restated here.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import quote, unquote_to_bytes, urlsplit

import yaml
from raes import (
    SDLError,
    Scenario,
    canonical_sdl_digest,
    load_sdl_fragment,
    parse_sdl_file,
)
from raes.language_service import apply_structured_edit
from raes.module_registry import resolve_lock_records
from raes_contracts.associated_artifacts import (
    associated_artifact_set_digest,
    load_associated_artifact_manifest_json,
    validate_associated_artifact_manifest,
)
from raes_contracts.contracts import AssociatedArtifactManifestModel

from . import _pack_fs, _transactions, validation
from .digest import (
    PackDigestError,
    authored_sdl_parent,
    validate_pack_content_manifest,
)

KIT_SCHEMA_VERSION = "environment-pack-kit/v1"
KIT_CATALOG_SCHEMA_VERSION = "environment-pack-kit-catalog/v1"
KIT_MATERIALIZATIONS_SCHEMA_VERSION = "environment-pack-kit-materializations/v1"
KIT_MATERIALIZATIONS_PATH = "kit.materializations.json"
KIT_PROPOSAL_VERSION = "raes-pack-kit-proposal/v1"

_KIT_URI_SCHEME = "raes-environment-kit"
_KIT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{0,126}[a-z0-9]$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,126}[a-z0-9]$")
_NAMESPACE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_MAX_SOURCE_REVISION_BYTES = 512
_SAFE_ASSET_TARGET_PREFIXES = (
    "assets/briefing/",
    "assets/content/",
    "assets/kits/",
    "docs/kits/",
)
_RESOURCES = Path(__file__).with_name("resources")
_KIT_SCHEMA = _RESOURCES / "schemas" / "kit.schema.yaml"
_KIT_CATALOG_SCHEMA = _RESOURCES / "schemas" / "kit-catalog.schema.yaml"

_FORBIDDEN_MODULE_SECTIONS = (
    "agents",
    "action_contracts",
    "behavior_specifications",
    "conditions",
    "objectives",
    "injects",
    "events",
    "scripts",
    "stories",
    "workflows",
)
_SECRET_KEY_FRAGMENTS = (
    "credential",
    "password",
    "private_key",
    "secret",
    "signed_url",
    "token",
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:x-amz-signature|sig|signature|token)=[^&\s]+"),
    re.compile(r"(?i)https?://[^/@\s]+:[^/@\s]+@"),
    re.compile(r"(?:eyJ[A-Za-z0-9_-]{8,}\.){2}[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?:gh[pousr]_|AKIA)[A-Za-z0-9_-]{12,}"),
)
_ENVIRONMENT_COORDINATE_RE = re.compile(
    r"(?i)^(?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|env:[A-Za-z_][A-Za-z0-9_]*)$"
)
_TERMINAL_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


class KitError(ValueError):
    """One bounded infrastructure-kit input or integrity failure."""


class KitRecoveryError(KitError):
    """Atomic rollback failed, but the original tree remains recoverable."""

    def __init__(self, recovery_path: Path) -> None:
        super().__init__(
            "kit rollback failed; the original pack is preserved for recovery"
        )
        self.recovery_path = str(recovery_path)


@dataclass(frozen=True)
class KitLimits:
    """Resource bounds for inspecting one staged kit release."""

    max_members: int = 256
    max_member_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 32 * 1024 * 1024
    max_yaml_nodes: int = 20_000
    max_yaml_aliases: int = 64
    max_yaml_depth: int = 64

    def __post_init__(self) -> None:
        values = (
            self.max_members,
            self.max_member_bytes,
            self.max_total_bytes,
            self.max_yaml_nodes,
            self.max_yaml_aliases,
            self.max_yaml_depth,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in values
        ):
            raise ValueError("kit limits must be positive integers")


@dataclass(frozen=True)
class KitSource:
    """A stable catalog source id and immutable revision over a staged root."""

    id: str
    revision: str
    root: str


@dataclass(frozen=True)
class KitRelease:
    """One validated kit release and its RAES-owned module facts."""

    root: str
    document: Mapping[str, object]
    scenario: object
    associated_artifacts: AssociatedArtifactManifestModel
    inventory: tuple[str, ...]

    @property
    def id(self) -> str:
        return str(self.document["id"])

    @property
    def version(self) -> str:
        return str(self.document["version"])


@dataclass(frozen=True)
class _SnapshotFile:
    path: str
    content: bytes
    digest: str


@dataclass(frozen=True)
class _PackSnapshot:
    files: tuple[_SnapshotFile, ...]
    digest: str


@dataclass(frozen=True)
class KitProposal:
    """One immutable, exact successor proposal consumed by every front end."""

    operation: str
    pack_root: str
    kit_id: str
    kit_version: str
    materialization_id: str
    namespace: str
    target_sdl: str
    parameter_names: tuple[str, ...]
    topology: tuple[str, ...]
    dependencies: tuple[str, ...]
    assumptions: tuple[str, ...]
    lock_changes: tuple[str, ...]
    changes: tuple[str, ...]
    diagnostics: tuple[validation.Diagnostic, ...]
    _base_digest: str
    _successor: tuple[_SnapshotFile, ...]
    _successor_digest: str


def _schema_violations(document: object, schema_path: Path) -> list[str]:
    schema = validation._trusted_schema(schema_path)
    return [
        f"{item.code}:{item.path}"
        for item in validation._schema_violations(document, schema, schema)
    ]


def _iter_mapping_values(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _iter_mapping_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mapping_values(item)


def _secret_shape_violations(document: object) -> list[str]:
    violations: list[str] = []
    for key, value in _iter_mapping_values(document):
        normalized = str(key).casefold().replace("-", "_")
        if any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS):
            violations.append("secret-key")
        if isinstance(value, str) and any(
            pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS
        ):
            violations.append("secret-value")
    return violations


def _canonical_member(value: object, field: str, violations: list[str]) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return _pack_fs.normalize_relpath(value, error_type=KitError)
    except KitError:
        violations.append(f"path:{field}")
        return None


def _safe_asset_target(value: object) -> bool:
    """Whether a kit asset lands only in closed non-executable pack surfaces."""

    if not isinstance(value, str):
        return False
    try:
        rel = _pack_fs.normalize_relpath(value, error_type=KitError)
    except KitError:
        return False
    return rel.startswith(_SAFE_ASSET_TARGET_PREFIXES)


def validate_kit_document(document: object) -> list[str]:
    """Return stable, value-free violations for one authored kit manifest."""

    violations = _schema_violations(document, _KIT_SCHEMA)
    if not isinstance(document, dict):
        return sorted(set(violations))

    violations.extend(_secret_shape_violations(document))
    for field in ("id", "version", "title", "summary", "released_at"):
        value = document.get(field)
        if not isinstance(value, str) or not value.strip():
            violations.append(f"non-empty:$.{field}")
    if isinstance(document.get("title"), str) and _TERMINAL_CONTROL_RE.search(
        str(document["title"])
    ):
        violations.append("terminal-control:$.title")

    module = document.get("module")
    if isinstance(module, dict):
        _canonical_member(module.get("path"), "module.path", violations)
    _canonical_member(
        document.get("associated_artifact_manifest"),
        "associated_artifact_manifest",
        violations,
    )

    resources = document.get("resources")
    if isinstance(resources, dict):
        for field in ("cpu_cores", "memory_mib", "storage_mib"):
            value = resources.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                violations.append(f"positive:$.resources.{field}")

    seen_targets: set[str] = set()
    seen_artifacts: set[str] = set()
    assets = document.get("assets")
    for index, asset in enumerate(assets if isinstance(assets, list) else []):
        if not isinstance(asset, dict):
            continue
        source = _canonical_member(asset.get("source"), f"assets[{index}].source", violations)
        target = _canonical_member(asset.get("target"), f"assets[{index}].target", violations)
        if not _safe_asset_target(target):
            violations.append(f"safe-target:$.assets[{index}].target")
        artifact_id = asset.get("artifact_id")
        if target is not None and target in seen_targets:
            violations.append(f"duplicate:$.assets[{index}].target")
        if isinstance(artifact_id, str) and artifact_id in seen_artifacts:
            violations.append(f"duplicate:$.assets[{index}].artifact_id")
        if target is not None:
            seen_targets.add(target)
        if isinstance(artifact_id, str):
            seen_artifacts.add(artifact_id)

    tests = document.get("tests")
    seen_tests: set[tuple[object, object]] = set()
    test_kinds: set[object] = set()
    for index, test in enumerate(tests if isinstance(tests, list) else []):
        if not isinstance(test, dict):
            continue
        _canonical_member(test.get("path"), f"tests[{index}].path", violations)
        identity = (test.get("path"), test.get("kind"))
        if identity in seen_tests:
            violations.append(f"duplicate:$.tests[{index}]")
        seen_tests.add(identity)
        test_kinds.add(test.get("kind"))
    for kind in ("validate", "parameter-variation", "multi-kit"):
        if kind not in test_kinds:
            violations.append(f"required:$.tests[kind={kind}]")

    components = document.get("component_inventory")
    if not isinstance(components, list) or not components:
        violations.append("required:$.component_inventory")
    for index, component in enumerate(
        components if isinstance(components, list) else []
    ):
        if not isinstance(component, dict):
            continue
        scope = component.get("scope")
        authority = component.get("authority")
        if scope in {"shipped", "pinned"} and authority == "author-declared-external":
            violations.append(f"authority:$.component_inventory[{index}]")

    prerequisites = document.get("prerequisites")
    seen_prerequisites: set[tuple[object, object, object]] = set()
    for index, prerequisite in enumerate(
        prerequisites if isinstance(prerequisites, list) else []
    ):
        if not isinstance(prerequisite, dict):
            continue
        identity = (
            prerequisite.get("kind"),
            prerequisite.get("id"),
            prerequisite.get("version"),
        )
        if identity in seen_prerequisites:
            violations.append(f"duplicate:$.prerequisites[{index}]")
        seen_prerequisites.add(identity)
        if prerequisite.get("kind") == "kit" and (
            not isinstance(prerequisite.get("id"), str)
            or _KIT_ID_RE.fullmatch(str(prerequisite["id"])) is None
            or not isinstance(prerequisite.get("version"), str)
            or _VERSION_RE.fullmatch(str(prerequisite["version"])) is None
        ):
            violations.append(f"identity:$.prerequisites[{index}]")

    return sorted(set(violations))


def validate_kit_catalog_document(document: object) -> list[str]:
    """Validate one generated catalog document against its closed v1 shape."""

    return sorted(set(_schema_violations(document, _KIT_CATALOG_SCHEMA)))


def validate_materializations_document(document: object) -> list[str]:
    """Validate one inert materialization/ownership ledger."""

    return validation.validate_kit_materializations_document(document)


def _strict_yaml(data: bytes, *, limits: KitLimits) -> object:
    try:
        text = data.decode("utf-8", errors="strict")
        validation._check_yaml_events(
            text,
            validation.PackValidationLimits(
                max_yaml_nodes=limits.max_yaml_nodes,
                max_yaml_aliases=limits.max_yaml_aliases,
                max_yaml_depth=limits.max_yaml_depth,
            ),
        )
        return yaml.load(text, Loader=validation._StrictLoader)
    except (UnicodeDecodeError, yaml.YAMLError, ValueError) as exc:
        raise KitError("kit manifest is not valid bounded strict YAML") from exc


def _strict_json_object(data: bytes, *, label: str) -> dict[str, object]:
    """Parse one bounded UTF-8 JSON object while rejecting duplicate members."""

    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        document: dict[str, object] = {}
        for key, value in pairs:
            if key in document:
                raise ValueError("duplicate JSON member")
            document[key] = value
        return document

    def invalid_constant(_value: str) -> object:
        raise ValueError("non-finite JSON number")

    try:
        document = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=object_pairs,
            parse_constant=invalid_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise KitError(f"{label} is invalid") from exc
    if not isinstance(document, dict):
        raise KitError(f"{label} is invalid")
    return document


def _strict_pack_yaml(data: bytes) -> dict[str, object]:
    try:
        document = _strict_yaml(data, limits=KitLimits())
    except KitError as exc:
        raise KitError("pack manifest is invalid") from exc
    if not isinstance(document, dict):
        raise KitError("pack manifest is invalid")
    return document


def _read_member(root_fd: int, rel: str, limits: KitLimits) -> bytes:
    try:
        return _pack_fs.read_member_bytes(
            root_fd,
            rel,
            max_bytes=limits.max_member_bytes,
            error_type=KitError,
        )
    except _pack_fs.PackFilesystemError as exc:
        raise KitError("kit member could not be read safely") from exc


def _kit_uri_path(uri: str) -> str:
    parsed = urlsplit(uri)
    if (
        parsed.scheme != _KIT_URI_SCHEME
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise KitError("associated artifact URI is not a canonical kit locator")
    try:
        path = unquote_to_bytes(parsed.path[1:]).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise KitError("associated artifact URI is not valid UTF-8") from exc
    return _pack_fs.normalize_relpath(path, error_type=KitError)


def _module_document(document: Mapping[str, object]) -> str:
    module = document.get("module")
    if not isinstance(module, dict):
        raise KitError("kit module pointer is invalid")
    rel = module.get("path")
    if not isinstance(rel, str):
        raise KitError("kit module pointer is invalid")
    return _pack_fs.normalize_relpath(rel, error_type=KitError)


def _manifest_document(document: Mapping[str, object]) -> str:
    rel = document.get("associated_artifact_manifest")
    if not isinstance(rel, str):
        raise KitError("kit associated-artifact pointer is invalid")
    return _pack_fs.normalize_relpath(rel, error_type=KitError)


def _verify_infrastructure_only(scenario: object) -> None:
    for section in _FORBIDDEN_MODULE_SECTIONS:
        if getattr(scenario, section, None):
            raise KitError("kit module contains scenario behavior or narrative")


def load_kit_release(
    kit_root: str | os.PathLike[str], *, limits: KitLimits | None = None
) -> KitRelease:
    """Safely load and byte-bind one immutably staged local kit release."""

    active = limits or KitLimits()
    try:
        root, root_fd = _pack_fs.open_root(kit_root, error_type=KitError)
    except (_pack_fs.PackFilesystemError, OSError) as exc:
        raise KitError("kit root could not be opened safely") from exc
    try:
        inventory = _pack_fs.inventory(
            root_fd, max_members=active.max_members, error_type=KitError
        )
        if "kit.yaml" not in inventory:
            raise KitError("kit manifest is missing")
        document = _strict_yaml(_read_member(root_fd, "kit.yaml", active), limits=active)
        violations = validate_kit_document(document)
        if violations or not isinstance(document, dict):
            raise KitError("kit manifest does not satisfy the closed contract")

        module_rel = _module_document(document)
        manifest_rel = _manifest_document(document)
        required_paths = {module_rel, manifest_rel}
        required_paths.update(
            str(item.get("source"))
            for item in document.get("assets", [])
            if isinstance(item, dict) and isinstance(item.get("source"), str)
        )
        required_paths.update(
            str(item.get("path"))
            for item in document.get("tests", [])
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        )
        if not required_paths.issubset(set(inventory)):
            raise KitError("kit references a missing member")

        raw_module = _strict_yaml(_read_member(root_fd, module_rel, active), limits=active)
        if isinstance(raw_module, dict) and any(
            raw_module.get(section) for section in _FORBIDDEN_MODULE_SECTIONS
        ):
            raise KitError("kit module contains scenario behavior or narrative")
        raw_descriptor = raw_module.get("module") if isinstance(raw_module, dict) else None
        raw_parameters = (
            raw_descriptor.get("parameters") if isinstance(raw_descriptor, dict) else []
        )
        if isinstance(raw_parameters, list) and any(
            isinstance(parameter, str)
            and any(
                fragment in parameter.casefold().replace("-", "_")
                for fragment in _SECRET_KEY_FRAGMENTS
            )
            for parameter in raw_parameters
        ):
            raise KitError("kit module declares a secret-shaped parameter")

        try:
            scenario = parse_sdl_file(Path(root, *module_rel.split("/")))
        except (SDLError, OSError, ValueError) as exc:
            raise KitError("kit module is not valid RAES SDL") from exc
        descriptor = getattr(scenario, "module", None)
        if descriptor is None:
            raise KitError("kit module has no RAES module descriptor")
        if descriptor.version != document.get("version"):
            raise KitError("kit version and RAES module version differ")
        if any(
            fragment in parameter.casefold().replace("-", "_")
            for parameter in descriptor.parameters
            for fragment in _SECRET_KEY_FRAGMENTS
        ):
            raise KitError("kit module declares a secret-shaped parameter")
        _verify_infrastructure_only(scenario)

        manifest_bytes = _read_member(root_fd, manifest_rel, active)
        try:
            manifest = load_associated_artifact_manifest_json(manifest_bytes)
        except (ValueError, TypeError) as exc:
            raise KitError("kit associated-artifact manifest is invalid") from exc
        if (
            manifest.manifest_id != f"{document['id']}-associated-artifacts"
            or manifest.manifest_version != document["version"]
        ):
            raise KitError("kit associated-artifact identity does not match the kit")

        artifact_paths: dict[str, str] = {}
        readers: dict[str, io.BytesIO] = {}
        total = len(manifest_bytes)
        if total > active.max_total_bytes:
            raise KitError("kit payload bytes exceed the inspection limit")
        for artifact_id, artifact in manifest.artifacts.items():
            rel = _kit_uri_path(artifact.uri)
            if rel == manifest_rel or rel in artifact_paths.values():
                raise KitError("kit associated-artifact paths are not unique")
            if rel not in inventory:
                raise KitError("kit associated artifact is missing")
            data = _read_member(root_fd, rel, active)
            total += len(data)
            if total > active.max_total_bytes:
                raise KitError("kit payload bytes exceed the inspection limit")
            artifact_paths[artifact_id] = rel
            readers[artifact_id] = io.BytesIO(data)
        expected_inventory = set(inventory) - {manifest_rel}
        if set(artifact_paths.values()) != expected_inventory:
            raise KitError("kit associated artifacts do not cover the exact release")
        diagnostics = validate_associated_artifact_manifest(
            manifest, parent=scenario, artifact_readers=readers
        )
        if diagnostics:
            raise KitError("kit associated-artifact byte binding failed")
        if canonical_sdl_digest(scenario).value != manifest.parent_ref.ref_digest:
            raise KitError("kit semantic parent digest does not match the module")
        if _pack_fs.inventory(
            root_fd, max_members=active.max_members, error_type=KitError
        ) != inventory:
            raise KitError("kit inventory changed during inspection")
    finally:
        os.close(root_fd)
    return KitRelease(
        root=root,
        document=document,
        scenario=scenario,
        associated_artifacts=manifest,
        inventory=inventory,
    )


def inspect_kit(release: KitRelease) -> dict[str, object]:
    """Return one deterministic discovery record with RAES-derived module facts."""

    descriptor = release.scenario.module
    assert descriptor is not None
    document = release.document
    variables = release.scenario.variables
    if any(parameter not in variables for parameter in descriptor.parameters):
        raise KitError("RAES module parameter has no RAES variable definition")
    topology = [
        f"{section}.{name}"
        for section, names in sorted(descriptor.exports.items())
        for name in names
    ]
    return {
        "id": release.id,
        "version": release.version,
        "title": document["title"],
        "summary": document["summary"],
        "concern": document["concern"],
        "released_at": document["released_at"],
        "module": {
            "id": descriptor.id,
            "version": descriptor.version,
            "parameters": list(descriptor.parameters),
            "parameter_defaults": {
                parameter: variables[parameter].default
                for parameter in descriptor.parameters
            },
            "exports": {
                section: list(names)
                for section, names in sorted(descriptor.exports.items())
            },
        },
        "topology": topology,
        "required_imports": [
            {"id": item["id"], "version": item["version"]}
            for item in document["prerequisites"]
            if item["kind"] == "kit"
        ],
        "assets": list(document["assets"]),
        "resources": dict(document["resources"]),
        "prerequisites": list(document["prerequisites"]),
        "limitations": list(document["limitations"]),
        "license": dict(document["license"]),
        "tests": list(document["tests"]),
        "component_inventory": list(document["component_inventory"]),
    }


def _validate_source(source: KitSource) -> None:
    if not isinstance(source.id, str) or _SOURCE_ID_RE.fullmatch(source.id) is None:
        raise KitError("kit source id is invalid")
    if (
        not isinstance(source.revision, str)
        or not source.revision.strip()
        or len(source.revision.encode("utf-8")) > _MAX_SOURCE_REVISION_BYTES
        or _secret_value(source.revision)
    ):
        raise KitError("kit source revision is invalid")
    if not isinstance(source.root, (str, os.PathLike)):
        raise KitError("kit source root is invalid")


def _source_release_roots(source: KitSource) -> tuple[str, ...]:
    _validate_source(source)
    try:
        _root, root_fd = _pack_fs.open_root(source.root, error_type=KitError)
    except (_pack_fs.PackFilesystemError, OSError) as exc:
        raise KitError("kit catalog source could not be opened safely") from exc
    try:
        inventory = _pack_fs.inventory(root_fd, max_members=16_384, error_type=KitError)
    finally:
        os.close(root_fd)
    releases: set[str] = set()
    for rel in inventory:
        parts = rel.split("/")
        if len(parts) == 4 and parts[0] == "kits" and parts[3] == "kit.yaml":
            releases.add("/".join(parts[:3]))
    return tuple(sorted(releases))


def build_kit_catalog(sources: tuple[KitSource, ...]) -> dict[str, object]:
    """Build a byte-deterministic catalog projection from staged sources."""

    entries: list[dict[str, object]] = []
    identities: set[tuple[str, str, str]] = set()
    for source in sorted(sources, key=lambda item: (item.id, item.revision)):
        for rel in _source_release_roots(source):
            release = load_kit_release(Path(source.root, *rel.split("/")))
            _prefix, path_id, path_version = rel.split("/")
            if release.id != path_id or release.version != path_version:
                raise KitError("kit release path does not match its identity")
            identity = (source.id, release.id, release.version)
            if identity in identities:
                raise KitError("kit catalog contains a duplicate immutable identity")
            identities.add(identity)
            entry = inspect_kit(release)
            entry["source"] = {"id": source.id, "revision": source.revision}
            entries.append(entry)
    entries.sort(key=lambda item: (
        str(item["source"]["id"]), str(item["id"]), str(item["version"])
    ))
    document: dict[str, object] = {
        "schema_version": KIT_CATALOG_SCHEMA_VERSION,
        "entries": entries,
    }
    if validate_kit_catalog_document(document):
        raise KitError("generated kit catalog violates its closed contract")
    return document


def catalog_json(document: Mapping[str, object]) -> str:
    """Serialize one generated catalog with stable UTF-8 JSON formatting."""

    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def search_catalog(
    catalog: Mapping[str, object], query: str
) -> tuple[Mapping[str, object], ...]:
    """Search deterministic public discovery fields without opening releases."""

    if not isinstance(query, str) or len(query.encode("utf-8")) > 4096:
        raise KitError("kit search query is invalid")
    needle = query.casefold().strip()
    entries = catalog.get("entries")
    if not isinstance(entries, list):
        raise KitError("kit catalog is invalid")
    matches: list[Mapping[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise KitError("kit catalog is invalid")
        haystack = " ".join(
            str(entry.get(field, ""))
            for field in ("id", "title", "summary", "concern")
        ).casefold()
        if not needle or needle in haystack:
            matches.append(entry)
    return tuple(matches)


def source_release(source: KitSource, kit_id: str, version: str) -> KitRelease:
    """Load one exact immutable release below a stable staged source root."""

    _validate_source(source)
    if (
        not isinstance(kit_id, str)
        or _KIT_ID_RE.fullmatch(kit_id) is None
        or not isinstance(version, str)
        or _VERSION_RE.fullmatch(version) is None
    ):
        raise KitError("kit release identity is invalid")
    expected = Path(source.root, "kits", kit_id, version)
    release = load_kit_release(expected)
    if release.id != kit_id or release.version != version:
        raise KitError("kit release path does not match its identity")
    return release


# --------------------------------------------------------------------------- #
# Immutable pack proposals and transactional materialization
# --------------------------------------------------------------------------- #
_PACK_MAX_MEMBERS = 2048
_PACK_MAX_MEMBER_BYTES = 8 * 1024 * 1024
_PACK_MAX_TOTAL_BYTES = 64 * 1024 * 1024
_CACHE_PREFIX = (("sdl", ".raes", "module-cache"),)


def _digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _snapshot_digest(files: tuple[_SnapshotFile, ...]) -> str:
    digest = hashlib.sha256()
    for item in files:
        encoded = item.path.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(bytes.fromhex(item.digest.removeprefix("sha256:")))
    return "sha256:" + digest.hexdigest()


def _capture_pack(pack_root: str | os.PathLike[str]) -> _PackSnapshot:
    """Capture one bounded descriptor-anchored pack snapshot."""

    try:
        _root, root_fd = _pack_fs.open_root(pack_root, error_type=KitError)
    except (KitError, OSError) as exc:
        raise KitError("pack root could not be opened safely") from exc
    try:
        inventory = _pack_fs.inventory(
            root_fd,
            max_members=_PACK_MAX_MEMBERS,
            excluded_prefixes=_CACHE_PREFIX,
            error_type=KitError,
        )
        files: list[_SnapshotFile] = []
        total = 0
        for rel in inventory:
            data = _pack_fs.read_member_bytes(
                root_fd,
                rel,
                max_bytes=_PACK_MAX_MEMBER_BYTES,
                error_type=KitError,
            )
            total += len(data)
            if total > _PACK_MAX_TOTAL_BYTES:
                raise KitError("pack bytes exceed the proposal limit")
            files.append(_SnapshotFile(rel, data, _digest_bytes(data)))
        if _pack_fs.inventory(
            root_fd,
            max_members=_PACK_MAX_MEMBERS,
            excluded_prefixes=_CACHE_PREFIX,
            error_type=KitError,
        ) != inventory:
            raise KitError("pack inventory changed during proposal capture")
    finally:
        os.close(root_fd)
    frozen = tuple(files)
    return _PackSnapshot(frozen, _snapshot_digest(frozen))


def _snapshot_mapping(snapshot: _PackSnapshot) -> dict[str, bytes]:
    return {item.path: item.content for item in snapshot.files}


def _write_snapshot(root: Path, files: Mapping[str, bytes]) -> None:
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    for rel, content in sorted(files.items()):
        _transactions.write_member(root, rel, content)


def _diagnostic(
    code: str, path: str | None = None, field_path: str | None = None
) -> validation.Diagnostic:
    message = code
    if path:
        message += f": {path}"
    if field_path:
        message += f":{field_path}"
    return validation.Diagnostic(
        code=code, path=path, field_path=field_path, message=message[:240]
    )


def _ordered_diagnostics(
    diagnostics: list[validation.Diagnostic],
) -> tuple[validation.Diagnostic, ...]:
    unique = {item.message: item for item in diagnostics}
    return tuple(unique[key] for key in sorted(unique))


def _secret_value(value: object) -> bool:
    if isinstance(value, str):
        return _ENVIRONMENT_COORDINATE_RE.fullmatch(value) is not None or any(
            pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS
        )
    return False


def _normalize_parameters(
    release: KitRelease, parameters: Mapping[str, object]
) -> tuple[dict[str, object], list[validation.Diagnostic]]:
    diagnostics: list[validation.Diagnostic] = []
    if not isinstance(parameters, Mapping) or len(parameters) > 64:
        return {}, [_diagnostic("kit.parameter.invalid", field_path="parameters")]
    allowed = set(release.scenario.module.parameters)
    normalized: dict[str, object] = {}
    for key, value in sorted(parameters.items(), key=lambda item: str(item[0])):
        if not isinstance(key, str) or key not in allowed:
            diagnostics.append(
                _diagnostic("kit.parameter.unknown", field_path="parameters")
            )
            continue
        if (
            not isinstance(value, (str, int, float, bool))
            or isinstance(value, float) and not math.isfinite(value)
            or isinstance(value, str) and len(value.encode("utf-8")) > 4096
        ):
            diagnostics.append(
                _diagnostic("kit.parameter.invalid", field_path="parameters")
            )
            continue
        if _secret_value(value):
            diagnostics.append(
                _diagnostic("kit.parameter.secret", field_path="parameters")
            )
            continue
        normalized[key] = value
    return normalized, diagnostics


def _load_ledger(files: Mapping[str, bytes]) -> dict[str, object]:
    if KIT_MATERIALIZATIONS_PATH not in files:
        return {
            "schema_version": KIT_MATERIALIZATIONS_SCHEMA_VERSION,
            "materializations": [],
            "files": [],
        }
    document = _strict_json_object(
        files[KIT_MATERIALIZATIONS_PATH], label="kit materialization ledger"
    )
    if validate_materializations_document(document):
        raise KitError("kit materialization ledger violates its closed contract")
    return document


def _pack_pointer(files: Mapping[str, bytes]) -> tuple[dict[str, object], str]:
    try:
        pack = _strict_pack_yaml(files["pack.yaml"])
    except KeyError as exc:
        raise KitError("pack manifest is invalid") from exc
    pointer = pack.get("associated_artifact_manifest")
    if not isinstance(pointer, str):
        raise KitError("pack has no associated-artifact identity")
    return pack, _pack_fs.normalize_relpath(pointer, error_type=KitError)


def _pack_artifact_path(uri: str, manifest_rel: str) -> str:
    parsed = urlsplit(uri)
    if (
        parsed.scheme != "raes-environment-pack"
        or parsed.netloc
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/")
    ):
        raise KitError("pack associated-artifact URI is invalid")
    try:
        rel = unquote_to_bytes(parsed.path[1:]).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise KitError("pack associated-artifact URI is invalid") from exc
    rel = _pack_fs.normalize_relpath(rel, error_type=KitError)
    if rel == manifest_rel:
        raise KitError("pack associated-artifact manifest is recursive")
    return rel


def _load_pack_artifacts(
    files: Mapping[str, bytes], manifest_rel: str
) -> tuple[AssociatedArtifactManifestModel, dict[str, str]]:
    try:
        manifest = load_associated_artifact_manifest_json(files[manifest_rel])
    except (KeyError, ValueError, TypeError) as exc:
        raise KitError("pack associated-artifact manifest is invalid") from exc
    paths: dict[str, str] = {}
    for artifact_id, artifact in manifest.artifacts.items():
        rel = _pack_artifact_path(artifact.uri, manifest_rel)
        if rel in paths.values():
            raise KitError("pack associated-artifact paths are not unique")
        paths[artifact_id] = rel
    return manifest, paths


def _release_bytes(release: KitRelease, rel: str) -> bytes:
    try:
        _root, root_fd = _pack_fs.open_root(release.root, error_type=KitError)
    except (KitError, OSError) as exc:
        raise KitError("kit release could not be reopened safely") from exc
    try:
        return _pack_fs.read_member_bytes(
            root_fd,
            rel,
            max_bytes=KitLimits().max_member_bytes,
            error_type=KitError,
        )
    finally:
        os.close(root_fd)


def _release_artifact_metadata(release: KitRelease) -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for artifact in release.associated_artifacts.artifacts.values():
        metadata[_kit_uri_path(artifact.uri)] = artifact.model_dump(mode="python")
    return metadata


def _unique_artifact_id(
    preferred: str, unavailable: set[str], *, path: str
) -> str:
    candidate = re.sub(r"[^a-zA-Z0-9_.-]+", "-", preferred).strip("-") or "artifact"
    if candidate not in unavailable:
        return candidate
    suffix = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
    candidate = f"{candidate}-{suffix}"
    if candidate in unavailable:
        raise KitError("associated-artifact id collision")
    return candidate


def _new_artifact(
    artifact_id: str,
    rel: str,
    body: bytes,
    *,
    source: str,
    created_at: str,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    document = dict(metadata or {})
    document.update(
        {
            "artifact_id": artifact_id,
            "uri": f"raes-environment-pack:/{quote(rel, safe='/-._~')}",
            "checksum": {
                "algorithm": "sha256",
                "value": hashlib.sha256(body).hexdigest(),
            },
            "size_bytes": len(body),
        }
    )
    document.setdefault("role", "configuration")
    document.setdefault("media_type", "application/octet-stream")
    document.setdefault("created_at", created_at)
    document.setdefault("source", source)
    document.setdefault("sensitivity", "internal")
    return document


def _ensure_pack_identity(
    candidate: Path, files: dict[str, bytes], *, created_at: str
) -> None:
    """Initialize the existing RAES associated-artifact contract when absent."""

    try:
        pack = _strict_pack_yaml(files["pack.yaml"])
    except KeyError as exc:
        raise KitError("pack manifest is invalid") from exc
    existing = pack.get("associated_artifact_manifest")
    if isinstance(existing, str):
        return
    if existing is not None or "associated-artifacts.json" in files:
        raise KitError("pack associated-artifact pointer is ambiguous")
    manifest_rel = "associated-artifacts.json"
    pack["associated_artifact_manifest"] = manifest_rel
    files["pack.yaml"] = yaml.safe_dump(pack, sort_keys=False).encode("utf-8")
    _transactions.write_member(candidate, "pack.yaml", files["pack.yaml"])

    name = pack.get("name")
    version = pack.get("version")
    if not isinstance(name, str) or not name or version is None:
        raise KitError("pack identity is invalid")
    paths = sorted(
        rel
        for rel in files
        if rel.startswith("sdl/") and rel.count("/") == 1 and rel.endswith(".sdl.yaml")
    )
    parsed = [parse_sdl_file(candidate.joinpath(*rel.split("/"))) for rel in paths]
    parent_index = next(
        (index for index, scenario in enumerate(parsed) if scenario.name == name),
        None,
    )
    if parent_index is None:
        raise KitError("pack semantic parent is invalid")
    parsed_parent = parsed[parent_index]
    parent_path = candidate.joinpath(*paths[parent_index].split("/"))
    parent = (
        parsed_parent
        if isinstance(parsed_parent, Scenario)
        else authored_sdl_parent(parent_path, expanded=parsed_parent)
    )
    if isinstance(parsed_parent, Scenario):
        parent_ref: dict[str, object] = {
            "ref_kind": "scenario-snapshot",
            "ref_id": name,
            "ref_digest": canonical_sdl_digest(parent).value,
        }
    else:
        parent_ref = {"ref_kind": "scenario", "ref_id": name}
    artifacts: dict[str, object] = {}
    for rel in sorted(files):
        artifact_id = f"pack-{hashlib.sha256(rel.encode()).hexdigest()[:16]}"
        artifacts[artifact_id] = _new_artifact(
            artifact_id,
            rel,
            files[rel],
            source="environment-pack-author",
            created_at=created_at,
        )
    manifest = AssociatedArtifactManifestModel.model_validate(
        {
            "schema_version": "associated-artifact-manifest/v1",
            "manifest_id": f"{name}-associated-artifacts",
            "manifest_version": str(version),
            "canonicalization_profile": "associated-artifact-set/v1",
            "scope": "scenario",
            "parent_ref": parent_ref,
            "artifacts": artifacts,
            "set_digest": "sha256:" + "0" * 64,
        }
    )
    manifest = manifest.model_copy(
        update={"set_digest": associated_artifact_set_digest(manifest)}
    )
    files[manifest_rel] = (manifest.model_dump_json(indent=2) + "\n").encode(
        "utf-8"
    )
    _transactions.write_member(candidate, manifest_rel, files[manifest_rel])


def _refresh_associated_artifacts(
    candidate: Path,
    files: dict[str, bytes],
    *,
    kit_metadata: Mapping[str, tuple[str, Mapping[str, object]]],
    created_at: str,
) -> None:
    """Rebind the exact ordinary pack inventory through RAES's artifact model."""

    pack, manifest_rel = _pack_pointer(files)
    prior, prior_paths = _load_pack_artifacts(files, manifest_rel)
    inventory = sorted(rel for rel in files if rel != manifest_rel)
    prior_by_path = {
        rel: prior.artifacts[artifact_id].model_dump(mode="python")
        for artifact_id, rel in prior_paths.items()
        if rel in files
    }
    artifacts: dict[str, object] = {}
    prior_ids = set(prior.artifacts)
    for rel in inventory:
        prior_document = prior_by_path.get(rel)
        if prior_document is not None:
            artifact_id = str(prior_document["artifact_id"])
            if artifact_id in artifacts:
                raise KitError("associated-artifact id collision")
            metadata = prior_document
            source = str(prior_document.get("source") or "environment-pack-author")
        elif rel in kit_metadata:
            preferred, metadata = kit_metadata[rel]
            artifact_id = _unique_artifact_id(
                preferred, prior_ids | set(artifacts), path=rel
            )
            source = str(metadata.get("source") or "environment-kit")
        else:
            preferred = (
                "kit-materializations"
                if rel == KIT_MATERIALIZATIONS_PATH
                else "raes-lock"
                if rel.endswith("/raes.lock.json")
                else f"pack-{hashlib.sha256(rel.encode()).hexdigest()[:16]}"
            )
            artifact_id = _unique_artifact_id(
                preferred, prior_ids | set(artifacts), path=rel
            )
            metadata = None
            source = "environment-pack-author"
        artifacts[artifact_id] = _new_artifact(
            artifact_id,
            rel,
            files[rel],
            source=source,
            created_at=created_at,
            metadata=metadata,
        )

    scenario_paths = sorted(
        rel
        for rel in inventory
        if rel.startswith("sdl/") and rel.count("/") == 1 and rel.endswith(".sdl.yaml")
    )
    if not scenario_paths:
        raise KitError("pack has no direct SDL semantic parent")
    paths = [candidate.joinpath(*rel.split("/")) for rel in scenario_paths]
    expanded = [parse_sdl_file(path) for path in paths]
    scenarios = [
        scenario
        if isinstance(scenario, Scenario)
        else authored_sdl_parent(path, expanded=scenario)
        for path, scenario in zip(paths, expanded)
    ]
    name = pack.get("name")
    parent_index = next(
        (index for index, scenario in enumerate(scenarios) if scenario.name == name),
        None,
    )
    if parent_index is None:
        raise KitError("pack semantic parent does not match pack identity")
    parent = scenarios[parent_index]
    parsed_parent = expanded[parent_index]
    if isinstance(parsed_parent, Scenario):
        parent_ref: dict[str, object] = {
            "ref_kind": "scenario-snapshot",
            "ref_id": str(name),
            "ref_digest": canonical_sdl_digest(parent).value,
        }
    else:
        # RAES 3.2 canonicalizes the validated expanded composition but its
        # associated-artifact validator does not yet admit that authoring phase
        # as a snapshot parent (OpenRAE/rae#1040). Use RAES's generic scenario
        # reference without manufacturing private validation state. The exact
        # root SDL, module files, lock, and all other pack bytes remain bound by
        # the RAES associated-artifact set digest.
        parent_ref = {"ref_kind": "scenario", "ref_id": str(name)}
    payload = prior.model_dump(mode="python")
    payload.update(
        {
            "manifest_id": f"{name}-associated-artifacts",
            "manifest_version": str(pack.get("version")),
            "parent_ref": parent_ref,
            "artifacts": artifacts,
            "set_digest": "sha256:" + "0" * 64,
        }
    )
    manifest = AssociatedArtifactManifestModel.model_validate(payload)
    manifest = manifest.model_copy(
        update={"set_digest": associated_artifact_set_digest(manifest)}
    )
    files[manifest_rel] = (manifest.model_dump_json(indent=2) + "\n").encode("utf-8")
    _transactions.write_member(candidate, manifest_rel, files[manifest_rel])


def _module_destination(release: KitRelease, namespace: str) -> str:
    return f"sdl/kits/{namespace}/{release.id}/{release.version}/module.sdl.yaml"


def _local_source(target_sdl: str, module_path: str) -> str:
    relative = os.path.relpath(module_path, os.path.dirname(target_sdl)).replace(os.sep, "/")
    return f"local:{relative}"


def _edit_import(
    content: bytes,
    *,
    operation: str,
    import_value: Mapping[str, object] | None = None,
    namespace: str = "",
) -> bytes:
    try:
        text_content = content.decode("utf-8", errors="strict")
        document = load_sdl_fragment(text_content)
    except (UnicodeDecodeError, SDLError, ValueError) as exc:
        raise KitError("target SDL is invalid") from exc
    if not isinstance(document, dict):
        raise KitError("target SDL is invalid")
    current = document.get("imports")
    if operation == "add":
        if current is None:
            first = apply_structured_edit(
                text_content, operation="set", pointer="/imports", value=[]
            )
            if first.get("status") not in {"edited", "edited_with_diagnostics"}:
                raise KitError("RAES could not initialize module imports")
            text = str(first["content"])
        elif isinstance(current, list):
            text = text_content
        else:
            raise KitError("target SDL imports are invalid")
        result = apply_structured_edit(
            text, operation="append", pointer="/imports", value=dict(import_value or {})
        )
    else:
        if not isinstance(current, list):
            raise KitError("owned RAES import is missing")
        indices = [
            index
            for index, item in enumerate(current)
            if isinstance(item, dict) and item.get("namespace") == namespace
        ]
        if len(indices) != 1:
            raise KitError("owned RAES import is missing or ambiguous")
        result = apply_structured_edit(
            text_content,
            operation="delete",
            pointer=f"/imports/{indices[0]}",
        )
    if result.get("status") not in {"edited", "edited_with_diagnostics"}:
        raise KitError("RAES rejected the module import edit")
    # RAES's language edit cannot file-resolve imports and therefore returns an
    # expected parse diagnostic for any imported document. The complete staged
    # successor is file-backed parsed and semantically validated before the
    # proposal can be returned; no exception prose is interpreted here.
    return str(result["content"]).encode("utf-8")


def _lock_bytes(candidate: Path, target_sdl: str) -> bytes:
    try:
        lock = resolve_lock_records(candidate.joinpath(*target_sdl.split("/")))
    except (SDLError, OSError, ValueError) as exc:
        raise KitError("RAES could not resolve the exact module lock") from exc
    return (
        json.dumps(lock.model_dump(mode="python"), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _lock_path(target_sdl: str) -> str:
    directory = os.path.dirname(target_sdl)
    return f"{directory}/raes.lock.json" if directory else "raes.lock.json"


def _baseline_file(
    path: str, owners: list[str], artifact_id: str, files: Mapping[str, bytes]
) -> dict[str, object]:
    return {
        "path": path,
        "baseline_digest": _digest_bytes(files[path]),
        "owners": sorted(set(owners)),
        "artifact_id": artifact_id,
    }


def _artifact_ids_for_files(
    files: Mapping[str, bytes], manifest_rel: str
) -> dict[str, str]:
    _manifest, paths = _load_pack_artifacts(files, manifest_rel)
    return {rel: artifact_id for artifact_id, rel in paths.items()}


def _finalize_candidate(
    candidate: Path,
    files: dict[str, bytes],
    ledger: dict[str, object],
    *,
    kit_metadata: Mapping[str, tuple[str, Mapping[str, object]]],
    created_at: str,
) -> _PackSnapshot:
    files[KIT_MATERIALIZATIONS_PATH] = (
        json.dumps(ledger, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    _transactions.write_member(
        candidate, KIT_MATERIALIZATIONS_PATH, files[KIT_MATERIALIZATIONS_PATH]
    )
    _refresh_associated_artifacts(
        candidate, files, kit_metadata=kit_metadata, created_at=created_at
    )
    result, _scenarios = validation._validate_pack_for_author_ci(candidate)
    if not result.ok:
        raise KitError("composed pack failed static author validation")
    try:
        validate_pack_content_manifest(candidate)
    except PackDigestError as exc:
        codes = ",".join(sorted({item.code for item in exc.diagnostics}))
        raise KitError(
            "composed pack failed associated-artifact validation"
            + (f" ({codes})" if codes else "")
        ) from exc
    return _capture_pack(candidate)


def _changes(base: _PackSnapshot, successor: _PackSnapshot) -> tuple[str, ...]:
    old = {item.path: item.digest for item in base.files}
    new = {item.path: item.digest for item in successor.files}
    return tuple(
        rel for rel in sorted(set(old) | set(new)) if old.get(rel) != new.get(rel)
    )


def _blocked_proposal(
    *,
    operation: str,
    pack_root: str,
    base: _PackSnapshot,
    kit_id: str,
    kit_version: str,
    materialization_id: str,
    namespace: str,
    target_sdl: str,
    parameter_names: tuple[str, ...],
    topology: tuple[str, ...],
    dependencies: tuple[str, ...],
    diagnostics: list[validation.Diagnostic],
) -> KitProposal:
    return KitProposal(
        operation=operation,
        pack_root=pack_root,
        kit_id=kit_id,
        kit_version=kit_version,
        materialization_id=materialization_id,
        namespace=namespace,
        target_sdl=target_sdl,
        parameter_names=parameter_names,
        topology=topology,
        dependencies=dependencies,
        assumptions=("authoring-time only", "local immutable kit release"),
        lock_changes=(),
        changes=(),
        diagnostics=_ordered_diagnostics(diagnostics),
        _base_digest=base.digest,
        _successor=base.files,
        _successor_digest=base.digest,
    )


def _propose_add(
    pack_root: str | os.PathLike[str],
    release: KitRelease,
    source: KitSource,
    *,
    namespace: str,
    target_sdl: str,
    parameters: Mapping[str, object],
    _base: _PackSnapshot | None = None,
    _ledger: dict[str, object] | None = None,
    _extra_lock_targets: tuple[str, ...] = (),
) -> KitProposal:
    """Build an add proposal, optionally over an internal combined successor."""

    # Re-admit the exact release bytes at the proposal boundary. A frozen
    # dataclass does not make nested mapping values immutable, and front ends
    # must never be able to mutate an already-admitted release in memory.
    release = load_kit_release(release.root)
    canonical_root = os.path.realpath(os.fspath(pack_root))
    base = _base if _base is not None else _capture_pack(canonical_root)
    base_files = _snapshot_mapping(base)
    ledger = _ledger if _ledger is not None else _load_ledger(base_files)
    diagnostics: list[validation.Diagnostic] = []
    normalized, parameter_diagnostics = _normalize_parameters(release, parameters)
    diagnostics.extend(parameter_diagnostics)
    try:
        _validate_source(source)
        expected_release_root = os.path.realpath(
            Path(source.root, "kits", release.id, release.version)
        )
        valid_source = os.path.realpath(release.root) == expected_release_root
    except (KitError, TypeError, ValueError):
        valid_source = False
    if not valid_source:
        diagnostics.append(_diagnostic("kit.source.conflict"))
    if _NAMESPACE_RE.fullmatch(namespace) is None:
        diagnostics.append(_diagnostic("kit.namespace.invalid", field_path="namespace"))
    try:
        target_sdl = _pack_fs.normalize_relpath(target_sdl, error_type=KitError)
    except KitError:
        target_sdl = "sdl/invalid.sdl.yaml"
        diagnostics.append(_diagnostic("kit.path.invalid", field_path="target_sdl"))
    if target_sdl not in base_files:
        diagnostics.append(_diagnostic("kit.path.missing", target_sdl))
    if not (
        target_sdl.startswith("sdl/")
        and target_sdl.count("/") == 1
        and target_sdl.endswith(".sdl.yaml")
    ):
        diagnostics.append(_diagnostic("kit.path.invalid", target_sdl))
    materializations = list(ledger["materializations"])
    for item in materializations:
        diagnostics.extend(
            _owned_modification_diagnostics(base_files, ledger, str(item["id"]))
        )
    installed = {
        (str(item["kit_id"]), str(item["kit_version"]))
        for item in materializations
    }
    for item in materializations:
        if item["namespace"] == namespace or item["id"] == namespace:
            diagnostics.append(_diagnostic("kit.namespace.conflict", target_sdl))
            diagnostics.append(_diagnostic("kit.export.conflict", target_sdl))
        if item["kit_id"] == release.id and item["kit_version"] != release.version:
            diagnostics.append(_diagnostic("kit.version.conflict"))
    dependency_records = tuple(
        sorted(
            (
                {"id": str(item["id"]), "version": str(item["version"])}
                for item in release.document["prerequisites"]
                if item["kind"] == "kit"
            ),
            key=lambda item: (item["id"], item["version"]),
        )
    )
    dependencies = tuple(
        f"{item['id']}@{item['version']}" for item in dependency_records
    )
    for dependency in dependency_records:
        if (dependency["id"], dependency["version"]) not in installed:
            diagnostics.append(_diagnostic("kit.dependency.missing"))

    module_path = _module_destination(release, namespace)
    planned_paths = {module_path}
    for asset in release.document["assets"]:
        target = str(asset["target"])
        if not _safe_asset_target(target):
            diagnostics.append(_diagnostic("kit.asset-target.invalid", target))
        planned_paths.add(target)
        if asset["visibility"] == "restricted" and target.startswith(
            ("assets/content/", "assets/briefing/")
        ):
            diagnostics.append(_diagnostic("kit.visibility.conflict", target))
    for rel in planned_paths:
        if rel in base_files:
            diagnostics.append(_diagnostic("kit.path.conflict", rel))
    topology = tuple(
        f"{section}.{name}"
        for section, names in sorted(release.scenario.module.exports.items())
        for name in names
    )
    if diagnostics:
        return _blocked_proposal(
            operation="add",
            pack_root=canonical_root,
            base=base,
            kit_id=release.id,
            kit_version=release.version,
            materialization_id=namespace,
            namespace=namespace,
            target_sdl=target_sdl,
            parameter_names=tuple(sorted(normalized)),
            topology=topology,
            dependencies=dependencies,
            diagnostics=diagnostics,
        )

    staging_parent = Path(tempfile.mkdtemp(prefix=".kit-preview-", dir=Path(canonical_root).parent))
    candidate = staging_parent / Path(canonical_root).name
    try:
        _write_snapshot(candidate, base_files)
        files = dict(base_files)
        _ensure_pack_identity(
            candidate, files, created_at=str(release.document["released_at"])
        )
        release_metadata = _release_artifact_metadata(release)
        kit_metadata: dict[str, tuple[str, Mapping[str, object]]] = {}
        source_module = _module_document(release.document)
        module_body = _release_bytes(release, source_module)
        files[module_path] = module_body
        _transactions.write_member(candidate, module_path, module_body)
        module_artifact = next(
            artifact
            for artifact in release.associated_artifacts.artifacts.values()
            if _kit_uri_path(artifact.uri) == source_module
        )
        kit_metadata[module_path] = (
            f"kit-{namespace}-{module_artifact.artifact_id}",
            release_metadata[source_module],
        )
        for asset in release.document["assets"]:
            source_rel = str(asset["source"])
            target_rel = str(asset["target"])
            body = _release_bytes(release, source_rel)
            files[target_rel] = body
            _transactions.write_member(candidate, target_rel, body)
            kit_metadata[target_rel] = (
                f"kit-{namespace}-{asset['artifact_id']}",
                release_metadata[source_rel],
            )

        import_value = {
            "source": _local_source(target_sdl, module_path),
            "namespace": namespace,
            "version": release.version,
            "parameters": normalized,
            "digest": _digest_bytes(module_body),
        }
        files[target_sdl] = _edit_import(
            files[target_sdl], operation="add", import_value=import_value
        )
        _transactions.write_member(candidate, target_sdl, files[target_sdl])
        lock_path = _lock_path(target_sdl)
        lock_targets = tuple(sorted(set((target_sdl, *_extra_lock_targets))))
        lock_paths: list[str] = []
        for lock_target in lock_targets:
            resolved_lock_path = _lock_path(lock_target)
            files[resolved_lock_path] = _lock_bytes(candidate, lock_target)
            _transactions.write_member(
                candidate, resolved_lock_path, files[resolved_lock_path]
            )
            lock_paths.append(resolved_lock_path)

        _pack, manifest_rel = _pack_pointer(files)
        prior_manifest, prior_paths = _load_pack_artifacts(files, manifest_rel)
        artifact_for_path = {rel: key for key, rel in prior_paths.items()}
        unavailable = set(prior_manifest.artifacts)
        for rel in sorted(kit_metadata):
            preferred, metadata = kit_metadata[rel]
            artifact_id = _unique_artifact_id(preferred, unavailable, path=rel)
            unavailable.add(artifact_id)
            kit_metadata[rel] = (artifact_id, metadata)
            artifact_for_path[rel] = artifact_id
        generated_metadata = [
            (rel, "raes-lock", "application/json") for rel in lock_paths
        ]
        generated_metadata.append(
            (
                KIT_MATERIALIZATIONS_PATH,
                "kit-materializations",
                "application/json",
            )
        )
        for rel, preferred, media_type in generated_metadata:
            if rel in artifact_for_path:
                continue
            artifact_id = _unique_artifact_id(preferred, unavailable, path=rel)
            unavailable.add(artifact_id)
            artifact_for_path[rel] = artifact_id
            kit_metadata[rel] = (
                artifact_id,
                {
                    "source": "environment-pack-author",
                    "role": "configuration",
                    "media_type": media_type,
                    "created_at": str(release.document["released_at"]),
                    "sensitivity": "internal",
                },
            )

        new_materialization = {
            "id": namespace,
            "kit_id": release.id,
            "kit_version": release.version,
            "source": {"id": source.id, "revision": source.revision},
            "namespace": namespace,
            "target_sdl": target_sdl,
            "parameters": normalized,
            "dependencies": list(dependency_records),
            "module_path": module_path,
        }
        materializations.append(new_materialization)
        materializations.sort(key=lambda item: str(item["id"]))
        ownership: dict[str, tuple[list[str], str]] = {}
        for entry in ledger["files"]:
            ownership[str(entry["path"])] = (
                list(entry["owners"]), str(entry["artifact_id"])
            )
        ownership[module_path] = ([namespace], artifact_for_path[module_path])
        for asset in release.document["assets"]:
            target_rel = str(asset["target"])
            ownership[target_rel] = ([namespace], artifact_for_path[target_rel])
        for shared in (target_sdl, lock_path):
            owners, artifact_id = ownership.get(
                shared, (["pack-author"], artifact_for_path[shared])
            )
            ownership[shared] = ([*owners, namespace], artifact_id)
        ledger = {
            "schema_version": KIT_MATERIALIZATIONS_SCHEMA_VERSION,
            "materializations": materializations,
            "files": [
                _baseline_file(rel, owners, artifact_id, files)
                for rel, (owners, artifact_id) in sorted(ownership.items())
            ],
        }
        successor = _finalize_candidate(
            candidate,
            files,
            ledger,
            kit_metadata=kit_metadata,
            created_at=str(release.document["released_at"]),
        )
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    return KitProposal(
        operation="add",
        pack_root=canonical_root,
        kit_id=release.id,
        kit_version=release.version,
        materialization_id=namespace,
        namespace=namespace,
        target_sdl=target_sdl,
        parameter_names=tuple(sorted(normalized)),
        topology=topology,
        dependencies=dependencies,
        assumptions=("authoring-time only", "local immutable kit release"),
        lock_changes=(f"add:{namespace}",),
        changes=_changes(base, successor),
        diagnostics=(),
        _base_digest=base.digest,
        _successor=successor.files,
        _successor_digest=successor.digest,
    )


def propose_add(
    pack_root: str | os.PathLike[str],
    release: KitRelease,
    source: KitSource,
    *,
    namespace: str,
    target_sdl: str,
    parameters: Mapping[str, object],
) -> KitProposal:
    """Build an exact, side-effect-free add proposal over one pack snapshot."""

    return _propose_add(
        pack_root,
        release,
        source,
        namespace=namespace,
        target_sdl=target_sdl,
        parameters=parameters,
    )


def _owned_modification_diagnostics(
    files: Mapping[str, bytes], ledger: Mapping[str, object], materialization_id: str
) -> list[validation.Diagnostic]:
    diagnostics: list[validation.Diagnostic] = []
    for entry in ledger["files"]:
        if materialization_id not in entry["owners"]:
            continue
        rel = str(entry["path"])
        if rel not in files or _digest_bytes(files[rel]) != entry["baseline_digest"]:
            diagnostics.append(_diagnostic("kit.author-modification.conflict", rel))
    return diagnostics


def _removal_diagnostics(
    files: Mapping[str, bytes],
    ledger: Mapping[str, object],
    materialization: Mapping[str, object],
    *,
    successor_kit: tuple[str, str] | None,
) -> list[validation.Diagnostic]:
    materialization_id = str(materialization["id"])
    diagnostics = _owned_modification_diagnostics(
        files, ledger, materialization_id
    )
    removed_kit_id = str(materialization["kit_id"])
    for item in ledger["materializations"]:
        if item["id"] == materialization_id:
            continue
        for dependency in item["dependencies"]:
            required = (str(dependency["id"]), str(dependency["version"]))
            if required[0] == removed_kit_id and successor_kit != required:
                diagnostics.append(_diagnostic("kit.dependency.conflict"))
    return diagnostics


def _stage_removal(
    candidate: Path,
    base_files: Mapping[str, bytes],
    ledger: Mapping[str, object],
    materialization: Mapping[str, object],
) -> tuple[
    dict[str, bytes],
    list[Mapping[str, object]],
    dict[str, tuple[list[str], str]],
    str,
    str,
]:
    """Apply only removal edits; validation waits for the final successor."""

    files = dict(base_files)
    materialization_id = str(materialization["id"])
    target_sdl = str(materialization["target_sdl"])
    namespace = str(materialization["namespace"])
    lock_path = _lock_path(target_sdl)
    files[target_sdl] = _edit_import(
        files[target_sdl], operation="remove", namespace=namespace
    )
    _transactions.write_member(candidate, target_sdl, files[target_sdl])

    ownership: dict[str, tuple[list[str], str]] = {}
    for entry in ledger["files"]:
        rel = str(entry["path"])
        owners = [
            owner for owner in entry["owners"] if owner != materialization_id
        ]
        kit_owners = [owner for owner in owners if owner != "pack-author"]
        if not kit_owners:
            if rel not in {target_sdl, lock_path}:
                files.pop(rel, None)
                path = candidate.joinpath(*rel.split("/"))
                if path.exists():
                    path.unlink()
            continue
        ownership[rel] = (owners, str(entry["artifact_id"]))
    remaining = [
        item
        for item in ledger["materializations"]
        if item["id"] != materialization_id
    ]
    return files, remaining, ownership, target_sdl, namespace


def _ownership_ledger(
    files: Mapping[str, bytes],
    materializations: list[Mapping[str, object]],
    ownership: Mapping[str, tuple[list[str], str]],
) -> dict[str, object]:
    return {
        "schema_version": KIT_MATERIALIZATIONS_SCHEMA_VERSION,
        "materializations": list(materializations),
        "files": [
            _baseline_file(rel, owners, artifact_id, files)
            for rel, (owners, artifact_id) in sorted(ownership.items())
        ],
    }


def _propose_remove(
    pack_root: str | os.PathLike[str],
    *,
    materialization_id: str,
    successor_kit: tuple[str, str] | None,
) -> KitProposal:
    """Build one ownership-driven remove proposal without guessing filenames."""

    canonical_root = os.path.realpath(os.fspath(pack_root))
    base = _capture_pack(canonical_root)
    base_files = _snapshot_mapping(base)
    ledger = _load_ledger(base_files)
    matches = [
        item for item in ledger["materializations"] if item["id"] == materialization_id
    ]
    if len(matches) != 1:
        return _blocked_proposal(
            operation="remove",
            pack_root=canonical_root,
            base=base,
            kit_id="unknown",
            kit_version="unknown",
            materialization_id=materialization_id,
            namespace=materialization_id,
            target_sdl="",
            parameter_names=(),
            topology=(),
            dependencies=(),
            diagnostics=[_diagnostic("kit.materialization.missing")],
        )
    materialization = matches[0]
    diagnostics = _removal_diagnostics(
        base_files,
        ledger,
        materialization,
        successor_kit=successor_kit,
    )
    if diagnostics:
        return _blocked_proposal(
            operation="remove",
            pack_root=canonical_root,
            base=base,
            kit_id=str(materialization["kit_id"]),
            kit_version=str(materialization["kit_version"]),
            materialization_id=materialization_id,
            namespace=str(materialization["namespace"]),
            target_sdl=str(materialization["target_sdl"]),
            parameter_names=tuple(sorted(materialization["parameters"])),
            topology=(),
            dependencies=(),
            diagnostics=diagnostics,
        )

    staging_parent = Path(tempfile.mkdtemp(prefix=".kit-preview-", dir=Path(canonical_root).parent))
    candidate = staging_parent / Path(canonical_root).name
    try:
        _write_snapshot(candidate, base_files)
        files, remaining, ownership, target_sdl, namespace = _stage_removal(
            candidate, base_files, ledger, materialization
        )
        lock_path = _lock_path(target_sdl)
        files[lock_path] = _lock_bytes(candidate, target_sdl)
        _transactions.write_member(candidate, lock_path, files[lock_path])
        ledger = _ownership_ledger(files, remaining, ownership)
        successor = _finalize_candidate(
            candidate,
            files,
            ledger,
            kit_metadata={},
            created_at="2026-08-01T00:00:00Z",
        )
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    return KitProposal(
        operation="remove",
        pack_root=canonical_root,
        kit_id=str(materialization["kit_id"]),
        kit_version=str(materialization["kit_version"]),
        materialization_id=materialization_id,
        namespace=namespace,
        target_sdl=target_sdl,
        parameter_names=tuple(sorted(materialization["parameters"])),
        topology=(),
        dependencies=(),
        assumptions=("authoring-time only", "explicit ownership only"),
        lock_changes=(f"remove:{namespace}",),
        changes=_changes(base, successor),
        diagnostics=(),
        _base_digest=base.digest,
        _successor=successor.files,
        _successor_digest=successor.digest,
    )


def propose_remove(
    pack_root: str | os.PathLike[str], *, materialization_id: str
) -> KitProposal:
    """Build one ownership-driven remove proposal without guessing filenames."""

    return _propose_remove(
        pack_root,
        materialization_id=materialization_id,
        successor_kit=None,
    )


def _materialization(
    files: Mapping[str, bytes], materialization_id: str
) -> Mapping[str, object] | None:
    ledger = _load_ledger(files)
    matches = [
        item for item in ledger["materializations"] if item["id"] == materialization_id
    ]
    return matches[0] if len(matches) == 1 else None


def _replacement_proposal(
    pack_root: str | os.PathLike[str],
    release: KitRelease,
    source: KitSource,
    *,
    operation: str,
    materialization_id: str,
    namespace: str,
    target_sdl: str,
    parameters: Mapping[str, object],
    require_same_kit: bool,
) -> KitProposal:
    """Compose a remove successor and add successor without touching the pack."""

    release = load_kit_release(release.root)
    canonical_root = os.path.realpath(os.fspath(pack_root))
    original = _capture_pack(canonical_root)
    original_files = _snapshot_mapping(original)
    ledger = _load_ledger(original_files)
    matches = [
        item
        for item in ledger["materializations"]
        if item["id"] == materialization_id
    ]
    if len(matches) != 1:
        return _blocked_proposal(
            operation=operation,
            pack_root=canonical_root,
            base=original,
            kit_id=release.id,
            kit_version=release.version,
            materialization_id=materialization_id,
            namespace=namespace,
            target_sdl=target_sdl,
            parameter_names=tuple(sorted(str(key) for key in parameters)),
            topology=(),
            dependencies=(),
            diagnostics=[_diagnostic("kit.materialization.missing")],
        )
    current = matches[0]
    if require_same_kit and current["kit_id"] != release.id:
        return _blocked_proposal(
            operation=operation,
            pack_root=canonical_root,
            base=original,
            kit_id=release.id,
            kit_version=release.version,
            materialization_id=materialization_id,
            namespace=namespace,
            target_sdl=target_sdl,
            parameter_names=tuple(sorted(str(key) for key in parameters)),
            topology=(),
            dependencies=(),
            diagnostics=[_diagnostic("kit.update.identity-conflict")],
        )
    removal_diagnostics = _removal_diagnostics(
        original_files,
        ledger,
        current,
        successor_kit=(release.id, release.version),
    )
    if removal_diagnostics:
        return _blocked_proposal(
            operation=operation,
            pack_root=canonical_root,
            base=original,
            kit_id=release.id,
            kit_version=release.version,
            materialization_id=materialization_id,
            namespace=namespace,
            target_sdl=target_sdl,
            parameter_names=tuple(sorted(str(key) for key in parameters)),
            topology=(),
            dependencies=(),
            diagnostics=removal_diagnostics,
        )

    staging_parent = Path(
        tempfile.mkdtemp(prefix=".kit-chain-", dir=Path(canonical_root).parent)
    )
    candidate = staging_parent / Path(canonical_root).name
    try:
        _write_snapshot(candidate, original_files)
        files, remaining, ownership, removed_target, _removed_namespace = (
            _stage_removal(candidate, original_files, ledger, current)
        )
        raw_ledger = _ownership_ledger(files, remaining, ownership)
        files[KIT_MATERIALIZATIONS_PATH] = (
            json.dumps(raw_ledger, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        _transactions.write_member(
            candidate,
            KIT_MATERIALIZATIONS_PATH,
            files[KIT_MATERIALIZATIONS_PATH],
        )
        raw_snapshot = _capture_pack(candidate)
        addition = _propose_add(
            candidate,
            release,
            source,
            namespace=namespace,
            target_sdl=target_sdl,
            parameters=parameters,
            _base=raw_snapshot,
            _ledger=raw_ledger,
            _extra_lock_targets=(removed_target,),
        )
    finally:
        shutil.rmtree(staging_parent, ignore_errors=True)
    if addition.diagnostics:
        return _blocked_proposal(
            operation=operation,
            pack_root=canonical_root,
            base=original,
            kit_id=release.id,
            kit_version=release.version,
            materialization_id=materialization_id,
            namespace=namespace,
            target_sdl=target_sdl,
            parameter_names=addition.parameter_names,
            topology=addition.topology,
            dependencies=addition.dependencies,
            diagnostics=list(addition.diagnostics),
        )
    successor = _PackSnapshot(addition._successor, addition._successor_digest)
    return KitProposal(
        operation=operation,
        pack_root=canonical_root,
        kit_id=release.id,
        kit_version=release.version,
        materialization_id=namespace,
        namespace=namespace,
        target_sdl=target_sdl,
        parameter_names=addition.parameter_names,
        topology=addition.topology,
        dependencies=addition.dependencies,
        assumptions=("authoring-time only", "remove and add are one transaction"),
        lock_changes=(f"{operation}:{materialization_id}:{namespace}",),
        changes=_changes(original, successor),
        diagnostics=(),
        _base_digest=original.digest,
        _successor=successor.files,
        _successor_digest=successor.digest,
    )


def propose_update(
    pack_root: str | os.PathLike[str],
    release: KitRelease,
    source: KitSource,
    *,
    materialization_id: str,
    parameters: Mapping[str, object],
) -> KitProposal:
    """Update one kit version/parameter set as a complete successor."""

    snapshot = _capture_pack(pack_root)
    current = _materialization(_snapshot_mapping(snapshot), materialization_id)
    namespace = str(current["namespace"]) if current else materialization_id
    target_sdl = str(current["target_sdl"]) if current else ""
    return _replacement_proposal(
        pack_root,
        release,
        source,
        operation="update",
        materialization_id=materialization_id,
        namespace=namespace,
        target_sdl=target_sdl,
        parameters=parameters,
        require_same_kit=True,
    )


def propose_replace(
    pack_root: str | os.PathLike[str],
    release: KitRelease,
    source: KitSource,
    *,
    materialization_id: str,
    namespace: str,
    target_sdl: str,
    parameters: Mapping[str, object],
) -> KitProposal:
    """Replace one implementation choice through a remove-plus-add transaction."""

    return _replacement_proposal(
        pack_root,
        release,
        source,
        operation="replace",
        materialization_id=materialization_id,
        namespace=namespace,
        target_sdl=target_sdl,
        parameters=parameters,
        require_same_kit=False,
    )


def proposal_document(proposal: KitProposal) -> dict[str, object]:
    """Return the stable value-free projection used by human/JSON clients."""

    return {
        "version": KIT_PROPOSAL_VERSION,
        "operation": proposal.operation,
        "kit": {"id": proposal.kit_id, "version": proposal.kit_version},
        "materialization": proposal.materialization_id,
        "namespace": proposal.namespace,
        "target_sdl": proposal.target_sdl,
        "parameters": list(proposal.parameter_names),
        "topology": list(proposal.topology),
        "dependencies": list(proposal.dependencies),
        "assumptions": list(proposal.assumptions),
        "files": list(proposal.changes),
        "lock_changes": list(proposal.lock_changes),
        "diagnostics": [
            {
                "code": item.code,
                "path": item.path,
                "field_path": item.field_path,
            }
            for item in proposal.diagnostics
        ],
    }


def apply_proposal(proposal: KitProposal) -> str:
    """Validate and atomically exchange the exact proposed successor tree."""

    if proposal.diagnostics:
        raise KitError("kit proposal has blocking diagnostics")
    target = Path(proposal.pack_root)
    current = _capture_pack(target)
    if current.digest != proposal._base_digest:
        raise KitError("pack changed after the proposal was built")
    staging_parent = Path(tempfile.mkdtemp(prefix=".kit-commit-", dir=target.parent))
    staged = staging_parent / target.name
    exchanged = False
    cleanup_staging = True
    try:
        _write_snapshot(
            staged, {item.path: item.content for item in proposal._successor}
        )
        staged_snapshot = _capture_pack(staged)
        if staged_snapshot.digest != proposal._successor_digest:
            raise KitError("staged successor differs from the proposal")
        result, _scenarios = validation._validate_pack_for_author_ci(staged)
        if not result.ok:
            raise KitError("staged successor failed static author validation")
        validate_pack_content_manifest(staged)
        if _capture_pack(target).digest != proposal._base_digest:
            raise KitError("pack changed before the atomic commit")
        _transactions.exchange(staged, target)
        exchanged = True
        # The exchanged-out tree proves which exact source was replaced. If a
        # concurrent mutation landed after the last check, restore it atomically.
        if _capture_pack(staged).digest != proposal._base_digest:
            _transactions.exchange(staged, target)
            exchanged = False
            raise KitError("pack changed during the atomic commit")
    except (KitError, OSError, _transactions.TransactionError, PackDigestError) as exc:
        if exchanged:
            try:
                _transactions.exchange(staged, target)
            except (OSError, _transactions.TransactionError) as rollback_exc:
                cleanup_staging = False
                raise KitRecoveryError(staged) from rollback_exc
        raise KitError("kit proposal could not be committed atomically") from exc
    finally:
        if cleanup_staging:
            shutil.rmtree(staging_parent, ignore_errors=True)
    return str(target)


__all__ = [
    "KIT_CATALOG_SCHEMA_VERSION",
    "KIT_MATERIALIZATIONS_PATH",
    "KIT_MATERIALIZATIONS_SCHEMA_VERSION",
    "KIT_PROPOSAL_VERSION",
    "KIT_SCHEMA_VERSION",
    "KitError",
    "KitRecoveryError",
    "KitLimits",
    "KitProposal",
    "KitRelease",
    "KitSource",
    "apply_proposal",
    "build_kit_catalog",
    "catalog_json",
    "inspect_kit",
    "load_kit_release",
    "proposal_document",
    "propose_add",
    "propose_remove",
    "propose_replace",
    "propose_update",
    "search_catalog",
    "source_release",
    "validate_kit_catalog_document",
    "validate_kit_document",
    "validate_materializations_document",
]
