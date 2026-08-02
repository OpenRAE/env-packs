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


def build_release_provenance(
    *,
    pack_name: str,
    pack_version: str,
    set_digest: str,
    semantic_parent: Mapping[str, object] | None,
    source_revision: str | None,
    builder_id: str,
    lock: Mapping[str, object] | None,
    view_sets: Sequence[Mapping[str, object]],
    sbom: Mapping[str, object],
) -> dict:
    """Build the in-toto pack-release provenance statement.

    ``set_digest`` is the release subject. ``lock`` is a bounded projection of the
    resolved module graph (``{digest, modules}``) or ``None`` when the pack imports
    no modules; ``view_sets`` are the per-view set identities; ``sbom`` binds the
    generated SBOM's digest and format. ``source_revision`` and ``builder_id``
    identify where and by whom the release was produced -- carried verbatim, never
    guessed, and ``source_revision`` may be ``None`` outside a version-controlled
    build.
    """

    predicate: dict = {
        "pack": {"name": pack_name, "version": pack_version},
        "source_revision": source_revision,
        "builder": {"id": builder_id},
        "lock": dict(lock) if lock is not None else None,
        "views": [dict(view) for view in view_sets],
        "sbom": dict(sbom),
    }
    if semantic_parent is not None:
        predicate["semantic_parent"] = dict(semantic_parent)
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


def provenance_bytes(document: dict) -> bytes:
    """Serialize provenance to canonical, reproducible UTF-8 JSON bytes."""

    return (
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")


def provenance_digest(document: dict) -> str:
    """Return the provenance statement's own canonical ``sha256:`` digest."""

    return "sha256:" + hashlib.sha256(provenance_bytes(document)).hexdigest()


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
    if document.get("_type") != STATEMENT_TYPE:
        diagnostics.append(validation.Diagnostic("provenance.statement-type", path="$._type"))
    if document.get("predicateType") != PREDICATE_TYPE:
        diagnostics.append(validation.Diagnostic("provenance.predicate-type", path="$.predicateType"))

    subjects = document.get("subject")
    subject = subjects[0] if isinstance(subjects, list) and subjects else {}
    subject = subject if isinstance(subject, dict) else {}
    subject_digest = subject.get("digest", {}) if isinstance(subject.get("digest"), dict) else {}
    try:
        expected_hex = _subject_hex(expected_set_digest)
    except ValueError:
        expected_hex = None
    if expected_hex is None or subject_digest.get(SUBJECT_DIGEST_ALG) != expected_hex:
        diagnostics.append(validation.Diagnostic("provenance.subject-mismatch", path="$.subject[0].digest"))

    predicate = document.get("predicate", {})
    predicate = predicate if isinstance(predicate, dict) else {}
    pack = predicate.get("pack", {}) if isinstance(predicate.get("pack"), dict) else {}
    if pack.get("name") != expected_name or pack.get("version") != expected_version:
        diagnostics.append(validation.Diagnostic("provenance.pack-mismatch", path="$.predicate.pack"))

    sbom = predicate.get("sbom", {}) if isinstance(predicate.get("sbom"), dict) else {}
    if not sbom:
        diagnostics.append(validation.Diagnostic("provenance.binding-missing", path="$.predicate.sbom"))
    elif sbom.get("digest") != expected_sbom_digest:
        diagnostics.append(validation.Diagnostic("provenance.sbom-digest-mismatch", path="$.predicate.sbom.digest"))

    if expected_source_revision is not None and predicate.get("source_revision") != expected_source_revision:
        diagnostics.append(validation.Diagnostic("provenance.source-mismatch", path="$.predicate.source_revision"))

    if expected_lock_digest is not None:
        lock = predicate.get("lock", {}) if isinstance(predicate.get("lock"), dict) else {}
        if lock.get("digest") != expected_lock_digest:
            diagnostics.append(validation.Diagnostic("provenance.lock-mismatch", path="$.predicate.lock.digest"))
    return diagnostics


__all__ = [
    "PREDICATE_TYPE",
    "STATEMENT_TYPE",
    "SUBJECT_DIGEST_ALG",
    "build_release_provenance",
    "provenance_bytes",
    "provenance_digest",
    "validate_release_provenance",
]
