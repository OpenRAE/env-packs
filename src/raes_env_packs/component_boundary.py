#!/usr/bin/env python3
"""Pack-controlled component boundary — the accountable SBOM inventory input.

ADR 0037 requires a released pack to expose a standards-backed component
inventory without letting a shipped or pinned component disappear behind an
author-declared boundary. Two forces meet here:

* Machine-derivable components -- the exact RAES ``Source`` artifacts the SDL
  pins, every ``raes.lock.json`` module, and each materialized-kit
  ``component_inventory`` row recovered through the *immutable* kit source and
  revision named in ``kit.materializations.json`` -- are **auto-included**. An
  author declaration can never omit them, so a falsely complete SBOM is
  structurally impossible for the parts a tool can prove.
* The author declares the rest of the pack-controlled boundary through the
  existing ``publication_supply`` input (extended, not a second ``sbom.yaml`` or
  component graph): external, runtime-selected, opaque, and unresolved scope, any
  shipped software an asset carries, and enrichment (license, provenance) of the
  auto-derived components.

Reconciliation validates the authored declaration as a closed schema-backed
contract and refuses a declaration that *contradicts* an incumbent (a digest
that disagrees with the lock or the SDL), that claims a shipped/pinned component
without the finest identity, or that references an associated artifact the pack
does not contain. Kit inventories that cannot be recovered through their
immutable source are reported as authority-unavailable, never inferred from
filenames. This module defines no second pack identity, module lock, trust
record, or SBOM format; it only decides what :mod:`sbom` renders.
"""

from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

import yaml
from raes.module_registry import load_lockfile

from . import _pack_fs
from . import digest as digest_module
from . import kits as kits_module
from . import publication as publication_module
from . import validation

SUPPLY_SCHEMA_VERSION = "environment-pack-publication-supply/v1"

_CANONICAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_BARE_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_CONTROLLED_SCOPES = frozenset({"shipped", "pinned"})
_KIT_MATERIALIZATIONS = "kit.materializations.json"
_SDL_LOCK_DIR = "sdl"
_CONTAINER_MEDIA_HINTS = ("docker", "oci.image", "container")

# Maps ``(source_id, revision, kit_id, kit_version)`` to an immutable staged
# catalog root that contains ``kits/``, or ``None`` when no such root can be
# supplied for that materialization.
KitSourceResolver = Callable[[str, str, str, str], str | None]


class ComponentBoundaryError(ValueError):
    """One bounded component-boundary input failure (payload-free message)."""


@dataclasses.dataclass(frozen=True)
class Component(object):
    """One software component the release SBOM inventories.

    ``digest`` is a canonical ``sha256:`` value when the component is content
    addressable. ``upstream_sbom`` is the associated-artifact id of an
    independently scoped upstream SBOM this component is documented by; that
    document is preserved and referenced, never flattened into the generated
    pack SBOM.
    """

    id: str
    scope: str
    kind: str
    authority: str
    ref: str
    version: str | None
    digest: str | None
    license: str | None
    provenance: str | None
    upstream_sbom: str | None
    description: str


def publication_supply_schema_path() -> Path:
    """Path to the packaged publication-supply schema."""

    return (
        Path(__file__).with_name("resources")
        / "schemas"
        / "publication-supply.schema.yaml"
    )


def _canonical_digest(value: object) -> str | None:
    """Return a canonical ``sha256:`` digest for a lock/RAES value, or ``None``.

    RAES records may spell a content digest either canonically or as bare hex;
    normalise both to one comparable form and drop anything else rather than
    fabricating a shape a consumer would treat as evidence.
    """

    result: str | None = None
    if isinstance(value, str):
        if _CANONICAL_DIGEST_RE.fullmatch(value):
            result = value
        elif _BARE_SHA256_RE.fullmatch(value):
            result = f"sha256:{value}"
    return result


def _slug(prefix: str, ref: str, used: set[str]) -> str:
    """Return a schema-safe, unique component id derived from an incumbent ref."""

    base = f"{prefix}-{_ID_SANITIZE_RE.sub('-', ref).strip('-') or 'component'}"
    candidate = base
    index = 1
    while candidate in used:
        index += 1
        candidate = f"{base}-{index}"
    used.add(candidate)
    return candidate


def _image_kind(media_type: object) -> str:
    """Map a RAES artifact media type to a component kind."""

    if isinstance(media_type, str) and any(
        hint in media_type for hint in _CONTAINER_MEDIA_HINTS
    ):
        return "container-image"
    return "other"


