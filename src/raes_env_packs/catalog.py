"""Environment-pack catalog projection (issue #188, ADR 0032).

``raes-pack-catalog`` renders one *generated* catalog read model from facts that
already have authorities. It is not an authoring surface, a runtime contract, a
trust decision, or a scenario semantic model, and it defines zero extensions to
RAES semantics (ADR 0009).

One normalized :class:`Entry` is the only data model for both outputs: the JSON
index serializes the entry and the human "card" renders that same entry. A
one-pack invocation produces the same document with a single entry, so there is
no separate card schema.

The generator consumes ONE safe, validated static-authority snapshot per pack
(``validation._validate_pack_snapshot``); it never reopens an untrusted tree,
imports author-CI execution, runs pack code, or touches the network, the clock,
Git, or the environment. Freshness is computed against a caller-supplied
``as_of`` and rehearsal-age policy so identical inputs produce byte-identical
JSON (ADR 0032).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import publication, validation
from .check import _terminal_safe

# JSON/schema identity. Bump (and mint a new schema) when the closed contract's
# field shape, requiredness, enum meaning, state semantics, identity, or
# canonical ordering changes. Independent of the package/pack/layout/RAES
# versions (ADR 0032).
SCHEMA_VERSION = "environment-pack-catalog/v1"

_CATALOG_SCHEMA = (
    Path(__file__).with_name("resources") / "schemas" / "catalog.schema.yaml"
)

# Durable documentation target for catalog diagnostics.
DOC_PAGE = "docs/public/catalog.md"

# Stable process contract (mirrors raes-pack-check / ADR 0031).
EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_USAGE = 2
EXIT_TOOL_FAILURE = 3

# Default rehearsal freshness policy when the caller supplies none. Freshness
# only ever applies to a previously *verified* observation; no such evidence
# channel exists yet, so this bound is carried for reproducibility, not used to
# downgrade a real observation.
DEFAULT_REHEARSAL_MAX_AGE_DAYS = 90

# A runtime profile the pack declares as actually shipped/available.
_SUPPORTED_PROFILE_STATUSES = frozenset({"supported", "required"})
# RAES owns integrity/authenticity/trust; this repository consumes it and never
# mints its own (ADR 0010).
_TRUST_AUTHORITY = "raes-reusable-asset-trust-policy"
# Asset visibilities that are eligible for the public/participant catalog media
# boundary. Anything else is restricted and never surfaced as a media reference.
_PUBLIC_MEDIA_VISIBILITY = frozenset({"participant", "public"})
# Provenance distribution classes that permit a public catalog to publish a
# reference. Restricted classes (internal-only, commercial-only,
# customer-specific) and seed-dependent `generated` output are never eligible.
_PUBLISHABLE_DISTRIBUTION = frozenset({"open", "redistributable"})

# A safe cross-repository source id: the same closed shape the catalog schema
# enforces. It admits no path separator, whitespace, or `..`, so an untrusted
# source label can never become an unchecked output path (ADR 0032).
_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*[a-z0-9]$")


def _is_safe_source_id(source_id: object) -> bool:
    """Whether a source id is safe to use as identity and (later) a path slug."""

    return (
        isinstance(source_id, str)
        and ".." not in source_id
        and _SOURCE_ID_RE.fullmatch(source_id) is not None
    )


@dataclass(frozen=True)
class Source(object):
    """A caller-supplied catalog source: stable identity plus a staged root.

    ``id`` and ``revision`` are the cross-repository identity Hub supplies. They
    are never derived from a Git remote, ambient branch, current ``HEAD``,
    filesystem mtime, or repository basename (ADR 0032).
    """

    id: str
    revision: str
    root: str


@dataclass(frozen=True)
class CatalogDiagnostic(object):
    """One catalog diagnostic.

    ``blocking`` distinguishes a problem that prevents a truthful entry (an
    invalid pack, an unsafe source id, a duplicate identity) from a non-blocking
    completeness note (a missing but truthfully ``unknown``/``unverified``
    fact). Locations are bounded and pack-relative; no authored value, absolute
    path, or upstream prose ever enters a diagnostic (ADR 0031/0032).
    """

    code: str
    blocking: bool
    source_id: str
    pack: str | None = None
    field: str | None = None


@dataclass(frozen=True)
class CatalogDocument(object):
    """The serializable catalog: schema version, freshness inputs, and entries."""

    as_of: str
    rehearsal_max_age_days: int
    entries: tuple[dict[str, object], ...]


# --------------------------------------------------------------------------
# Explicit state constructors (ADR 0032). `unknown` never carries a value.
# --------------------------------------------------------------------------
def _known_text(value: str) -> dict[str, object]:
    return {"state": "known", "value": value}


def _unknown() -> dict[str, object]:
    return {"state": "unknown"}


def _known_list(values: list[str]) -> dict[str, object]:
    return {"state": "known", "values": values}


def _text_field(value: object) -> dict[str, object]:
    """Project a descriptive text fact: known only for a non-empty string."""

    if isinstance(value, str) and value.strip():
        return _known_text(value)
    return _unknown()


def _str_list(value: object) -> list[str]:
    """Return the non-empty strings of a list value, in declared order."""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


# --------------------------------------------------------------------------
# Per-authority projections
# --------------------------------------------------------------------------
def _project_identity(manifest: dict[str, object]) -> dict[str, object]:
    """Identity and maturity from pack.yaml."""

    status = manifest.get("status")
    maturity = status if status in ("draft", "built", "golden") else "unknown"
    return {
        "name": str(manifest.get("name") or ""),
        "title": str(manifest.get("title") or ""),
        "version": str(manifest.get("version") or ""),
        "maturity": maturity,
    }


def _project_audiences(compatibility: dict[str, object] | None) -> dict[str, object]:
    """Intended audiences from delivery-bundle declarations."""

    if not isinstance(compatibility, dict):
        return _unknown()
    bundles = compatibility.get("delivery_bundles")
    audiences = sorted(
        {
            bundle["audience"]
            for bundle in (bundles if isinstance(bundles, list) else [])
            if isinstance(bundle, dict) and isinstance(bundle.get("audience"), str)
        }
    )
    return _known_list(audiences) if audiences else _unknown()


def _project_runtimes(compatibility: dict[str, object] | None) -> list[dict[str, object]]:
    """Declared runtime/adapter capability per named profile."""

    if not isinstance(compatibility, dict):
        return []
    profiles = compatibility.get("runtime_profiles")
    rows: list[dict[str, object]] = []
    for profile in profiles if isinstance(profiles, list) else []:
        if not isinstance(profile, dict) or not isinstance(profile.get("profile_id"), str):
            continue
        support = (
            "supported"
            if profile.get("status") in _SUPPORTED_PROFILE_STATUSES
            else "unsupported"
        )
        row: dict[str, object] = {"profile_id": profile["profile_id"], "support": support}
        if isinstance(profile.get("provider"), str):
            row["provider"] = profile["provider"]
        rows.append(row)
    return sorted(rows, key=lambda row: str(row["profile_id"]))


def _project_launch_modes(
    compatibility: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Declared delivery/launch modes per bundle."""

    if not isinstance(compatibility, dict):
        return []
    bundles = compatibility.get("delivery_bundles")
    rows: list[dict[str, object]] = []
    for bundle in bundles if isinstance(bundles, list) else []:
        if not isinstance(bundle, dict) or not isinstance(bundle.get("bundle_id"), str):
            continue
        support = "supported" if bundle.get("status") == "supported" else "unsupported"
        row: dict[str, object] = {"bundle_id": bundle["bundle_id"], "support": support}
        if isinstance(bundle.get("audience"), str):
            row["audience"] = bundle["audience"]
        rows.append(row)
    return sorted(rows, key=lambda row: str(row["bundle_id"]))


