"""Static, in-process validation for one untrusted environment pack.

The public API deliberately excludes catalog discovery and author workflow
execution.  It validates only the version-matched pack contract and RAES SDL
documents, returning bounded diagnostics suitable for an ingest boundary.
"""

from __future__ import annotations

import os
import re
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
_PACK_MANIFEST = "pack.yaml"
_CHALLENGES_FILE = "challenges/challenges.yaml"
_FILESYSTEM_CHANGED = "filesystem.changed"


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


@dataclass
class ValidationResult(object):
    """The deterministic outcome of validating one environment pack."""

    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Whether validation completed without a contract error."""

        return not self.errors


class _Errors(object):
    """Bounded deterministic diagnostic collector."""

    def __init__(self, limits: PackValidationLimits) -> None:
        self._limits = limits
        self._items: list[str] = []

    def add(
        self, code: str, path: str | None = None, field_path: str | None = None
    ) -> None:
        if len(self._items) >= self._limits.max_errors:
            return
        message = code
        if path:
            message += f": {path}"
        if field_path:
            message += f":{field_path}"
        message = message[:self._limits.max_error_chars]
        self._items.append(message)

    def result(self) -> ValidationResult:
        return ValidationResult(sorted(set(self._items)))


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
) -> None:
    """Validate the canonical referenced provenance ledger."""

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
        return
    ledger = _load_yaml_member(root_fd, rel, limits, errors)
    if not isinstance(ledger, dict):
        if ledger is not None:
            errors.add("provenance.type", rel)
        return
    _add_schema_violations(
        errors, "provenance", rel, ledger, _trusted_schema(_PROVENANCE_SCHEMA)
    )
    ledger_pack = ledger.get("pack")
    ledger_name = ledger_pack.get("name") if isinstance(ledger_pack, dict) else None
    if ledger_name != pack.get("name"):
        errors.add("provenance.name-mismatch", rel, "pack.name")
    _validate_provenance_safety(ledger, rel, errors)
    _validate_provenance_review(ledger, rel, errors)


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
) -> None:
    """Validate an optional referenced compatibility manifest."""

    rel = _pointer(
        pack, "compatibility_manifest", "compatibility", inventory, errors, required=False
    )
    if rel is None:
        return
    manifest = _load_yaml_member(root_fd, rel, limits, errors)
    if not isinstance(manifest, dict):
        if manifest is not None:
            errors.add("compatibility.type", rel)
        return
    _add_schema_violations(
        errors, "compatibility", rel, manifest, _trusted_schema(_COMPATIBILITY_SCHEMA)
    )
    for field_path in _boundary_overlaps(manifest.get("artifact_boundaries")):
        errors.add("compatibility.boundary-overlap", rel, field_path)


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


def _validate_pack_core(
    pack_root: str | os.PathLike[str],
    active: PackValidationLimits,
    *,
    author_sdl: bool,
) -> tuple[ValidationResult, tuple[object, ...]]:
    """Run shared static validation and optionally retain parsed scenarios."""

    errors = _Errors(active)
    scenarios: tuple[object, ...] = ()
    opened = _open_validation_root(pack_root, errors)
    if opened is not None:
        root, root_fd = opened
        try:
            inventory = _safe_inventory(root_fd, active, errors)
            if inventory is not None:
                _validate_challenges(root_fd, inventory, active, errors)
                pack = _load_pack_manifest(root_fd, inventory, root, active, errors)
                if pack is not None:
                    _validate_provenance(root_fd, inventory, pack, active, errors)
                    _validate_compatibility(root_fd, inventory, pack, active, errors)
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
    return errors.result(), scenarios


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

    result, _scenarios = _validate_pack_core(
        pack_root, limits or PackValidationLimits(), author_sdl=False
    )
    return result


def _validate_pack_for_author_ci(
    pack_root: str | os.PathLike[str],
    *,
    limits: PackValidationLimits | None = None,
) -> tuple[ValidationResult, tuple[object, ...]]:
    """Run the shared static authority with author-controlled import resolution."""

    return _validate_pack_core(
        pack_root, limits or PackValidationLimits(), author_sdl=True
    )


__all__ = ["PackValidationLimits", "ValidationResult", "validate_pack"]
