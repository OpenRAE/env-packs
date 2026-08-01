"""Static, in-process validation for one untrusted environment pack.

The public API deliberately excludes catalog discovery and author workflow
execution.  It validates only the version-matched pack contract and RAES SDL
documents, returning bounded diagnostics suitable for an ingest boundary.
"""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from raes import SDLError, SDLParserLimits, parse_sdl, parse_sdl_file
from yaml.events import (
    AliasEvent,
    CollectionEndEvent,
    CollectionStartEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceStartEvent,
)

from . import _pack_fs

CONTENT_SAFETY_FLAGS = (
    "no_real_malware",
    "no_real_third_party_targets",
    "no_real_credentials",
    "no_sensitive_data",
    "offensive_tooling_boundary",
)
REQUIRED_REVIEW_GATES = (
    "licensing",
    "attribution",
    "sensitive-data",
    "offensive-tooling",
)

_RESOURCES = Path(__file__).with_name("resources")
_PROVENANCE_SCHEMA = _RESOURCES / "schemas" / "provenance.schema.yaml"
_COMPATIBILITY_SCHEMA = _RESOURCES / "schemas" / "pack-compatibility.schema.yaml"
_KIT_MATERIALIZATIONS_SCHEMA = (
    _RESOURCES / "schemas" / "kit-materializations.schema.yaml"
)
_PACK_MANIFEST = "pack.yaml"
_CHALLENGES_FILE = "challenges/challenges.yaml"
_KIT_MATERIALIZATIONS_FILE = "kit.materializations.json"
_FILESYSTEM_CHANGED = "filesystem.changed"
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


@dataclass(frozen=True)
class PackValidationLimits(object):
    """Resource limits for one :func:`validate_pack` call."""

    max_metadata_bytes: int = 1024 * 1024
    max_sdl_bytes: int = 8 * 1024 * 1024
    max_members: int = 1024
    max_errors: int = 100
    max_error_chars: int = 240
    max_yaml_nodes: int = 20_000
    max_yaml_aliases: int = 64
    max_yaml_depth: int = 64
    sdl: SDLParserLimits = field(default_factory=SDLParserLimits)

    def __post_init__(self) -> None:
        numeric = (
            self.max_metadata_bytes,
            self.max_sdl_bytes,
            self.max_members,
            self.max_errors,
            self.max_error_chars,
            self.max_yaml_nodes,
            self.max_yaml_aliases,
            self.max_yaml_depth,
        )
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in numeric
        ):
            raise ValueError("pack validation limits must be positive integers")


@dataclass(frozen=True)
class Diagnostic(object):
    """One canonical, bounded validation finding.

    ``code`` is a stable dotted identifier; ``path`` is a canonical
    pack-relative member and ``field_path`` a field pointer within it. Both are
    optional and never carry an authored value or an absolute path. ``message``
    is the bounded rendered string retained as the derived
    :attr:`ValidationResult.errors` compatibility view (ADR 0013, ADR 0031).
    """

    code: str
    path: str | None = None
    field_path: str | None = None
    message: str = ""


def _diagnostic_from_message(message: str) -> Diagnostic:
    """Parse a historical ``errors`` string back into a Diagnostic.

    Supports the legacy ``ValidationResult(errors=[...])`` construction: the
    string is ``code``, ``code: path``, or ``code: path:field``.
    """

    code, separator, rest = message.partition(": ")
    if not separator:
        return Diagnostic(code=message, message=message)
    path, _, field_path = rest.partition(":")
    return Diagnostic(
        code=code,
        path=path or None,
        field_path=field_path or None,
        message=message,
    )


class ValidationResult(object):
    """The deterministic outcome of validating one environment pack.

    ``diagnostics`` is the canonical, ordered, de-duplicated finding set. The
    historical ``errors`` string list and ``ok`` are derived views over it, so
    existing callers keep working while richer clients read structured records
    (ADR 0031).

    The exported constructor stays backward compatible: it accepts a tuple/list
    of :class:`Diagnostic` (canonical) *or* the historical list of error
    strings, positionally or as ``errors=``. Strings are normalized to
    :class:`Diagnostic` records so ``errors`` and ``ok`` behave as before.
    """

    __slots__ = ("_diagnostics",)

    def __init__(
        self,
        diagnostics: Iterable[object] = (),
        *,
        errors: Iterable[str] | None = None,
    ) -> None:
        source: Iterable[object] = errors if errors is not None else diagnostics
        self._diagnostics: tuple[Diagnostic, ...] = tuple(
            item if isinstance(item, Diagnostic) else _diagnostic_from_message(str(item))
            for item in source
        )

    @property
    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """The canonical, ordered finding set."""

        return self._diagnostics

    @property
    def errors(self) -> list[str]:
        """Bounded rendered strings — the historical compatibility view."""

        return [diagnostic.message for diagnostic in self._diagnostics]

    @property
    def ok(self) -> bool:
        """Whether validation completed without a contract error."""

        return not self._diagnostics

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ValidationResult)
            and other._diagnostics == self._diagnostics
        )

    def __hash__(self) -> int:
        return hash(self._diagnostics)

    def __repr__(self) -> str:
        return f"ValidationResult(diagnostics={self._diagnostics!r})"