def _project_participant_activity(scenarios: tuple[object, ...]) -> dict[str, object]:
    """Summarize governed RAES fields only (counts), never inferred activity."""

    if not scenarios:
        return _unknown()
    activity: dict[str, object] = {"state": "known", "scenarios": len(scenarios)}
    nodes = 0
    counted = False
    for scenario in scenarios:
        container = getattr(scenario, "nodes", None)
        try:
            nodes += len(container)  # type: ignore[arg-type]
            counted = True
        except TypeError:
            continue
    if counted:
        activity["nodes"] = nodes
    return activity


def _project_safety(provenance: dict[str, object] | None) -> dict[str, object]:
    """Content-safety attestations from the provenance ledger."""

    if not isinstance(provenance, dict):
        return _unknown()
    safety = provenance.get("content_safety")
    if not isinstance(safety, dict):
        return _unknown()
    satisfied = all(safety.get(flag) is True for flag in validation.CONTENT_SAFETY_FLAGS)
    return {"state": "known", "attestations_satisfied": satisfied}


def _project_provenance(provenance: dict[str, object] | None) -> dict[str, object]:
    """Leak-safe provenance projection: counts and review status only."""

    if not isinstance(provenance, dict):
        return _unknown()
    sources = provenance.get("sources")
    artifacts = provenance.get("artifacts")
    review = provenance.get("review")
    projected: dict[str, object] = {
        "state": "known",
        "sources": len(sources) if isinstance(sources, list) else 0,
        "artifacts": len(artifacts) if isinstance(artifacts, list) else 0,
    }
    if isinstance(review, dict) and isinstance(review.get("status"), str):
        projected["review_status"] = review["status"]
    return projected