# --------------------------------------------------------------------------- #
# Authored declaration (closed schema-backed contract)
# --------------------------------------------------------------------------- #
def validate_publication_supply_document(
    document: object,
) -> tuple[list[validation.Diagnostic], tuple[Component, ...]]:
    """Validate the publication-supply document as a closed schema-backed contract.

    Returns ``(diagnostics, declared_components)``. Schema shape and every
    semantic rule the closed JSON subset cannot express -- canonical digests,
    finest identity on controlled scopes, honest authority use -- are enforced
    here so a release or consumer gate refuses a malformed declaration instead of
    ignoring it.
    """

    schema = validation._trusted_schema(publication_supply_schema_path())
    diagnostics = [
        validation.Diagnostic(f"publication-supply.schema.{item.code}", path=item.path)
        for item in validation._schema_violations(document, schema, schema)
    ]
    if diagnostics or not isinstance(document, dict):
        return diagnostics, ()

    components, row_diagnostics = _declared_components(document.get("component_boundary"))
    diagnostics.extend(row_diagnostics)
    return diagnostics, tuple(components)


def _declared_components(
    rows: object,
) -> tuple[list[Component], list[validation.Diagnostic]]:
    """Project and semantically validate each authored ``component_boundary`` row.

    Returns ``(components, diagnostics)``. Every well-formed row becomes a
    :class:`Component`, and every semantic rule the closed JSON subset cannot
    express is checked against a shared id set so a duplicate id or a controlled
    scope missing its digest is refused. A non-list ``rows`` yields no components.
    """

    components: list[Component] = []
    diagnostics: list[validation.Diagnostic] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows if isinstance(rows, list) else ()):
        if not isinstance(row, dict):
            continue
        component = _component_from_row(row)
        components.append(component)
        diagnostics.extend(
            _component_semantics(component, f"$.component_boundary[{index}]", seen_ids)
        )
    return components, diagnostics


def _component_from_row(row: Mapping[str, object]) -> Component:
    """Project one validated boundary row into a :class:`Component`."""

    def text(key: str) -> str:
        """Return the row's string value for ``key``, or an empty string."""
        value = row.get(key)
        return value if isinstance(value, str) else ""

    def optional(key: str) -> str | None:
        """Return the row's string value for ``key``, or ``None`` when absent."""
        value = row.get(key)
        return value if isinstance(value, str) else None

    return Component(
        id=text("id"),
        scope=text("scope"),
        kind=text("kind"),
        authority=text("authority"),
        ref=text("ref"),
        version=optional("version"),
        digest=optional("digest"),
        license=optional("license"),
        provenance=optional("provenance"),
        upstream_sbom=optional("upstream_sbom"),
        description=text("description"),
    )


def _component_semantics(
    component: Component, path: str, seen_ids: set[str]
) -> list[validation.Diagnostic]:
    """Enforce the author-declaration rules the closed JSON subset cannot express."""

    out: list[validation.Diagnostic] = []
    if component.id in seen_ids:
        out.append(validation.Diagnostic("component-boundary.duplicate-id", path=path))
    seen_ids.add(component.id)
    if not component.ref.strip() or not component.description.strip():
        out.append(validation.Diagnostic("component-boundary.empty-field", path=path))
    if component.digest is not None and _canonical_digest(component.digest) is None:
        out.append(validation.Diagnostic("component-boundary.digest-invalid", path=path))
    if component.scope in _CONTROLLED_SCOPES:
        # A pack-controlled component is distributed or immutably pinned, so it
        # cannot be an author-declared external and must carry a content digest.
        if component.authority == "author-declared-external":
            out.append(
                validation.Diagnostic(
                    "component-boundary.external-authority-on-controlled", path=path
                )
            )
        if _canonical_digest(component.digest) is None:
            out.append(
                validation.Diagnostic("component-boundary.missing-digest", path=path)
            )
    return out


# --------------------------------------------------------------------------- #
# Machine-derivable incumbents (auto-included; omission impossible)
# --------------------------------------------------------------------------- #
def incumbent_components(
    *,
    lockfile: object,
    kit_inventories: Sequence[Mapping[str, object]],
    scenarios: Sequence[object],
) -> list[Component]:
    """Derive the components every incumbent authority proves the pack ships/pins.

    These are auto-included in the SBOM regardless of the author declaration, so
    an author can never omit a lock module, a shipped kit component, or an SDL
    exact artifact from the inventory.
    """

    # One shared id set keeps every derived component id unique across the three
    # incumbent authorities; the helpers run in a fixed order so the union is
    # deterministic.
    used: set[str] = set()
    return [
        *_module_components(lockfile, used),
        *_kit_inventory_components(kit_inventories, used),
        *_sdl_artifact_components(scenarios, used),
    ]