class _Errors(object):
    """Bounded deterministic diagnostic collector."""

    def __init__(self, limits: PackValidationLimits) -> None:
        self._limits = limits
        self._items: list[Diagnostic] = []

    def add(
        self, code: str, path: str | None = None, field_path: str | None = None
    ) -> None:
        if len(self._items) >= self._limits.max_errors:
            return
        # Bound every structured component, not just the rendered message: a
        # schema-derived field path can embed an author-controlled key, and a
        # pack member path is foreign input. The whole diagnostic stays within
        # the configured char bound (ADR 0013).
        limit = self._limits.max_error_chars
        if path is not None:
            path = path[:limit]
        if field_path is not None:
            field_path = field_path[:limit]
        message = code
        if path:
            message += f": {path}"
        if field_path:
            message += f":{field_path}"
        message = message[:limit]
        self._items.append(
            Diagnostic(
                code=code, path=path, field_path=field_path, message=message
            )
        )

    def result(self) -> ValidationResult:
        unique: dict[str, Diagnostic] = {}
        for diagnostic in self._items:
            unique.setdefault(diagnostic.message, diagnostic)
        return ValidationResult(
            tuple(unique[message] for message in sorted(unique))
        )


class _DuplicateKey(yaml.YAMLError):
    """Strict YAML rejected a duplicate mapping key."""

    pass


class _StrictLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""

    def construct_mapping(
        self, node: yaml.nodes.MappingNode, deep: bool = False
    ) -> dict[object, object]:
        mapping: dict[object, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in mapping:
                    raise _DuplicateKey("duplicate mapping key")
            except TypeError as exc:
                raise yaml.YAMLError("unhashable mapping key") from exc
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


@dataclass(frozen=True)
class _SchemaViolation(object):
    """Body-free schema violation code and field path."""

    code: str
    path: str


_SCHEMA_TYPE_CHECKS = {
    "object": lambda value: isinstance(value, dict),
    "array": lambda value: isinstance(value, list),
    "string": lambda value: isinstance(value, str),
    "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
    "number": lambda value: isinstance(value, (int, float))
    and not isinstance(value, bool)
    and (not isinstance(value, float) or math.isfinite(value)),
    "boolean": lambda value: isinstance(value, bool),
    "null": lambda value: value is None,
}


def _resolve_ref(schema: dict[str, object], ref: str) -> dict[str, object] | None:
    """Resolve one local ``$defs`` reference in a trusted schema."""

    if not ref.startswith("#/$defs/"):
        return None
    target: object = schema
    for part in ref[2:].split("/"):
        if not isinstance(target, dict) or part not in target:
            return None
        target = target[part]
    return target if isinstance(target, dict) else None


def _expected_types(schema: dict[str, object]) -> tuple[str, ...] | None:
    """Return declared JSON types, or ``None`` when type is unconstrained."""

    expected = schema.get("type")
    if expected is None:
        return None
    if isinstance(expected, list):
        return tuple(str(item) for item in expected)
    return (str(expected),)


def _schema_value_violations(
    value: object, schema: dict[str, object], path: str
) -> list[_SchemaViolation]:
    """Return scalar constraint violations at one schema path."""

    violations: list[_SchemaViolation] = []
    if "const" in schema and value != schema["const"]:
        violations.append(_SchemaViolation("const", path))
    choices = schema.get("enum")
    if isinstance(choices, list) and value not in choices:
        violations.append(_SchemaViolation("enum", path))
    pattern = schema.get("pattern")
    if (
        isinstance(value, str)
        and pattern is not None
        and re.fullmatch(str(pattern), value) is None
    ):
        violations.append(_SchemaViolation("pattern", path))
    return violations


def _schema_object_violations(
    value: dict[object, object],
    schema: dict[str, object],
    root_schema: dict[str, object],
    path: str,
) -> list[_SchemaViolation]:
    """Return object-shape and recursive property violations."""

    violations: list[_SchemaViolation] = []
    properties = schema.get("properties")
    props = properties if isinstance(properties, dict) else {}
    required = schema.get("required")
    if isinstance(required, list):
        violations.extend(
            _SchemaViolation("required", f"{path}.{key}")
            for key in required
            if key not in value
        )
    if schema.get("additionalProperties") is False:
        violations.extend(
            _SchemaViolation("unknown", f"{path}.{key}")
            for key in value
            if key not in props
        )
    for key, child_schema in props.items():
        if key in value and isinstance(child_schema, dict):
            violations.extend(
                _schema_violations(
                    value[key], child_schema, root_schema, f"{path}.{key}"
                )
            )
    return violations


def _schema_array_violations(
    value: list[object],
    schema: dict[str, object],
    root_schema: dict[str, object],
    path: str,
) -> list[_SchemaViolation]:
    """Return array-size and recursive item violations."""

    violations: list[_SchemaViolation] = []
    minimum = schema.get("minItems")
    if isinstance(minimum, int) and len(value) < minimum:
        violations.append(_SchemaViolation("min-items", path))
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(value):
            violations.extend(
                _schema_violations(item, item_schema, root_schema, f"{path}[{index}]")
            )
    return violations


def _schema_violations(
    value: object,
    schema: dict[str, object],
    root_schema: dict[str, object],
    path: str = "$",
) -> list[_SchemaViolation]:
    """Validate one value against the repository's trusted schema subset."""

    ref = schema.get("$ref")
    if ref is not None:
        resolved = _resolve_ref(root_schema, str(ref))
        if resolved is None:
            violations = [_SchemaViolation("ref", path)]
        else:
            violations = _schema_violations(value, resolved, root_schema, path)
    else:
        expected = _expected_types(schema)
        type_mismatch = expected is not None and not any(
            _SCHEMA_TYPE_CHECKS.get(name, lambda _value: True)(value)
            for name in expected
        )
        if type_mismatch:
            violations = [_SchemaViolation("type", path)]
        else:
            violations = _schema_value_violations(value, schema, path)
            if isinstance(value, dict):
                violations.extend(
                    _schema_object_violations(value, schema, root_schema, path)
                )
            elif isinstance(value, list):
                violations.extend(
                    _schema_array_violations(value, schema, root_schema, path)
                )
    return violations


def _check_yaml_events(text: str, limits: PackValidationLimits) -> None:
    """Reject YAML streams that exceed structural expansion limits."""

    depth = aliases = nodes = 0
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, AliasEvent):
            aliases += 1
        if isinstance(event, (ScalarEvent, MappingStartEvent, SequenceStartEvent)):
            nodes += 1
        if isinstance(event, CollectionStartEvent):
            depth += 1
            if depth > limits.max_yaml_depth:
                raise yaml.YAMLError("YAML depth limit exceeded")
        elif isinstance(event, CollectionEndEvent):
            depth -= 1
        if (
            aliases > limits.max_yaml_aliases
            or nodes > limits.max_yaml_nodes
            or nodes * (aliases + 1) > limits.max_yaml_nodes
        ):
            raise yaml.YAMLError("YAML expansion limit exceeded")