def _project_release(
    publication_doc: dict[str, object] | None,
    publication_declared: bool,
    scenarios: tuple[object, ...],
) -> dict[str, object]:
    """Release identity + availability from the validated publication profile.

    The outcomes stay distinct (ADR 0032) — an absent authority, an
    expected-invalid document, and an unexpected failure are never collapsed:

    - no publication pointer declared → ``unknown`` (authority absent);
    - pointer declared but the document did not load or failed publication
      validation → ``unverified`` (present but not established);
    - validates clean → ``known`` with the immutable identity.

    Manifest↔publication identity agreement is NOT re-decided here: the shared
    static authority (``_validate_pack_core``) already fails ``validate_pack``
    on a mismatch, so a mismatched pack never reaches this projection. This
    consumes only facts whose joins were established upstream. An unexpected
    exception is not caught here — it propagates to the CLI's tool-failure path
    rather than being mislabeled as foreign-input invalidity.
    """

    if not publication_declared:
        return _unknown()
    if not isinstance(publication_doc, dict):
        # Declared but unreadable/not a mapping: present, not absent.
        return {"state": "unverified"}
    requirements = publication.authored_artifact_requirements(scenarios)
    violations = publication.validate_publication_document(
        publication_doc, requirements=requirements
    )
    if violations:
        return {"state": "unverified"}
    identity = publication.release_identity(publication_doc)
    pack = identity.get("pack") if isinstance(identity, dict) else None
    projected: dict[str, object] = {"state": "known"}
    if isinstance(pack, dict):
        if isinstance(pack.get("name"), str):
            projected["name"] = pack["name"]
        if isinstance(pack.get("version"), str):
            projected["version"] = pack["version"]
    distribution = publication_doc.get("distribution")
    if isinstance(distribution, dict):
        availability = _str_list(distribution.get("availability"))
        if availability:
            projected["availability"] = sorted(availability)
    return projected


def _path_components(path: str) -> tuple[str, ...]:
    """Canonical forward/back-slash-split path components, dropping ``.``/empties."""

    return tuple(part for part in re.split(r"[\\/]+", path) if part not in ("", "."))


def _distribution_class(provenance: dict[str, object] | None, path: str) -> str | None:
    """The provenance distribution class governing ``path``, or ``None``.

    A provenance ``artifacts[]`` row's ``path`` is the default class for content
    at or under that root; the most specific (longest) matching root governs.
    This is the relational join that lets media eligibility bind to the
    provenance authority instead of trusting the compatibility row alone.
    """

    if not isinstance(provenance, dict):
        return None
    target = _path_components(path)
    if not target or ".." in target:
        return None
    best_len = -1
    best_class: str | None = None
    for artifact in provenance.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        root = artifact.get("path")
        classification = artifact.get("classification")
        if not isinstance(root, str) or not isinstance(classification, str):
            continue
        root_parts = _path_components(root)
        if root_parts == target[: len(root_parts)] and len(root_parts) > best_len:
            best_len = len(root_parts)
            best_class = classification
    return best_class


