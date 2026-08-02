#!/usr/bin/env python3
"""Pack-release provenance statement bound to the RAES release subject (ADR 0037).

A published pack release carries build/release provenance that binds the pack
version, semantic parent, source revision, builder/workflow identity, exact
``raes.lock.json`` state, release-view set identities, and the generated SBOM
digest to one subject: the validator-derived RAES associated-artifact set digest.
This is the signable/attestable subject and is deliberately distinct from a RAES
``Source.build.attestation`` (which records facts about one image build) and from
module signatures (which authenticate resolved modules). These are related
evidence at different boundaries and are never collapsed into one claim.

The statement is an in-toto Statement v1 with a pack-release predicate. The
subject digest is recorded under an explicit ``raesAssociatedArtifactSet``
algorithm name rather than a bare ``sha256`` key, because a RAES set digest and
an OCI manifest digest share the ``sha256:`` spelling and must never be confused.
The document is a deterministic function of its inputs and records no timestamp,
so an unchanged release produces byte-identical provenance. The generated
provenance is external evidence about the release and stays outside the
associated-artifact set it describes.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from . import validation

STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://raes.dev/provenance/pack-release/v1"
SUBJECT_DIGEST_ALG = "raesAssociatedArtifactSet"

_CANONICAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _subject_hex(set_digest: str) -> str:
    """Return the bare hex body of a canonical RAES set digest."""

    if _CANONICAL_DIGEST_RE.fullmatch(set_digest) is None:
        raise ValueError("set digest is not a canonical sha256 value")
    return set_digest.split(":", 1)[1]


@dataclass(frozen=True)
class ReleaseFacts:
    """The six release facts bound into a pack-release provenance statement.

    ``lock`` is a bounded projection of the resolved module graph
    (``{digest, modules}``) or ``None`` when the pack imports no modules;
    ``view_sets`` are the per-view set identities; ``sbom`` binds the generated
    SBOM's digest and format. ``source_revision`` and ``builder_id`` identify
    where and by whom the release was produced -- carried verbatim, never
    guessed, and ``source_revision`` may be ``None`` outside a version-controlled
    build. ``semantic_parent`` is the release's semantic parent, or ``None``.
    """

    semantic_parent: Mapping[str, object] | None
    source_revision: str | None
    builder_id: str
    lock: Mapping[str, object] | None
    view_sets: Sequence[Mapping[str, object]]
    sbom: Mapping[str, object]


def build_release_provenance(
    *,
    pack_name: str,
    pack_version: str,
    set_digest: str,
    facts: ReleaseFacts,
) -> dict[str, object]:
    """Build the in-toto pack-release provenance statement.

    ``set_digest`` is the release subject and ``facts`` carries the six release
    facts bound into the predicate (see :class:`ReleaseFacts`). The document is a
    deterministic function of its inputs and records no timestamp, so an
    unchanged release produces byte-identical provenance.
    """

    predicate: dict[str, object] = {
        "pack": {"name": pack_name, "version": pack_version},
        "source_revision": facts.source_revision,
        "builder": {"id": facts.builder_id},
        "lock": dict(facts.lock) if facts.lock is not None else None,
        "views": [dict(view) for view in facts.view_sets],
        "sbom": dict(facts.sbom),
    }
    if facts.semantic_parent is not None:
        predicate["semantic_parent"] = dict(facts.semantic_parent)
    return {
        "_type": STATEMENT_TYPE,
        "subject": [
            {
                "name": f"{pack_name}@{pack_version}",
                "digest": {SUBJECT_DIGEST_ALG: _subject_hex(set_digest)},
            }
        ],
        "predicateType": PREDICATE_TYPE,
        "predicate": predicate,
    }


def provenance_bytes(document: dict[str, object]) -> bytes:
    """Serialize provenance to canonical, reproducible UTF-8 JSON bytes."""

    return (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def provenance_digest(document: dict[str, object]) -> str:
    """Return the provenance statement's own canonical ``sha256:`` digest."""

    return "sha256:" + hashlib.sha256(provenance_bytes(document)).hexdigest()


def _predicate(document: dict[str, object]) -> dict[str, object]:
    """Return the statement predicate as a mapping, or an empty one."""

    predicate = document.get("predicate", {})
    return predicate if isinstance(predicate, dict) else {}