def _load_yaml_member(
    root_fd: int,
    rel: str,
    limits: PackValidationLimits,
    errors: _Errors,
) -> object | None:
    """Load one bounded, strict YAML member through safe descriptors."""

    try:
        raw = _pack_fs.read_member_bytes(
            root_fd, rel, max_bytes=limits.max_metadata_bytes
        )
        text = raw.decode("utf-8", errors="strict")
        _check_yaml_events(text, limits)
        return yaml.load(text, Loader=_StrictLoader)
    except UnicodeDecodeError:
        errors.add("yaml.invalid-utf8", rel)
    except _DuplicateKey:
        errors.add("yaml.duplicate-key", rel)
    except yaml.YAMLError:
        errors.add("yaml.invalid", rel)
    except _pack_fs.PackFilesystemError as exc:
        if str(exc) == "pack metadata exceeds the validation limit":
            errors.add("resource.metadata-limit", rel)
        else:
            errors.add(_FILESYSTEM_CHANGED, rel)
    return None


def _trusted_schema(path: Path) -> dict[str, object]:
    """Load one packaged schema maintained with the installed validator."""

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("packaged validation schema is not an object")
    return value


def _strict_json_member(
    root_fd: int,
    rel: str,
    limits: PackValidationLimits,
    errors: _Errors,
) -> object | None:
    """Load one bounded JSON member without duplicate keys or non-finite numbers."""

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
        raw = _pack_fs.read_member_bytes(
            root_fd, rel, max_bytes=limits.max_metadata_bytes
        )
        return json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=object_pairs,
            parse_constant=invalid_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        errors.add("kit-materializations.invalid", rel)
    except _pack_fs.PackFilesystemError as exc:
        if str(exc) == "pack metadata exceeds the validation limit":
            errors.add("resource.metadata-limit", rel)
        else:
            errors.add(_FILESYSTEM_CHANGED, rel)
    return None


def _iter_mapping_values(value: object):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from _iter_mapping_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mapping_values(item)


def _secret_value(value: object) -> bool:
    return isinstance(value, str) and (
        _ENVIRONMENT_COORDINATE_RE.fullmatch(value) is not None
        or any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS)
    )