def _project_media(
    compatibility: dict[str, object] | None,
    inventory: frozenset[str],
    provenance: dict[str, object] | None,
) -> tuple[list[dict[str, object]], bool]:
    """Public-boundary-eligible declared media, bound to the validated authorities.

    Returns ``(references, excluded_not_distributable)``. A reference is surfaced
    ONLY when every applicable authority agrees (ADR 0032): the compatibility row
    declares a public/participant, shipped asset; the path exists in the
    descriptor-anchored inventory (existence is already a ``validate_pack``
    invariant for shipped assets — this is defense in depth); and the provenance
    ledger classifies the path as publicly distributable.

    Visibility and distribution are deliberately separate axes: a
    participant-visible asset may legitimately be a restricted distribution
    class, so excluding it from a PUBLIC catalog is a catalog-eligibility
    decision, not a pack defect. That exclusion is NOT silent — the caller
    records a completeness diagnostic — so ``validate_pack`` and the catalog
    never disagree while an author still gets an actionable signal. A reference
    is recorded as safe metadata only, never parsed, fetched, or trusted.
    """

    if not isinstance(compatibility, dict):
        return [], False
    assets = compatibility.get("assets")
    rows: list[dict[str, object]] = []
    excluded_not_distributable = False
    for asset in assets if isinstance(assets, list) else []:
        if not isinstance(asset, dict):
            continue
        path = asset.get("path")
        visibility = asset.get("visibility")
        if not (
            isinstance(path, str)
            and visibility in _PUBLIC_MEDIA_VISIBILITY
            and asset.get("status") == "shipped"
            and path in inventory
        ):
            continue
        if _distribution_class(provenance, path) not in _PUBLISHABLE_DISTRIBUTION:
            # Declared public and present, but not publicly distributable per
            # provenance — surfaced as a diagnostic, never as a media reference.
            excluded_not_distributable = True
            continue
        row: dict[str, object] = {"reference": path, "eligible": True}
        if isinstance(visibility, str):
            row["role"] = visibility
        rows.append(row)
    return sorted(rows, key=lambda row: str(row["reference"])), excluded_not_distributable


# Discovery facts a catalog consumer needs; a truthful `unknown` still earns a
# non-blocking completeness diagnostic so incompleteness stays actionable (AC3).
_REQUIRED_DISCOVERY_FIELDS = (
    "purpose",
    "license",
    "audiences",
    "difficulty",
    "participant_time",
)


def _completeness(entry: dict[str, object]) -> list[dict[str, object]]:
    """Non-blocking completeness codes for truthfully absent required facts."""

    notes: list[dict[str, object]] = []
    for field in _REQUIRED_DISCOVERY_FIELDS:
        if entry[field].get("state") == "unknown":  # type: ignore[union-attr]
            notes.append({"code": f"catalog.{field}.undeclared", "field": field})
    if entry["safety"].get("state") == "unknown":  # type: ignore[union-attr]
        notes.append({"code": "catalog.safety.undeclared", "field": "safety"})
    if entry["last_rehearsal"].get("state") == "unknown":  # type: ignore[union-attr]
        notes.append(
            {"code": "catalog.rehearsal.unverified", "field": "last_rehearsal"}
        )
    return notes


