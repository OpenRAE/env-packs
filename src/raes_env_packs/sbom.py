#!/usr/bin/env python3
"""Per-pack CycloneDX SBOM generation bound to the RAES release subject (ADR 0037).

The existing release-workflow SBOM (ADR 0004) describes the ``raes-env-packs``
Python distribution, not an individual environment-pack release. This module
generates a standards-backed CycloneDX JSON SBOM for one *pack* release from its
validated component boundary (:mod:`component_boundary`) and binds it to the
exact validated release subject -- the validator-derived RAES associated-artifact
set digest. The SBOM records its own digest and is emitted *outside* the
associated-artifact set it describes, so it never introduces a recursive
identity.

The generator reports inventory only. It marks external, runtime-selected,
opaque, and unresolved components as explicit scope rather than guessing their
transitive closure, references (never flattens) independently scoped upstream
SBOMs, and asserts nothing about safety, authenticity, realizability, or
vulnerability status. CycloneDX JSON is emitted directly with the standard
library so the package keeps its minimal runtime dependency surface (ADR 0004).
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Sequence

from . import component_boundary
from . import validation

SPEC_VERSION = "1.5"
BOM_FORMAT = "CycloneDX"

_CANONICAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# env-packs property namespace. The RAES set digest is the pack-release subject;
# the digest domain is named explicitly because a RAES set digest and an OCI
# manifest digest share the ``sha256:`` spelling (ADR 0037).
_PROP_SET_DIGEST = "raes:associated-artifact-set-digest"
_PROP_DIGEST_DOMAIN = "raes:digest-domain"
_PROP_SCOPE = "raes:component-scope"
_PROP_AUTHORITY = "raes:component-authority"
_PROP_KIND = "raes:component-kind"
_PROP_PROVENANCE = "raes:component-provenance"
_SET_DIGEST_DOMAIN = "raes-associated-artifact-set"

# CycloneDX component type for each declared kind.
_KIND_TO_TYPE = {
    "raes-module": "library",
    "container-image": "container",
    "os-package": "library",
    "language-package": "library",
    "executable": "application",
    "model": "machine-learning-model",
    "dataset": "data",
    "firmware": "firmware",
    "source": "file",
    "other": "library",
}
# CycloneDX component scope for each declared boundary scope. Pack-controlled
# components are required; everything else is an explicit, optional, non-guessed
# dependency the pack does not resolve for the consumer.
_SCOPE_TO_CDX = {
    "shipped": "required",
    "pinned": "required",
    "external": "optional",
    "runtime-selected": "optional",
    "opaque": "optional",
    "unresolved": "optional",
}


def _serial_number(set_digest: str) -> str:
    """Derive a deterministic CycloneDX serial URN from the release subject.

    A random serial would make an unchanged release re-identify its SBOM on every
    rebuild. Deriving it from the set digest keeps the document reproducible while
    remaining a valid ``urn:uuid``.
    """

    seed = hashlib.sha256(f"cdx-serial:{set_digest}".encode("utf-8")).digest()
    return f"urn:uuid:{uuid.UUID(bytes=seed[:16], version=5)}"


def _hex(digest: str | None) -> str | None:
    """Return the bare hex body of a canonical ``sha256:`` digest, or ``None``."""

    if isinstance(digest, str) and _CANONICAL_DIGEST_RE.fullmatch(digest):
        return digest.split(":", 1)[1]
    return None


def _component_entry(component: component_boundary.Component) -> dict[str, object]:
    """Render one declared component as a CycloneDX component object."""

    entry: dict[str, object] = {
        "type": _KIND_TO_TYPE.get(component.kind, "library"),
        "bom-ref": component.id,
        "name": component.ref,
        "scope": _SCOPE_TO_CDX.get(component.scope, "optional"),
    }
    if component.version:
        entry["version"] = component.version
    hex_digest = _hex(component.digest)
    if hex_digest is not None:
        entry["hashes"] = [{"alg": "SHA-256", "content": hex_digest}]
    if component.license:
        entry["licenses"] = [{"license": {"name": component.license}}]
    properties = [
        {"name": _PROP_SCOPE, "value": component.scope},
        {"name": _PROP_AUTHORITY, "value": component.authority},
        {"name": _PROP_KIND, "value": component.kind},
    ]
    if component.provenance:
        properties.append({"name": _PROP_PROVENANCE, "value": component.provenance})
    entry["properties"] = properties
    if component.upstream_sbom:
        # Reference the independently scoped upstream SBOM; never flatten it into
        # this generated document (ADR 0037). It stays an associated artifact
        # with its own subject, scope, digest, and provenance.
        entry["externalReferences"] = [
            {"type": "bom", "url": f"raes-associated-artifact:{component.upstream_sbom}"}
        ]
    entry["properties"].sort(key=lambda item: (item["name"], item["value"]))
    return entry


def generate_sbom(
    *,
    pack_name: str,
    pack_version: str,
    set_digest: str,
    components: Sequence[component_boundary.Component],
    timestamp: str | None = None,
) -> dict[str, object]:
    """Generate a CycloneDX 1.5 SBOM document for one validated pack release.

    ``set_digest`` is the validator-derived RAES associated-artifact set digest --
    the release subject the SBOM is bound to, carried on the metadata component so
    a consumer can join the inventory back to the exact bytes it verified. The
    document is otherwise a deterministic function of its inputs; ``timestamp`` is
    accepted only when a caller wants a build time recorded and is omitted by
    default so an unchanged release produces byte-identical output.
    """

    if _CANONICAL_DIGEST_RE.fullmatch(set_digest) is None:
        raise ValueError("set digest is not a canonical sha256 value")
    metadata_component = {
        "type": "application",
        "bom-ref": f"pack:{pack_name}@{pack_version}",
        "name": pack_name,
        "version": pack_version,
        "properties": [
            {"name": _PROP_SET_DIGEST, "value": set_digest},
            {"name": _PROP_DIGEST_DOMAIN, "value": _SET_DIGEST_DOMAIN},
        ],
    }
    metadata: dict[str, object] = {"component": metadata_component}
    if timestamp is not None:
        metadata["timestamp"] = timestamp
    return {
        "bomFormat": BOM_FORMAT,
        "specVersion": SPEC_VERSION,
        "serialNumber": _serial_number(set_digest),
        "version": 1,
        "metadata": metadata,
        "components": [_component_entry(component) for component in components],
    }


def sbom_bytes(document: dict[str, object]) -> bytes:
    """Serialize an SBOM to canonical, reproducible UTF-8 JSON bytes."""

    return (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def sbom_digest(document: dict[str, object]) -> str:
    """Return the SBOM's own canonical ``sha256:`` digest over its bytes."""

    return "sha256:" + hashlib.sha256(sbom_bytes(document)).hexdigest()