def _canonical_materialization_path(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return _pack_fs.normalize_relpath(value)
    except _pack_fs.PackFilesystemError:
        return None


def validate_kit_materializations_document(document: object) -> list[str]:
    """Validate the shared inert materialization and ownership ledger contract."""

    schema = _trusted_schema(_KIT_MATERIALIZATIONS_SCHEMA)
    violations = [
        f"schema.{item.code}:{item.path}"
        for item in _schema_violations(document, schema, schema)
    ]
    for key, value in _iter_mapping_values(document):
        normalized = str(key).casefold().replace("-", "_")
        if any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS):
            violations.append("secret-key:$")
        if isinstance(value, str) and any(
            pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS
        ):
            violations.append("secret-value:$")
    if not isinstance(document, dict):
        return sorted(set(violations))

    materializations = document.get("materializations")
    rows = materializations if isinstance(materializations, list) else []
    identities: set[str] = set()
    installed: set[tuple[str, str]] = set()
    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        identity = item.get("id")
        namespace = item.get("namespace")
        if not isinstance(identity, str) or identity in identities:
            violations.append(f"identity:$.materializations[{index}].id")
        else:
            identities.add(identity)
        if identity != namespace:
            violations.append(f"namespace:$.materializations[{index}].namespace")
        kit_id = item.get("kit_id")
        kit_version = item.get("kit_version")
        if isinstance(kit_id, str) and isinstance(kit_version, str):
            installed.add((kit_id, kit_version))
        for field in ("target_sdl", "module_path"):
            if _canonical_materialization_path(item.get(field)) is None:
                violations.append(f"path:$.materializations[{index}].{field}")
        parameters = item.get("parameters")
        if not isinstance(parameters, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, (str, int, float, bool))
            or isinstance(value, float) and not math.isfinite(value)
            or _secret_value(value)
            for key, value in (
                parameters.items() if isinstance(parameters, dict) else ()
            )
        ):
            violations.append(f"parameters:$.materializations[{index}].parameters")
        dependencies = item.get("dependencies")
        dependency_rows = dependencies if isinstance(dependencies, list) else []
        seen_dependencies: set[tuple[object, object]] = set()
        for dependency_index, dependency in enumerate(dependency_rows):
            if not isinstance(dependency, dict):
                continue
            pair = (dependency.get("id"), dependency.get("version"))
            if pair in seen_dependencies:
                violations.append(
                    f"dependency-duplicate:$.materializations[{index}]"
                    f".dependencies[{dependency_index}]"
                )
            seen_dependencies.add(pair)

    for index, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        dependencies = item.get("dependencies")
        for dependency_index, dependency in enumerate(
            dependencies if isinstance(dependencies, list) else []
        ):
            if not isinstance(dependency, dict):
                continue
            pair = (dependency.get("id"), dependency.get("version"))
            if pair not in installed:
                violations.append(
                    f"dependency-missing:$.materializations[{index}]"
                    f".dependencies[{dependency_index}]"
                )

    file_rows = document.get("files")
    files = file_rows if isinstance(file_rows, list) else []
    paths: set[str] = set()
    artifact_ids: set[str] = set()
    ownership: dict[str, set[str]] = {}
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            continue
        path = _canonical_materialization_path(item.get("path"))
        if path is None or path in paths:
            violations.append(f"file-path:$.files[{index}].path")
        else:
            paths.add(path)
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or artifact_id in artifact_ids:
            violations.append(f"artifact-id:$.files[{index}].artifact_id")
        else:
            artifact_ids.add(artifact_id)
        owners = item.get("owners")
        owner_rows = owners if isinstance(owners, list) else []
        if (
            not owner_rows
            or len(owner_rows) != len(set(map(str, owner_rows)))
            or any(
                not isinstance(owner, str)
                or owner != "pack-author" and owner not in identities
                for owner in owner_rows
            )
            or not any(owner != "pack-author" for owner in owner_rows)
        ):
            violations.append(f"owners:$.files[{index}].owners")
        if path is not None:
            ownership[path] = {
                owner for owner in owner_rows if isinstance(owner, str)
            }

    for index, item in enumerate(rows):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            continue
        identity = item["id"]
        for field in ("target_sdl", "module_path"):
            path = _canonical_materialization_path(item.get(field))
            if path is not None and identity not in ownership.get(path, set()):
                violations.append(f"ownership:$.materializations[{index}].{field}")
    return sorted(set(violations))


def _validate_kit_materializations(
    root_fd: int,
    inventory: frozenset[str],
    limits: PackValidationLimits,
    errors: _Errors,
) -> None:
    """Enforce an optional kit ledger in every canonical pack-validation path."""

    if _KIT_MATERIALIZATIONS_FILE not in inventory:
        return
    document = _strict_json_member(
        root_fd, _KIT_MATERIALIZATIONS_FILE, limits, errors
    )
    if document is None:
        return
    for violation in validate_kit_materializations_document(document):
        code, _separator, field_path = violation.partition(":")
        errors.add(
            f"kit-materializations.{code}",
            _KIT_MATERIALIZATIONS_FILE,
            field_path or None,
        )
    if not isinstance(document, dict):
        return
    for index, item in enumerate(
        document.get("materializations", [])
        if isinstance(document.get("materializations"), list)
        else []
    ):
        if not isinstance(item, dict):
            continue
        for field in ("target_sdl", "module_path"):
            path = _canonical_materialization_path(item.get(field))
            if path is not None and path not in inventory:
                errors.add(
                    "kit-materializations.member-missing",
                    _KIT_MATERIALIZATIONS_FILE,
                    f"materializations[{index}].{field}",
                )
    for index, item in enumerate(
        document.get("files", [])
        if isinstance(document.get("files"), list)
        else []
    ):
        if not isinstance(item, dict):
            continue
        path = _canonical_materialization_path(item.get("path"))
        if path is not None and path not in inventory:
            errors.add(
                "kit-materializations.member-missing",
                _KIT_MATERIALIZATIONS_FILE,
                f"files[{index}].path",
            )


def _add_schema_violations(
    errors: _Errors,
    prefix: str,
    rel: str,
    value: object,
    schema: dict[str, object],
) -> None:
    """Append stable diagnostics for schema-subset violations."""

    for violation in _schema_violations(value, schema, schema):
        errors.add(f"{prefix}.schema.{violation.code}", rel, violation.path)


def _pointer(
    pack: dict[str, object],
    key: str,
    label: str,
    inventory: frozenset[str],
    errors: _Errors,
    *,
    required: bool,
    expected_path: str | None = None,
) -> str | None:
    """Resolve and inventory-check one optional or required pack pointer."""

    resolved: str | None = None
    value = pack.get(key)
    if value is None:
        if required:
            errors.add(f"{label}.pointer.missing", _PACK_MANIFEST, key)
    elif not isinstance(value, str):
        errors.add(f"{label}.pointer.invalid", _PACK_MANIFEST, key)
    else:
        try:
            rel = _pack_fs.normalize_relpath(value)
        except _pack_fs.PackFilesystemError:
            errors.add(f"{label}.pointer.invalid", _PACK_MANIFEST, key)
        else:
            if expected_path is not None and rel != expected_path:
                errors.add(f"{label}.pointer.invalid", _PACK_MANIFEST, key)
            elif rel not in inventory:
                errors.add(f"{label}.missing", rel)
            else:
                resolved = rel
    return resolved