def build_entry(source: Source, snapshot: "validation._PackSnapshot") -> dict[str, object]:
    """Project one validated snapshot into a normalized catalog entry.

    The caller guarantees the pack passed static validation, so the manifest and
    its identity fields are present. Everything else is projected with an
    explicit state; a missing fact is a truthful ``unknown``/``unverified``, not
    a guess.
    """

    manifest = snapshot.manifest or {}
    media, media_not_distributable = _project_media(
        snapshot.compatibility, snapshot.inventory, snapshot.provenance
    )
    entry: dict[str, object] = {
        "source": {"id": source.id, "revision": source.revision},
        **_project_identity(manifest),
        "purpose": _text_field(manifest.get("description")),
        "authors": (
            _known_list(_str_list(manifest.get("authors")))
            if _str_list(manifest.get("authors"))
            else _unknown()
        ),
        "license": _text_field(manifest.get("license")),
        "limitations": _text_field(manifest.get("limitations")),
        "audiences": _project_audiences(snapshot.compatibility),
        "participant_activity": _project_participant_activity(snapshot.scenarios),
        # Explicit pack-domain estimates: descriptive pack.yaml metadata when an
        # author declares it, a truthful `unknown` otherwise. Never averaged from
        # challenges or derived from RAES clocks (ADR 0032).
        "difficulty": _text_field(manifest.get("difficulty")),
        "setup_time": _text_field(manifest.get("setup_time")),
        "participant_time": _text_field(manifest.get("participant_time")),
        "runtimes": _project_runtimes(snapshot.compatibility),
        "launch_modes": _project_launch_modes(snapshot.compatibility),
        # No resource/cost field exists in the compatibility contract today, so
        # it is a truthful `unknown` rather than an inference from node counts or
        # cloud prices.
        "resource_cost": _unknown(),
        # Fidelity is a RAES action-contract/realization claim; the catalog mints
        # no fidelity score, and no safe public projection exists at the current
        # pin, so it stays `unknown` (ADR 0032).
        "fidelity": _unknown(),
        "safety": _project_safety(snapshot.provenance),
        "provenance": _project_provenance(snapshot.provenance),
        "release": _project_release(
            snapshot.publication,
            snapshot.publication_declared,
            snapshot.scenarios,
        ),
        # RAES-owned and deferred: never upgraded from a digest, golden status,
        # or rehearsal success (ADR 0010).
        "trust": {"state": "unverified", "authority": _TRUST_AUTHORITY},
        # No structured, identity-bound rehearsal evidence channel exists yet, so
        # the honest projection is `unknown` (ADR 0032).
        "last_rehearsal": _unknown(),
        "media": media,
    }
    entry["completeness"] = _completeness(entry)
    if media_not_distributable:
        entry["completeness"].append(  # type: ignore[union-attr]
            {"code": "catalog.media.not-distributable", "field": "media"}
        )
    return entry


# --------------------------------------------------------------------------
# Aggregation (deterministic and collision-safe)
# --------------------------------------------------------------------------
def _entry_sort_key(entry: dict[str, object]) -> tuple[str, str, str]:
    """The documented composite key: source id, pack name, pack version."""

    source = entry.get("source")
    source_id = source["id"] if isinstance(source, dict) else ""
    return (str(source_id), str(entry.get("name")), str(entry.get("version")))


def build_catalog(
    sources: list[Source],
    *,
    as_of: str,
    rehearsal_max_age_days: int = DEFAULT_REHEARSAL_MAX_AGE_DAYS,
    limits: validation.PackValidationLimits | None = None,
) -> tuple[CatalogDocument, tuple[CatalogDiagnostic, ...]]:
    """Aggregate staged sources into one deterministic catalog document.

    Every source is validated through the shared static authority first; an
    invalid pack, an unsafe source id, or a duplicate composite identity is a
    blocking diagnostic and contributes no entry (fail closed — input order
    never selects a winner). Entries are sorted by the composite key so the same
    inputs in any discovery order produce byte-identical JSON.
    """

    active = limits or validation.PackValidationLimits()
    diagnostics: list[CatalogDiagnostic] = []
    entries: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str, str]] = set()

    for source in sources:
        if not _is_safe_source_id(source.id):
            diagnostics.append(
                CatalogDiagnostic("catalog.source.unsafe", True, source.id)
            )
            continue
        result, snapshot = validation._validate_pack_snapshot(
            source.root, limits=active
        )
        if not result.ok:
            # An invalid pack cannot be projected truthfully. Surface the
            # underlying static-authority codes as blocking catalog diagnostics.
            for diagnostic in result.diagnostics:
                diagnostics.append(
                    CatalogDiagnostic(
                        f"catalog.pack.invalid:{diagnostic.code}",
                        True,
                        source.id,
                        snapshot.manifest.get("name")
                        if isinstance(snapshot.manifest, dict)
                        else None,
                        diagnostic.path,
                    )
                )
            continue
        entry = build_entry(source, snapshot)
        key = _entry_sort_key(entry)
        if key in seen_keys:
            diagnostics.append(
                CatalogDiagnostic(
                    "catalog.identity.duplicate", True, source.id, str(entry["name"])
                )
            )
            continue
        seen_keys.add(key)
        entries.append(entry)
        for note in entry["completeness"]:  # type: ignore[union-attr]
            diagnostics.append(
                CatalogDiagnostic(
                    str(note["code"]),
                    False,
                    source.id,
                    str(entry["name"]),
                    note.get("field"),
                )
            )

    document = CatalogDocument(
        as_of=as_of,
        rehearsal_max_age_days=rehearsal_max_age_days,
        entries=tuple(sorted(entries, key=_entry_sort_key)),
    )
    return document, tuple(diagnostics)