def _append_format_diagnostics(
    document: dict[str, object], diagnostics: list[validation.Diagnostic]
) -> None:
    """Append format and spec-version diagnostics for a candidate SBOM document."""

    if document.get("bomFormat") != BOM_FORMAT:
        diagnostics.append(validation.Diagnostic("sbom.format", path="$.bomFormat"))
    if document.get("specVersion") != SPEC_VERSION:
        diagnostics.append(validation.Diagnostic("sbom.spec-version", path="$.specVersion"))


def _metadata_component(document: dict[str, object]) -> dict[str, object]:
    """Return the SBOM metadata component object, or an empty mapping when absent."""

    metadata = document.get("metadata")
    component = metadata.get("component") if isinstance(metadata, dict) else None
    return component if isinstance(component, dict) else {}


def _append_subject_diagnostics(
    component: dict[str, object],
    expected_name: str,
    expected_version: str,
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Append a subject-mismatch diagnostic when the metadata name/version differ."""

    if component.get("name") != expected_name or component.get("version") != expected_version:
        diagnostics.append(validation.Diagnostic("sbom.subject-mismatch", path="$.metadata.component"))


def _append_subject_digest_diagnostics(
    component: dict[str, object],
    expected_set_digest: str,
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Append a subject-digest diagnostic when the bound set digest is not the subject."""

    properties = {
        item.get("name"): item.get("value")
        for item in component.get("properties", [])
        if isinstance(item, dict)
    }
    if properties.get(_PROP_SET_DIGEST) != expected_set_digest:
        diagnostics.append(
            validation.Diagnostic(
                "sbom.subject-digest-mismatch", path="$.metadata.component.properties"
            )
        )


def _append_coverage_diagnostics(
    document: dict[str, object],
    expected_component_refs: frozenset[str],
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Append a coverage diagnostic for every declared component ref the SBOM omits."""

    present = {
        entry.get("bom-ref")
        for entry in document.get("components", [])
        if isinstance(entry, dict)
    }
    diagnostics.extend(
        validation.Diagnostic("sbom.coverage-missing", path=f"$.components[{ref}]")
        for ref in sorted(expected_component_refs - present)
    )


def validate_sbom_document(
    document: object,
    *,
    expected_name: str,
    expected_version: str,
    expected_set_digest: str,
    expected_component_refs: frozenset[str],
) -> list[validation.Diagnostic]:
    """Verify an SBOM's shape, subject binding, and declared-boundary coverage.

    This is the publication and consumer gate (ADR 0037): the SBOM must be a
    CycloneDX document of the supported spec, its metadata component must name the
    exact release, its bound set digest must equal the verified subject, and it
    must cover every component the boundary declared. Coverage failure and subject
    mismatch are distinct, bounded diagnostics -- an SBOM that silently drops a
    declared component is not accepted.
    """

    if not isinstance(document, dict):
        return [validation.Diagnostic("sbom.not-an-object", path="$")]
    diagnostics: list[validation.Diagnostic] = []
    _append_format_diagnostics(document, diagnostics)
    component = _metadata_component(document)
    _append_subject_diagnostics(component, expected_name, expected_version, diagnostics)
    _append_subject_digest_diagnostics(component, expected_set_digest, diagnostics)
    _append_coverage_diagnostics(document, expected_component_refs, diagnostics)
    return diagnostics


__all__ = [
    "BOM_FORMAT",
    "SPEC_VERSION",
    "generate_sbom",
    "sbom_bytes",
    "sbom_digest",
    "validate_sbom_document",
]