def _validate_provenance_safety(
    ledger: dict[str, object], rel: str, errors: _Errors
) -> None:
    """Require every canonical content-safety attestation."""

    safety = ledger.get("content_safety")
    for flag_name in CONTENT_SAFETY_FLAGS:
        if not isinstance(safety, dict) or safety.get(flag_name) is not True:
            errors.add("provenance.safety.required", rel, f"content_safety.{flag_name}")


def _review_gate_ids(ledger: dict[str, object]) -> set[str]:
    """Return valid review gate identifiers from one provenance ledger."""

    review = ledger.get("review")
    gates = review.get("gates") if isinstance(review, dict) else None
    if not isinstance(gates, list):
        return set()
    return {
        gate_id
        for row in gates
        if isinstance(row, dict)
        for gate_id in (row.get("gate_id"),)
        if isinstance(gate_id, str)
    }


def _validate_provenance_review(
    ledger: dict[str, object], rel: str, errors: _Errors
) -> None:
    """Require the canonical publication-review gates."""

    present = _review_gate_ids(ledger)
    for gate in REQUIRED_REVIEW_GATES:
        if gate not in present:
            errors.add("provenance.review-gate.missing", rel, f"review.gates.{gate}")


def _validate_provenance(
    root_fd: int,
    inventory: frozenset[str],
    pack: dict[str, object],
    limits: PackValidationLimits,
    errors: _Errors,
) -> dict[str, object] | None:
    """Validate the canonical referenced provenance ledger.

    Returns the parsed ledger when it loaded as a mapping so the shared static
    pass can retain it in the snapshot, or ``None`` when it is absent or
    unreadable. Returning the parsed document never widens the diagnostic
    surface; it only avoids a second read of the same bytes downstream.
    """

    rel = _pointer(
        pack,
        "provenance_ledger",
        "provenance",
        inventory,
        errors,
        required=True,
        expected_path="docs/provenance-ledger.yaml",
    )
    if rel is None:
        return None
    ledger = _load_yaml_member(root_fd, rel, limits, errors)
    if not isinstance(ledger, dict):
        if ledger is not None:
            errors.add("provenance.type", rel)
        return None
    _add_schema_violations(
        errors, "provenance", rel, ledger, _trusted_schema(_PROVENANCE_SCHEMA)
    )
    ledger_pack = ledger.get("pack")
    ledger_name = ledger_pack.get("name") if isinstance(ledger_pack, dict) else None
    if ledger_name != pack.get("name"):
        errors.add("provenance.name-mismatch", rel, "pack.name")
    _validate_provenance_safety(ledger, rel, errors)
    _validate_provenance_review(ledger, rel, errors)
    return ledger


# Visibility-boundary overlap is a relational ingest invariant JSON Schema cannot
# express (ADR 0013): every participant_visible path must be disjoint from every
# restricted non-participant root, so hidden-tier content cannot be declared into
# a participant export. Restricted roots are the operator_only and oracle_only
# groups, plus any row exported as operator/oracle/private.
_PARTICIPANT_BOUNDARY_GROUP = "participant_visible"
_RESTRICTED_BOUNDARY_GROUPS = frozenset({"operator_only", "oracle_only"})
_RESTRICTED_BOUNDARY_EXPORTS = frozenset({"operator", "oracle", "private"})


def _boundary_path_key(path: object) -> tuple[str, ...] | None:
    """Return canonical path components of a boundary path, or None.

    ``docs`` and ``docs/`` yield the same key; ``.`` and empty segments are
    dropped. Empty, root, or parent-escaping paths return ``None`` — those are
    handled by the schema and path-containment gates, not this relational check.
    Comparison is component-wise, so ``docs`` contains ``docs/x`` but not
    ``docs2``. Both ``/`` and ``\\`` split into components: canonical manifest
    paths are forward-slash only (``_pack_fs.normalize_relpath`` rejects a
    backslash), but a Windows filesystem treats ``\\`` as a separator, so a
    row like ``docs\\secret.yaml`` must fail closed as a descendant of ``docs``
    rather than be read as one opaque component.
    """

    if not isinstance(path, str):
        return None
    parts = tuple(part for part in re.split(r"[\\/]+", path) if part not in ("", "."))
    if not parts or ".." in parts:
        return None
    return parts


def _is_restricted_boundary(group: str, row: dict[str, object]) -> bool:
    """Whether one boundary row is a restricted (operator/oracle/private) root."""

    return (
        group in _RESTRICTED_BOUNDARY_GROUPS
        or row.get("export") in _RESTRICTED_BOUNDARY_EXPORTS
    )


def _restricted_boundary_keys(boundaries: dict[str, object]) -> set[tuple[str, ...]]:
    """Path keys of every restricted (operator/oracle/private) boundary root."""

    keys: set[tuple[str, ...]] = set()
    for group, rows in boundaries.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and _is_restricted_boundary(group, row):
                key = _boundary_path_key(row.get("path"))
                if key is not None:
                    keys.add(key)
    return keys