# --------------------------------------------------------------------------
# Serialization
# --------------------------------------------------------------------------
def _document_mapping(document: CatalogDocument) -> dict[str, object]:
    """The plain mapping serialized to JSON and validated against the schema."""

    return {
        "schema_version": SCHEMA_VERSION,
        "as_of": document.as_of,
        "freshness": {"rehearsal_max_age_days": document.rehearsal_max_age_days},
        "entries": list(document.entries),
    }


# Discovery fields whose known/unknown state governs a single `value` string.
_DISCOVERY_TEXT_FIELDS = (
    "purpose",
    "license",
    "limitations",
    "difficulty",
    "setup_time",
    "participant_time",
)
# Discovery fields whose known/unknown state governs a `values` list.
_DISCOVERY_LIST_FIELDS = ("authors", "audiences")


def _stated(entry: dict[str, object], field: str) -> dict[str, object]:
    value = entry.get(field)
    return value if isinstance(value, dict) else {}


def _state_field_violations(
    entry: dict[str, object], field: str, path: str
) -> list[str]:
    """Relational state/value checks for one field family.

    Enforces the invariant JSON-Schema shape validation cannot express (ADR
    0032): which evidence fields each state *requires* and which it *forbids*.
    `known` must carry its value; `unknown` must not; an evidence state
    (`verified`/`stale`) must carry its observation, while `unverified`/`unknown`
    must not.
    """

    stated = _stated(entry, field)
    state = stated.get("state")
    out: list[str] = []

    def require(present: bool, keys: tuple[str, ...]) -> None:
        for key in keys:
            has = key in stated
            if present and not has:
                out.append(f"{path}.{field}.{key}: state-requires-field")
            if not present and has:
                out.append(f"{path}.{field}.{key}: state-forbids-field")

    if field in _DISCOVERY_TEXT_FIELDS:
        require(state == "known", ("value",))
    elif field in _DISCOVERY_LIST_FIELDS:
        require(state == "known", ("values",))
    elif field == "participant_activity":
        require(state == "known", ("scenarios",))
        if state != "known":
            require(False, ("nodes",))
    elif field == "resource_cost":
        require(state == "known", ("value",))
        if state != "known":
            require(False, ("profile", "basis"))
    elif field == "fidelity":
        require(state == "known", ("value",))
    elif field == "safety":
        require(state == "known", ("attestations_satisfied",))
    elif field == "provenance":
        require(state == "known", ("sources",))
        if state != "known":
            require(False, ("artifacts", "review_status"))
    elif field == "release":
        # Identity fields belong only to a `known` release; `unknown` and
        # `unverified` must not carry an unbound identity claim.
        if state != "known":
            require(False, ("name", "version", "availability"))
    elif field == "last_rehearsal":
        evidence = state in ("verified", "stale")
        require(evidence, ("as_of", "profile"))
    return out


_STATE_FIELDS = (
    _DISCOVERY_TEXT_FIELDS
    + _DISCOVERY_LIST_FIELDS
    + (
        "participant_activity",
        "resource_cost",
        "fidelity",
        "safety",
        "provenance",
        "release",
        "last_rehearsal",
    )
)


def _state_invariant_violations(mapping: dict[str, object]) -> list[str]:
    """Relational state/value violations across every entry and state family."""

    out: list[str] = []
    entries = mapping.get("entries")
    for index, entry in enumerate(entries if isinstance(entries, list) else []):
        if not isinstance(entry, dict):
            continue
        path = f"$.entries[{index}]"
        for field in _STATE_FIELDS:
            out.extend(_state_field_violations(entry, field, path))
    return out