def _module_components(lockfile: object, used: set[str]) -> list[Component]:
    """Derive the pinned RAES module components the ``raes.lock.json`` proves."""

    out: list[Component] = []
    imports = getattr(lockfile, "imports", None)
    for record in imports if isinstance(imports, Sequence) else ():
        module_id = getattr(record, "module_id", None)
        if not isinstance(module_id, str) or not module_id:
            continue
        out.append(
            Component(
                id=_slug("module", module_id, used),
                scope="pinned",
                kind="raes-module",
                authority="module-lock",
                ref=module_id,
                version=_str_or_none(getattr(record, "module_version", None)),
                digest=_canonical_digest(getattr(record, "content_digest", None)),
                license=None,
                provenance="raes.lock.json",
                upstream_sbom=None,
                description=f"RAES module {module_id} pinned by raes.lock.json",
            )
        )
    return out


def _kit_inventory_components(
    kit_inventories: Sequence[Mapping[str, object]], used: set[str]
) -> list[Component]:
    """Derive the shipped/pinned components recovered kit inventories declare."""

    out: list[Component] = []
    for entry in kit_inventories:
        scope = entry.get("scope")
        ref = entry.get("ref")
        if scope not in _CONTROLLED_SCOPES or not isinstance(ref, str) or not ref:
            continue
        out.append(
            Component(
                id=_slug("kit", ref, used),
                scope=str(scope),
                kind="other",
                authority="kit",
                ref=ref,
                version=None,
                digest=None,
                license=None,
                provenance=f"kit:{entry.get('__kit_id', '')}",
                upstream_sbom=None,
                description=str(entry.get("description") or f"kit component {ref}"),
            )
        )
    return out


def _sdl_artifact_components(
    scenarios: Sequence[object], used: set[str]
) -> list[Component]:
    """Derive the pinned components from the pack SDL's exact artifacts."""

    out: list[Component] = []
    requirements = publication_module.authored_artifact_requirements(scenarios)
    for requirement in requirements.values():
        exact = getattr(requirement, "exact_artifact", None) if requirement else None
        artifact_id = getattr(exact, "artifact_id", None)
        if not isinstance(artifact_id, str) or not artifact_id:
            continue
        out.append(
            Component(
                id=_slug("artifact", artifact_id, used),
                scope="pinned",
                kind=_image_kind(getattr(exact, "media_type", None)),
                authority="raes-artifact",
                ref=artifact_id,
                version=_str_or_none(getattr(exact, "version", None)),
                digest=_canonical_digest(getattr(exact, "digest", None)),
                license=None,
                provenance="sdl-source",
                upstream_sbom=None,
                description=f"artifact {artifact_id} pinned by the pack SDL",
            )
        )
    return out


def _str_or_none(value: object) -> str | None:
    """Return ``value`` when it is a non-empty string, else ``None``."""

    return value if isinstance(value, str) and value else None


def merge_components(
    incumbents: Sequence[Component], declared: Sequence[Component]
) -> tuple[list[Component], list[validation.Diagnostic]]:
    """Union incumbent and authored components; refuse a contradicting declaration.

    An authored row that shares an incumbent's ``ref`` may enrich it (license,
    provenance, upstream SBOM) but must not disagree on the content digest -- a
    digest that contradicts the lock or the SDL is tampering, not enrichment. An
    authored row for a component no incumbent knows is added as declared.
    """

    diagnostics: list[validation.Diagnostic] = []
    by_ref: dict[str, Component] = {}
    order: list[str] = []
    for component in incumbents:
        # Two nodes may pin the same image; a ref appears in the inventory once.
        if component.ref not in by_ref:
            order.append(component.ref)
        by_ref[component.ref] = component
    for component in declared:
        incumbent = by_ref.get(component.ref)
        if incumbent is None:
            by_ref[component.ref] = component
            order.append(component.ref)
            continue
        if (
            component.digest is not None
            and incumbent.digest is not None
            and _canonical_digest(component.digest) != _canonical_digest(incumbent.digest)
        ):
            diagnostics.append(
                validation.Diagnostic("component-boundary.digest-mismatch", path=component.id)
            )
            continue
        by_ref[component.ref] = _enrich(incumbent, component)
    return [by_ref[ref] for ref in order], diagnostics