def _key_overlaps_restricted(
    key: tuple[str, ...],
    restricted: set[tuple[str, ...]],
    restricted_prefixes: set[tuple[str, ...]],
) -> bool:
    """Whether a participant key equals, contains, or sits under a restricted root.

    ``key in restricted`` is an identical path; ``key in restricted_prefixes``
    means the participant path is an ancestor of (contains) a restricted root; a
    restricted root among the participant key's own prefixes means it sits under
    one. Any of the three would stage a restricted root into a participant export.
    """

    if key in restricted or key in restricted_prefixes:
        return True
    return any(key[:cut] in restricted for cut in range(1, len(key)))


def _boundary_overlaps(boundaries: object) -> list[str]:
    """Return participant field paths that overlap a restricted root.

    Pure and malformed-tolerant: no filesystem access, no exceptions on bad
    rows, and never a restricted (hidden) path value — only the participant
    declaration's field location, which is participant-visible by definition.
    Restricted roots are pre-hashed so the scan is linear in total path
    components, not a participant×restricted Cartesian product on an adversarial
    manifest.
    """

    if not isinstance(boundaries, dict):
        return []
    restricted = _restricted_boundary_keys(boundaries)
    restricted_prefixes = {
        key[:cut] for key in restricted for cut in range(1, len(key))
    }
    participant_rows = boundaries.get(_PARTICIPANT_BOUNDARY_GROUP)
    rows = participant_rows if isinstance(participant_rows, list) else []
    overlaps: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        key = _boundary_path_key(row.get("path"))
        if key is not None and _key_overlaps_restricted(
            key, restricted, restricted_prefixes
        ):
            overlaps.append(
                f"artifact_boundaries.{_PARTICIPANT_BOUNDARY_GROUP}[{index}].path"
            )
    return overlaps


def _validate_compatibility(
    root_fd: int,
    inventory: frozenset[str],
    pack: dict[str, object],
    limits: PackValidationLimits,
    errors: _Errors,
) -> dict[str, object] | None:
    """Validate an optional referenced compatibility manifest.

    Returns the parsed manifest when it loaded as a mapping so the shared static
    pass can retain it in the snapshot, or ``None`` when it is absent or
    unreadable.
    """

    rel = _pointer(
        pack, "compatibility_manifest", "compatibility", inventory, errors, required=False
    )
    if rel is None:
        return None
    manifest = _load_yaml_member(root_fd, rel, limits, errors)
    if not isinstance(manifest, dict):
        if manifest is not None:
            errors.add("compatibility.type", rel)
        return None
    _add_schema_violations(
        errors, "compatibility", rel, manifest, _trusted_schema(_COMPATIBILITY_SCHEMA)
    )
    for field_path in _boundary_overlaps(manifest.get("artifact_boundaries")):
        errors.add("compatibility.boundary-overlap", rel, field_path)
    _validate_shipped_assets_exist(manifest, rel, inventory, errors)
    return manifest


def _validate_shipped_assets_exist(
    manifest: dict[str, object],
    rel: str,
    inventory: frozenset[str],
    errors: _Errors,
) -> None:
    """Referenced-member existence for declared-shipped compatibility assets.

    A ``shipped`` asset row that names a member absent from the descriptor-
    anchored inventory is a cross-authority defect (ADR 0032): the compatibility
    manifest asserts content the pack does not contain. This join lives in the
    shared static authority so ``validate_pack`` and any downstream projection
    agree — a projection must never silently drop such a declaration. ``planned``
    and ``not_shipped`` assets legitimately need not exist yet.
    """

    assets = manifest.get("assets")
    for index, asset in enumerate(assets if isinstance(assets, list) else []):
        if not isinstance(asset, dict) or asset.get("status") != "shipped":
            continue
        path = asset.get("path")
        if not isinstance(path, str):
            continue
        try:
            member = _pack_fs.normalize_relpath(path)
        except _pack_fs.PackFilesystemError:
            member = None
        if member is None or member not in inventory:
            errors.add("compatibility.asset.missing", rel, f"assets[{index}].path")


def _validate_challenges(
    root_fd: int,
    inventory: frozenset[str],
    limits: PackValidationLimits,
    errors: _Errors,
) -> None:
    """Reject the removed pack-domain ``challenges[].category`` field.

    Challenge presentation grouping is an adapter-local (CTFd) concern, not pack
    semantics; a scenario's tactic/technique classification lives in RAES SDL
    behaviour specifications, governed by RAES concept-authority, never a pack
    field (ADR 0014). The guard fires only on the exact structured path
    ``challenges[].category`` and never scans prose.
    """

    if _CHALLENGES_FILE not in inventory:
        return
    document = _load_yaml_member(root_fd, _CHALLENGES_FILE, limits, errors)
    if not isinstance(document, dict):
        return
    challenges = document.get("challenges")
    if not isinstance(challenges, list):
        return
    for index, entry in enumerate(challenges):
        if isinstance(entry, dict) and "category" in entry:
            errors.add(
                "challenges.category.forbidden",
                _CHALLENGES_FILE,
                f"challenges[{index}].category",
            )


def _open_validation_root(
    pack_root: str | os.PathLike[str], errors: _Errors
) -> tuple[str, int] | None:
    """Open one pack root or record a stable invalid-root diagnostic."""

    opened: tuple[str, int] | None = None
    try:
        opened = _pack_fs.open_root(pack_root)
    except _pack_fs.PackFilesystemError:
        errors.add("filesystem.invalid-root")
    return opened