def validate_document(document: CatalogDocument) -> list[str]:
    """Validate the generated document against the packaged catalog schema
    AND the relational state/value contract.

    Schema shape alone is not sufficient (ADR 0032): a canonical semantic pass
    enforces which evidence fields each state requires or forbids. A violation
    here is a generator defect, not foreign input — the caller treats a
    non-empty result as a tool failure. Returns stable ``$.<path>: <code>``
    strings.
    """

    schema = validation._trusted_schema(_CATALOG_SCHEMA)
    mapping = _document_mapping(document)
    violations = [
        f"{violation.path}: {violation.code}"
        for violation in validation._schema_violations(mapping, schema, schema)
    ]
    violations.extend(_state_invariant_violations(mapping))
    return violations


def render_json(document: CatalogDocument) -> str:
    """Serialize the catalog as deterministic, static-host-friendly JSON.

    UTF-8, fixed separators and indentation, stable key ordering, one trailing
    newline. Authored text is carried by JSON serialization, never string
    interpolation, so it cannot break the document.
    """

    return (
        json.dumps(
            _document_mapping(document),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    )


def _render_field(label: str, field: dict[str, object]) -> str:
    """Render one stated field for the human card, escaping authored text."""

    state = field.get("state")
    if "value" in field:
        return f"  {label}: {state} — {_terminal_safe(str(field['value']))}"
    if "values" in field:
        values = ", ".join(_terminal_safe(str(item)) for item in field["values"])  # type: ignore[union-attr]
        return f"  {label}: {state} — {values}"
    return f"  {label}: {state}"


def render_preview(document: CatalogDocument) -> str:
    """Render the same entries as a plain-language card set.

    HTML/Markdown-active content is never emitted; authored text is
    control-character escaped exactly as ``raes-pack-check`` does, so a crafted
    pack cannot spoof or drive the terminal.
    """

    lines = [f"catalog: {len(document.entries)} entr{'y' if len(document.entries) == 1 else 'ies'} (as of {_terminal_safe(document.as_of)})"]
    for entry in document.entries:
        source = entry["source"]
        lines.append("")
        lines.append(
            f"[{_terminal_safe(str(source['id']))}] "  # type: ignore[index]
            f"{_terminal_safe(str(entry['name']))} "
            f"{_terminal_safe(str(entry['version']))}  ({entry['maturity']})"
        )
        lines.append(f"  title: {_terminal_safe(str(entry['title']))}")
        lines.append(_render_field("purpose", entry["purpose"]))  # type: ignore[arg-type]
        lines.append(_render_field("audiences", entry["audiences"]))  # type: ignore[arg-type]
        lines.append(_render_field("license", entry["license"]))  # type: ignore[arg-type]
        lines.append(_render_field("difficulty", entry["difficulty"]))  # type: ignore[arg-type]
        supported = [r["profile_id"] for r in entry["runtimes"] if r["support"] == "supported"]  # type: ignore[union-attr,index]
        runtimes = ", ".join(_terminal_safe(str(p)) for p in supported) or "(none declared)"
        lines.append(f"  runtimes: {runtimes}")
        lines.append(f"  trust: {entry['trust']['state']} (authority: {_TRUST_AUTHORITY})")  # type: ignore[index]
        lines.append(f"  last rehearsal: {entry['last_rehearsal']['state']}")  # type: ignore[index]
        notes = entry["completeness"]
        if notes:
            codes = ", ".join(str(note["code"]) for note in notes)  # type: ignore[union-attr]
            lines.append(f"  completeness: {codes}")
    return "\n".join(lines) + "\n"


def _render_diagnostics(diagnostics: tuple[CatalogDiagnostic, ...]) -> str:
    """Render blocking diagnostics for stderr, bounded and body-free."""

    lines: list[str] = []
    for diagnostic in diagnostics:
        location = _terminal_safe(diagnostic.field) if diagnostic.field else "(entry)"
        pack = _terminal_safe(diagnostic.pack) if diagnostic.pack else "(unknown)"
        lines.append(
            f"[{_terminal_safe(diagnostic.source_id)}] {pack} {diagnostic.code} "
            f"at {location}  (see {DOC_PAGE})"
        )
    return "\n".join(lines) + "\n" if lines else ""


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _read_sources_manifest(path: str) -> list[Source]:
    """Read a ``[{id, revision, root}]`` sources manifest as staged descriptors.

    The manifest is a caller-controlled selector file (not pack content): its
    ``root`` paths are staged local directories. Raises ``ValueError`` for a
    malformed manifest so the CLI can report a usage error.
    """

    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, list):
        raise ValueError("sources manifest must be a list of {id, revision, root}")
    sources: list[Source] = []
    for item in raw:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(key), str) for key in ("id", "revision", "root")
        ):
            raise ValueError("each source needs string id, revision, and root")
        sources.append(Source(id=item["id"], revision=item["revision"], root=item["root"]))
    return sources