def _check_type(
    document: dict[str, object], diagnostics: list[validation.Diagnostic]
) -> None:
    """Bind the statement and predicate type identifiers."""

    if document.get("_type") != STATEMENT_TYPE:
        diagnostics.append(validation.Diagnostic("provenance.statement-type", path="$._type"))
    if document.get("predicateType") != PREDICATE_TYPE:
        diagnostics.append(validation.Diagnostic("provenance.predicate-type", path="$.predicateType"))


def _check_subject(
    document: dict[str, object],
    expected_set_digest: str,
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Bind the release subject digest."""

    subjects = document.get("subject")
    subject = subjects[0] if isinstance(subjects, list) and subjects else {}
    subject = subject if isinstance(subject, dict) else {}
    subject_digest = subject.get("digest", {}) if isinstance(subject.get("digest"), dict) else {}
    try:
        expected_hex: str | None = _subject_hex(expected_set_digest)
    except ValueError:
        expected_hex = None
    if expected_hex is None or subject_digest.get(SUBJECT_DIGEST_ALG) != expected_hex:
        diagnostics.append(validation.Diagnostic("provenance.subject-mismatch", path="$.subject[0].digest"))


def _check_pack(
    document: dict[str, object],
    expected_name: str,
    expected_version: str,
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Bind the pack name and version."""

    predicate = _predicate(document)
    pack = predicate.get("pack", {}) if isinstance(predicate.get("pack"), dict) else {}
    if pack.get("name") != expected_name or pack.get("version") != expected_version:
        diagnostics.append(validation.Diagnostic("provenance.pack-mismatch", path="$.predicate.pack"))


def _check_sbom(
    document: dict[str, object],
    expected_sbom_digest: str,
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Bind the generated SBOM's digest, and its presence."""

    sbom = _predicate(document).get("sbom", {})
    sbom = sbom if isinstance(sbom, dict) else {}
    if not sbom:
        diagnostics.append(validation.Diagnostic("provenance.binding-missing", path="$.predicate.sbom"))
    elif sbom.get("digest") != expected_sbom_digest:
        diagnostics.append(validation.Diagnostic("provenance.sbom-digest-mismatch", path="$.predicate.sbom.digest"))


def _check_source(
    document: dict[str, object],
    expected_source_revision: str | None,
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Bind the source revision, only when the consumer supplies one."""

    if expected_source_revision is None:
        return
    if _predicate(document).get("source_revision") != expected_source_revision:
        diagnostics.append(validation.Diagnostic("provenance.source-mismatch", path="$.predicate.source_revision"))


def _check_lock(
    document: dict[str, object],
    expected_lock_digest: str | None,
    diagnostics: list[validation.Diagnostic],
) -> None:
    """Bind the lock digest, only when the consumer supplies one."""

    if expected_lock_digest is None:
        return
    lock = _predicate(document).get("lock", {})
    lock = lock if isinstance(lock, dict) else {}
    if lock.get("digest") != expected_lock_digest:
        diagnostics.append(validation.Diagnostic("provenance.lock-mismatch", path="$.predicate.lock.digest"))


def validate_release_provenance(
    document: object,
    *,
    expected_name: str,
    expected_version: str,
    expected_set_digest: str,
    expected_sbom_digest: str,
    expected_source_revision: str | None = None,
    expected_lock_digest: str | None = None,
) -> list[validation.Diagnostic]:
    """Verify a provenance statement binds the expected release facts.

    Each binding is checked independently so a missing binding and a mismatched
    one are distinct, bounded diagnostics. ``expected_source_revision`` and
    ``expected_lock_digest`` are checked only when supplied, so a consumer that
    does not independently know them can still verify subject, pack, and SBOM
    bindings.
    """

    if not isinstance(document, dict):
        return [validation.Diagnostic("provenance.not-an-object", path="$")]
    diagnostics: list[validation.Diagnostic] = []
    _check_type(document, diagnostics)
    _check_subject(document, expected_set_digest, diagnostics)
    _check_pack(document, expected_name, expected_version, diagnostics)
    _check_sbom(document, expected_sbom_digest, diagnostics)
    _check_source(document, expected_source_revision, diagnostics)
    _check_lock(document, expected_lock_digest, diagnostics)
    return diagnostics


__all__ = [
    "PREDICATE_TYPE",
    "ReleaseFacts",
    "STATEMENT_TYPE",
    "SUBJECT_DIGEST_ALG",
    "build_release_provenance",
    "provenance_bytes",
    "provenance_digest",
    "validate_release_provenance",
]