def _safe_inventory(
    root_fd: int, limits: PackValidationLimits, errors: _Errors
) -> frozenset[str] | None:
    """Inventory one pack or record its bounded filesystem failure."""

    inventory: frozenset[str] | None = None
    try:
        inventory = frozenset(
            _pack_fs.inventory(root_fd, max_members=limits.max_members)
        )
    except _pack_fs.PackFilesystemError as exc:
        if str(exc) == "pack member count exceeds the validation limit":
            errors.add("resource.member-limit")
        else:
            errors.add("filesystem.unsafe-member")
    return inventory


def _validate_pack_identity(
    pack: dict[str, object], root: str, errors: _Errors
) -> None:
    """Validate the manifest's required identity fields and directory name."""

    for key in ("name", "title", "version"):
        value = pack.get(key)
        if not isinstance(value, str) or not value:
            errors.add("pack.identity.missing", _PACK_MANIFEST, key)
    if pack.get("name") != os.path.basename(root):
        errors.add("pack.identity.name-mismatch", _PACK_MANIFEST, "name")


def _load_pack_manifest(
    root_fd: int,
    inventory: frozenset[str],
    root: str,
    limits: PackValidationLimits,
    errors: _Errors,
) -> dict[str, object] | None:
    """Load and identity-check the required pack manifest."""

    manifest: dict[str, object] | None = None
    if _PACK_MANIFEST not in inventory:
        errors.add("pack.missing", _PACK_MANIFEST)
    else:
        loaded = _load_yaml_member(root_fd, _PACK_MANIFEST, limits, errors)
        if isinstance(loaded, dict):
            manifest = loaded
            _validate_pack_identity(manifest, root, errors)
        elif loaded is not None:
            errors.add("pack.type", _PACK_MANIFEST)
    return manifest


def _direct_sdl_documents(inventory: frozenset[str]) -> list[str]:
    """Return sorted, direct SDL documents from the safe inventory."""

    return sorted(
        rel
        for rel in inventory
        if rel.startswith("sdl/")
        and rel.count("/") == 1
        and rel.endswith(".sdl.yaml")
    )


def _parse_sdl_document(
    root_fd: int,
    root: str,
    rel: str,
    limits: PackValidationLimits,
    errors: _Errors,
    *,
    author_sdl: bool,
) -> object | None:
    """Parse one bounded SDL document through the selected RAES entry point."""

    scenario: object | None = None
    try:
        raw = _pack_fs.read_member_bytes(
            root_fd, rel, max_bytes=limits.max_sdl_bytes
        )
        text = raw.decode("utf-8", errors="strict")
        if author_sdl:
            scenario = parse_sdl_file(Path(root, *rel.split("/")), limits=limits.sdl)
        else:
            scenario = parse_sdl(text, limits=limits.sdl)
    except UnicodeDecodeError:
        errors.add("sdl.invalid-utf8", rel)
    except SDLError as exc:
        if not author_sdl and "imports require file-backed parsing" in str(exc):
            errors.add("sdl.imports-denied", rel)
        else:
            errors.add("sdl.invalid", rel)
    except OSError:
        errors.add(_FILESYSTEM_CHANGED, rel)
    except _pack_fs.PackFilesystemError as exc:
        if str(exc) == "pack metadata exceeds the validation limit":
            errors.add("resource.sdl-limit", rel)
        else:
            errors.add(_FILESYSTEM_CHANGED, rel)
    return scenario


def _validate_sdl_documents(
    root_fd: int,
    root: str,
    inventory: frozenset[str],
    limits: PackValidationLimits,
    errors: _Errors,
    *,
    author_sdl: bool,
) -> tuple[object, ...]:
    """Validate every direct SDL document and retain successful scenarios."""

    documents = _direct_sdl_documents(inventory)
    if not documents:
        errors.add("sdl.missing", "sdl")
    parsed: list[object] = []
    for rel in documents:
        scenario = _parse_sdl_document(
            root_fd, root, rel, limits, errors, author_sdl=author_sdl
        )
        if scenario is not None:
            parsed.append(scenario)
    return tuple(parsed)


def _load_optional_publication(
    root_fd: int,
    inventory: frozenset[str],
    pack: dict[str, object],
    limits: PackValidationLimits,
) -> dict[str, object] | None:
    """Read an optional publication-supply document for the snapshot.

    Publication clearance is validated by ``publication.validate_publication_document``
    against the parsed profile, so the shared pass only captures the bytes here
    (through the same descriptor-anchored, bounded reader every other member
    uses) rather than reopening the tree later. Any load problem yields ``None``;
    it never widens ``validate_pack``'s diagnostic surface.
    """

    value = pack.get("publication_supply")
    if not isinstance(value, str):
        return None
    rel = _safe_relpath(value)
    if rel is None or rel not in inventory:
        return None
    loaded = _load_yaml_member(root_fd, rel, limits, _Errors(limits))
    return loaded if isinstance(loaded, dict) else None


def _safe_relpath(value: str) -> str | None:
    """Normalize a pack-relative pointer, or ``None`` when it is unsafe."""

    try:
        return _pack_fs.normalize_relpath(value)
    except _pack_fs.PackFilesystemError:
        return None