def _resolve_sources(args: argparse.Namespace) -> list[Source]:
    """Resolve CLI arguments into the ordered source list."""

    if args.sources is not None:
        return _read_sources_manifest(args.sources)
    return [
        Source(id=args.source_id, revision=args.source_revision, root=args.pack_root)
    ]


def _parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``raes-pack-catalog`` command."""

    parser = argparse.ArgumentParser(
        prog="raes-pack-catalog",
        description=(
            "Render a machine-readable environment-pack catalog projection. One "
            "staged pack produces a one-entry catalog document (its card); a "
            "sources manifest aggregates many packs deterministically. "
            "Networkless and non-executing: it never runs pack code, resolves "
            "SDL imports, reads the clock, or touches Git or the environment."
        ),
        epilog=(
            "exit codes: 0 catalog generated; 1 a source is invalid or has a "
            "duplicate/unsafe identity; 2 invalid invocation; 3 generator/upstream failure."
        ),
    )
    parser.add_argument(
        "pack_root",
        nargs="?",
        help="path to one staged pack directory (single-pack mode)",
    )
    parser.add_argument(
        "--source-id",
        help="stable non-secret source id for the single pack (default: local)",
        default="local",
    )
    parser.add_argument(
        "--source-revision",
        help="immutable source revision for the single pack (default: unspecified)",
        default="unspecified",
    )
    parser.add_argument(
        "--sources",
        help="path to a [{id, revision, root}] manifest to aggregate many packs",
    )
    parser.add_argument(
        "--as-of",
        default="",
        help="caller-supplied point in time freshness is computed against",
    )
    parser.add_argument(
        "--rehearsal-max-age-days",
        type=int,
        default=DEFAULT_REHEARSAL_MAX_AGE_DAYS,
        help="rehearsal freshness policy, echoed for reproducibility",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="render the human card set instead of the JSON document",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point. Returns the process exit status."""

    parser = _parser()
    args = parser.parse_args(argv)

    if args.sources is None and args.pack_root is None:
        parser.error("provide a pack_root or --sources manifest")
    if args.sources is not None and args.pack_root is not None:
        parser.error("use either a pack_root or --sources, not both")
    if args.rehearsal_max_age_days < 1:
        parser.error("--rehearsal-max-age-days must be a positive integer")

    try:
        sources = _resolve_sources(args)
    except (ValueError, OSError) as exc:
        parser.error(f"could not read sources: {type(exc).__name__}")

    for source in sources:
        if not os.path.isdir(source.root):
            parser.error(f"not a directory: {_terminal_safe(source.root)}")

    try:
        document, diagnostics = build_catalog(
            sources,
            as_of=args.as_of,
            rehearsal_max_age_days=args.rehearsal_max_age_days,
        )
        schema_errors = validate_document(document)
    except Exception as exc:
        # A generator or upstream defect is a tool failure, never mislabeled as
        # invalid pack content. Report only the exception type (ADR 0031).
        print(f"raes-pack-catalog: internal error ({type(exc).__name__})", file=sys.stderr)
        return EXIT_TOOL_FAILURE

    if schema_errors:
        # A generated document that fails its own schema is a defect in this
        # tool, not in the pack.
        print(
            f"raes-pack-catalog: internal error (schema: {schema_errors[0]})",
            file=sys.stderr,
        )
        return EXIT_TOOL_FAILURE

    blocking = tuple(d for d in diagnostics if d.blocking)
    if blocking:
        # Fail closed: emit no document (a partial/collision-resolved catalog
        # would be misleading), report the blocking problems on stderr.
        sys.stderr.write(_render_diagnostics(blocking))
        return EXIT_BLOCKING

    if args.preview:
        sys.stdout.write(render_preview(document))
    else:
        # JSON mode writes only the JSON document to stdout; per-entry
        # completeness notes travel inside it.
        sys.stdout.write(render_json(document))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