def _enrich(incumbent: Component, declared: Component) -> Component:
    """Fill an incumbent's optional fields from the authored row, keeping identity."""

    return cast(
        Component,
        dataclasses.replace(
            incumbent,
            license=incumbent.license or declared.license,
            provenance=incumbent.provenance or declared.provenance,
            upstream_sbom=incumbent.upstream_sbom or declared.upstream_sbom,
        ),
    )


# --------------------------------------------------------------------------- #
# Pack loader (gathers incumbents + authored declaration, then merges)
# --------------------------------------------------------------------------- #
def _read_pack_yaml(pack_root: str | os.PathLike[str]) -> dict[str, object]:
    """Read ``pack.yaml`` through a descriptor-anchored bounded reader."""

    try:
        _root, root_fd = _pack_fs.open_root(pack_root, error_type=ComponentBoundaryError)
    except (_pack_fs.PackFilesystemError, OSError) as exc:
        raise ComponentBoundaryError("pack root could not be opened safely") from exc
    try:
        raw = _pack_fs.read_member_bytes(root_fd, "pack.yaml", max_bytes=1024 * 1024)
    except (_pack_fs.PackFilesystemError, OSError) as exc:
        raise ComponentBoundaryError("pack.yaml could not be read") from exc
    finally:
        os.close(root_fd)
    try:
        document = yaml.safe_load(raw.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ComponentBoundaryError("pack.yaml is not valid UTF-8 YAML") from exc
    return document if isinstance(document, dict) else {}


def _read_member_yaml(pack_root: str | os.PathLike[str], rel: str) -> object | None:
    """Read one optional pack-relative YAML member, or ``None`` when absent."""

    try:
        _root, root_fd = _pack_fs.open_root(pack_root)
    except (_pack_fs.PackFilesystemError, OSError):
        return None
    raw: bytes | None = None
    try:
        norm = _pack_fs.normalize_relpath(rel)
        raw = _pack_fs.read_member_bytes(root_fd, norm, max_bytes=8 * 1024 * 1024)
    except (_pack_fs.PackFilesystemError, OSError):
        raw = None
    finally:
        os.close(root_fd)
    result: object | None = None
    if raw is not None:
        try:
            result = yaml.safe_load(raw.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError):
            result = None
    return result


def _recover_kit_inventories(
    pack_root: str | os.PathLike[str], kit_source_resolver: KitSourceResolver | None = None
) -> tuple[list[dict[str, object]], list[validation.Diagnostic]]:
    """Recover kit component inventories through the immutable source/revision.

    ``kit_source_resolver`` maps ``(source_id, revision, kit_id, kit_version)`` to
    an immutable staged catalog root that contains ``kits/``. When a pack declares
    materializations but no resolver can supply that root, the inventory is
    reported as an authority-unavailable failure rather than silently skipped --
    ADR 0037 forbids inferring the components from filenames.
    """

    document = _read_member_yaml(pack_root, _KIT_MATERIALIZATIONS)
    records = document.get("materializations") if isinstance(document, dict) else None
    if not isinstance(records, list) or not records:
        return [], []
    inventories: list[dict[str, object]] = []
    diagnostics: list[validation.Diagnostic] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        entries, record_diagnostics = _recover_one_kit_inventory(record, index, kit_source_resolver)
        inventories.extend(entries)
        diagnostics.extend(record_diagnostics)
    return inventories, diagnostics


def _recover_one_kit_inventory(
    record: Mapping[str, object],
    index: int,
    kit_source_resolver: KitSourceResolver | None,
) -> tuple[list[dict[str, object]], list[validation.Diagnostic]]:
    """Recover one materialization record's kit inventory entries.

    Returns ``(entries, diagnostics)``. A record missing its immutable identity,
    or a kit that cannot be opened through the resolver-supplied source, is
    reported as a single bounded diagnostic and yields no entries; a recovered kit
    tags every inventory row with its originating ``__kit_id``.
    """

    path = f"{_KIT_MATERIALIZATIONS}[{index}]"
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    kit_id = record.get("kit_id")
    kit_version = record.get("kit_version")
    source_id = source.get("id")
    revision = source.get("revision")
    if not all(isinstance(v, str) and v for v in (kit_id, kit_version, source_id, revision)):
        return [], [validation.Diagnostic("component-boundary.kit-record-invalid", path=path)]
    inventory = _open_kit_inventory(source_id, revision, kit_id, kit_version, kit_source_resolver)
    if inventory is None:
        return [], [validation.Diagnostic("component-boundary.kit-source-unavailable", path=path)]
    return [{**entry, "__kit_id": kit_id} for entry in inventory], []


def _open_kit_inventory(
    source_id: str,
    revision: str,
    kit_id: str,
    kit_version: str,
    kit_source_resolver: KitSourceResolver | None,
) -> list[dict[str, object]] | None:
    """Return one kit's raw ``component_inventory`` rows, or ``None`` when unavailable.

    ``None`` means no resolver could supply the immutable staged root or the kit
    could not be opened through it -- an authority-unavailable failure the caller
    reports rather than inferring components from filenames. A kit that opens with
    no inventory returns an empty list.
    """

    root = kit_source_resolver(source_id, revision, kit_id, kit_version) if kit_source_resolver else None
    if root is None:
        return None
    try:
        release = kits_module.source_release(
            kits_module.KitSource(id=source_id, revision=revision, root=str(root)),
            kit_id,
            kit_version,
        )
    except kits_module.KitError:
        return None
    return [
        entry
        for entry in release.document.get("component_inventory", ())
        if isinstance(entry, dict)
    ]


def _load_lockfile(pack_root: str | os.PathLike[str]) -> object:
    """Load the pack's ``sdl/raes.lock.json`` module lock, or ``None``."""

    try:
        return load_lockfile(Path(pack_root, _SDL_LOCK_DIR))
    except (OSError, ValueError):
        return None


def _associated_artifact_ids(pack_root: str | os.PathLike[str]) -> frozenset[str]:
    """Return the pack's opaque associated-artifact ids, or an empty set."""

    try:
        manifest = digest_module.validate_pack_content_manifest(pack_root)
    except (digest_module.PackDigestError, OSError, ValueError):
        return frozenset()
    return frozenset(manifest.artifacts)


def _unknown_artifact_diagnostics(
    pack_root: str | os.PathLike[str], declared: Sequence[Component]
) -> list[validation.Diagnostic]:
    """Flag authored associated-artifact rows the pack does not actually contain."""

    return [
        validation.Diagnostic("component-boundary.artifact-unknown", path=component.id)
        for component in declared
        if component.authority == "associated-artifact"
        and component.ref not in _associated_artifact_ids(pack_root)
    ]


def pack_component_boundary(
    pack_root: str | os.PathLike[str],
    *,
    scenarios: Sequence[object] | None = None,
    kit_source_resolver: KitSourceResolver | None = None,
) -> tuple[tuple[Component, ...], list[validation.Diagnostic]]:
    """Resolve one pack's full component boundary for SBOM generation.

    Returns ``(components, diagnostics)``. ``components`` is the union of the
    auto-included incumbents and the validated authored declaration; it is what
    :mod:`sbom` renders. ``diagnostics`` is empty exactly when the authored
    declaration is well-formed and consistent with every incumbent. A pack with
    no ``publication_supply`` still yields its incumbent components, so publishing
    it always inventories the modules and artifacts it pins.
    """

    pack = _read_pack_yaml(pack_root)
    diagnostics: list[validation.Diagnostic] = []
    declared: tuple[Component, ...] = ()
    pointer = pack.get("publication_supply")
    if isinstance(pointer, str):
        document = _read_member_yaml(pack_root, pointer)
        if document is None:
            return (), [validation.Diagnostic("publication-supply.unreadable", path=pointer)]
        schema_diagnostics, declared = validate_publication_supply_document(document)
        if schema_diagnostics:
            return declared, schema_diagnostics
        diagnostics.extend(_unknown_artifact_diagnostics(pack_root, declared))

    kit_inventories, kit_diagnostics = _recover_kit_inventories(pack_root, kit_source_resolver)
    diagnostics.extend(kit_diagnostics)
    if scenarios is None:
        try:
            _result, scenarios = validation._validate_pack_for_author_ci(pack_root)
        except (OSError, ValueError):
            scenarios = ()

    incumbents = incumbent_components(
        lockfile=_load_lockfile(pack_root),
        kit_inventories=kit_inventories,
        scenarios=scenarios or (),
    )
    components, merge_diagnostics = merge_components(incumbents, list(declared))
    diagnostics.extend(merge_diagnostics)
    return tuple(components), diagnostics


__all__ = [
    "Component",
    "ComponentBoundaryError",
    "SUPPLY_SCHEMA_VERSION",
    "incumbent_components",
    "merge_components",
    "pack_component_boundary",
    "publication_supply_schema_path",
    "validate_publication_supply_document",
]