def _validate_publication_identity(
    publication: dict[str, object] | None,
    pack: dict[str, object],
    rel: str,
    errors: _Errors,
) -> None:
    """Identity agreement between the publication profile and the manifest.

    A publication profile whose declared release identity names a *different*
    pack lets one pack's release identity and availability be attached to
    another's card. This relational join lives in the shared static authority
    (ADR 0032) so a mismatch fails ``validate_pack`` rather than being quietly
    downgraded in a projection. Absent identity fields are a publication-schema
    concern, not a mismatch, so only a present-and-differing value is flagged.
    """

    if not isinstance(publication, dict):
        return
    release = publication.get("release")
    release_pack = release.get("pack") if isinstance(release, dict) else None
    if not isinstance(release_pack, dict):
        return
    name = release_pack.get("name")
    version = release_pack.get("version")
    if (name is not None and name != pack.get("name")) or (
        version is not None and version != pack.get("version")
    ):
        errors.add("publication.identity-mismatch", rel, "release.pack")


@dataclass(frozen=True)
class _PackSnapshot(object):
    """The parsed, bounded result of one shared static-validation pass.

    Internal only: an extension of :func:`_validate_pack_core`, not a public
    pack model. It retains exactly the documents the pass already parsed so a
    downstream projection (the catalog read model, ADR 0032) consumes one
    validated snapshot instead of reopening an untrusted tree through a second
    loader. Every document is a plain parsed value; no filesystem handle
    escapes the pass.
    """

    root: str | None
    inventory: frozenset[str]
    manifest: dict[str, object] | None
    provenance: dict[str, object] | None
    compatibility: dict[str, object] | None
    # ``publication_declared`` records whether pack.yaml declared a
    # publication-supply pointer at all. It lets a projection distinguish an
    # *absent* authority (no pointer) from a *present but unreadable* one
    # (pointer declared, but the document failed to load) — two states a bare
    # ``publication is None`` would otherwise collapse (ADR 0032).
    publication_declared: bool
    publication: dict[str, object] | None
    scenarios: tuple[object, ...]


def _validate_pack_core(
    pack_root: str | os.PathLike[str],
    active: PackValidationLimits,
    *,
    author_sdl: bool,
) -> tuple[ValidationResult, _PackSnapshot]:
    """Run shared static validation and retain the parsed snapshot."""

    errors = _Errors(active)
    scenarios: tuple[object, ...] = ()
    root_out: str | None = None
    inventory_out: frozenset[str] = frozenset()
    manifest: dict[str, object] | None = None
    provenance: dict[str, object] | None = None
    compatibility: dict[str, object] | None = None
    publication_declared = False
    publication: dict[str, object] | None = None
    opened = _open_validation_root(pack_root, errors)
    if opened is not None:
        root, root_fd = opened
        root_out = root
        try:
            inventory = _safe_inventory(root_fd, active, errors)
            if inventory is not None:
                inventory_out = inventory
                _validate_challenges(root_fd, inventory, active, errors)
                _validate_kit_materializations(root_fd, inventory, active, errors)
                pack = _load_pack_manifest(root_fd, inventory, root, active, errors)
                if pack is not None:
                    manifest = pack
                    provenance = _validate_provenance(
                        root_fd, inventory, pack, active, errors
                    )
                    compatibility = _validate_compatibility(
                        root_fd, inventory, pack, active, errors
                    )
                    publication_pointer = pack.get("publication_supply")
                    publication_declared = isinstance(publication_pointer, str)
                    publication = _load_optional_publication(
                        root_fd, inventory, pack, active
                    )
                    _validate_publication_identity(
                        publication,
                        pack,
                        publication_pointer
                        if isinstance(publication_pointer, str)
                        else _PACK_MANIFEST,
                        errors,
                    )
                    scenarios = _validate_sdl_documents(
                        root_fd,
                        root,
                        inventory,
                        active,
                        errors,
                        author_sdl=author_sdl,
                    )
        finally:
            os.close(root_fd)
    snapshot = _PackSnapshot(
        root=root_out,
        inventory=inventory_out,
        manifest=manifest,
        provenance=provenance,
        compatibility=compatibility,
        publication_declared=publication_declared,
        publication=publication,
        scenarios=scenarios,
    )
    return errors.result(), snapshot


def validate_pack(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
) -> ValidationResult:
    """Validate one pack directory against the static consumer contract.

    Invalid foreign input is returned as stable, bounded error codes. Unexpected
    package defects still raise normally so they cannot be mislabeled as input
    failures.
    """

    result, _snapshot = _validate_pack_core(
        pack_root, limits or PackValidationLimits(), author_sdl=False
    )
    return result


def _validate_pack_for_author_ci(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
) -> tuple[ValidationResult, tuple[object, ...]]:
    """Run the shared static authority with author-controlled import resolution."""

    result, snapshot = _validate_pack_core(
        pack_root, limits or PackValidationLimits(), author_sdl=True
    )
    return result, snapshot.scenarios


def _validate_pack_snapshot(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
    author_sdl: bool = False,
) -> tuple[ValidationResult, _PackSnapshot]:
    """Run the shared static authority and return its parsed snapshot.

    The catalog read model (ADR 0032) consumes this so it never reopens an
    untrusted tree after validation. ``author_sdl`` stays ``False`` for the
    untrusted-ingest default: SDL imports remain denied exactly as in
    :func:`validate_pack`.
    """

    return _validate_pack_core(
        pack_root, limits or PackValidationLimits(), author_sdl=author_sdl
    )


__all__ = [
    "Diagnostic",
    "PackValidationLimits",
    "ValidationResult",
    "validate_kit_materializations_document",
    "validate_pack",
]
