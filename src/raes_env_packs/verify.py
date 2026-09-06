#!/usr/bin/env python3
"""Consumer verification of a pack release before promotion (ADR 0037, ASP-0004).

Before an install or update is accepted, the same staged bytes must pass every
applicable gate: shared static validation, full RAES associated-artifact byte
binding, release signature/attestation, release provenance, SBOM integrity and
subject binding, RAES lock drift, and publication-profile agreement. This module
runs those gates over already-acquired bytes and reports the outcome as a
structured result that keeps *evidence observations* separate from *blocking
diagnostics*.

Crucially, it keeps five evidence states distinct rather than collapsing them
into a boolean or a caught exception (ADR 0037):

* ``absent`` -- the evidence was not published;
* ``unavailable`` -- a verifier, registry, or policy authority is unavailable;
* ``unverified`` -- evidence is present but was not verified;
* ``failed`` -- verification was attempted and failed; and
* ``verified`` -- verified under the named subject.

Signature and module-signature verification depend on external tooling (cosign,
the RAES module registry) that a caller injects; when no verifier is supplied
those gates are ``unavailable``, never silently passed. The library performs no
network access, executes no pack code, and does not log; unexpected programming
defects remain tool failures rather than being relabeled an untrusted pack.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import sys
from collections.abc import Callable, Mapping
from typing import TextIO


from . import digest as digest_module
from . import publication as publication_module
from . import release_provenance
from . import sbom as sbom_module
from . import validation
from . import _pack_fs
from ._authoring_safety import sensitive_member

STATE_ABSENT = "absent"
STATE_UNAVAILABLE = "unavailable"
STATE_UNVERIFIED = "unverified"
STATE_FAILED = "failed"
STATE_VERIFIED = "verified"

GATE_STATIC = "static-validation"
GATE_CONTENT_BINDING = "content-binding"
GATE_PUBLICATION = "publication-profile"
GATE_SBOM = "sbom"
GATE_PROVENANCE = "provenance"
GATE_RELEASE_SIGNATURE = "release-signature"
GATE_LOCK = "lock"
GATE_MODULE_SIGNATURE = "module-signature"

# Gates whose evidence must be ``verified`` before a release is accepted for
# promotion. Signature gates are reported but their policy is the caller's:
# an offline verifier may accept content while requiring authentication
# separately (see ``authenticated``).
_CORE_GATES = (GATE_STATIC, GATE_CONTENT_BINDING, GATE_PUBLICATION, GATE_SBOM, GATE_PROVENANCE)

# A signature verifier receives the release subject (the RAES set digest) and the
# provenance statement, and returns True only when the signature/attestation over
# that subject verifies under the caller's trust policy.
SignatureVerifier = Callable[[str, Mapping[str, object]], bool]


@dataclasses.dataclass(frozen=True)
class Evidence(object):
    """One gate observation: which gate, which of the five states, and why."""

    gate: str
    state: str
    detail: str


@dataclasses.dataclass(frozen=True)
class VerificationResult(object):
    """The result of verifying one release: evidence plus blocking diagnostics."""

    subject: str | None
    evidence: tuple[Evidence, ...]
    diagnostics: tuple[validation.Diagnostic, ...]

    def by_gate(self) -> dict[str, Evidence]:
        """Map each gate name to its observation."""

        return {item.gate: item for item in self.evidence}

    @property
    def failed(self) -> tuple[Evidence, ...]:
        """The gates whose verification was attempted and failed."""

        return tuple(item for item in self.evidence if item.state == STATE_FAILED)

    @property
    def accepted(self) -> bool:
        """True when every core content gate verified and nothing failed.

        Signature authenticity is reported separately; a caller that requires it
        checks :attr:`authenticated`. A release with any failed gate or any
        blocking diagnostic is never accepted.
        """

        if self.diagnostics or self.failed:
            return False
        states = {item.gate: item.state for item in self.evidence}
        return all(states.get(gate) == STATE_VERIFIED for gate in _CORE_GATES)

    @property
    def authenticated(self) -> bool:
        """True when the release signature/attestation verified over the subject."""

        signature = self.by_gate().get(GATE_RELEASE_SIGNATURE)
        return signature is not None and signature.state == STATE_VERIFIED


def _sha256_file(root: str, *parts: str) -> str | None:
    """Return the canonical ``sha256:`` digest of ``root``/``parts``, or ``None``.

    ``root`` is trusted and ``parts`` are relative; the joined path is resolved and
    confirmed to stay inside ``root`` *in this function*, so the exact value that
    reaches the ``open`` sink is the containment-validated realpath (Sonar
    pythonsecurity:S8707). A path that escapes ``root`` or is absent yields
    ``None``.
    """

    root_real = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_real, *parts))
    if candidate != root_real and os.path.commonpath([root_real, candidate]) != root_real:
        return None
    if not os.path.isfile(candidate):
        return None
    hasher = hashlib.sha256()
    with open(candidate, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def load_release_evidence(
    evidence_dir: str | os.PathLike[str],
) -> tuple[dict | None, dict | None, dict | None]:
    """Load ``release.yaml`` and the SBOM/provenance it references.

    Returns ``(profile, sbom_document, provenance_document)``. A missing profile
    yields ``(None, None, None)``; a profile without an evidence block yields the
    profile with ``None`` documents, which the verifier reports as ``absent``
    rather than an error.
    """

    limits = validation.PackValidationLimits()
    try:
        _root, root_fd = _pack_fs.open_root(evidence_dir)
    except _pack_fs.PackFilesystemError:
        return None, None, None
    try:
        errors = validation._Errors(limits)
        profile = validation._load_yaml_member(root_fd, "release.yaml", limits, errors)
        profile = profile if isinstance(profile, dict) and errors.result().ok else None
        evidence = profile.get("evidence") if profile is not None else None
        return (profile, _load_json_pointer(root_fd, evidence, "sbom", limits),
                _load_json_pointer(root_fd, evidence, "provenance", limits))
    finally:
        os.close(root_fd)


def _load_json_pointer(
    root_fd: int, evidence: object, key: str, limits: validation.PackValidationLimits,
) -> dict | None:
    """Load one evidence document referenced by ``evidence[key].path``.

    Read through the same root descriptor, refusing links, special files,
    escaping paths, duplicate keys and oversized documents before use.
    """

    ref = evidence.get(key) if isinstance(evidence, dict) else None
    rel = ref.get("path") if isinstance(ref, dict) else None
    if not isinstance(rel, str) or sensitive_member(rel):
        return None
    errors = validation._Errors(limits)
    document = validation._strict_json_member(root_fd, rel, limits, errors)
    return document if isinstance(document, dict) and errors.result().ok else None


def _static_gate(pack_root: str) -> Evidence:
    """Shared consumer static validation through ``validate_pack``."""

    try:
        result = validation.validate_pack(pack_root)
    except (OSError, ValueError):
        return Evidence(GATE_STATIC, STATE_FAILED, "pack could not be statically validated")
    if result.ok:
        return Evidence(GATE_STATIC, STATE_VERIFIED, "pack passes static validation")
    return Evidence(GATE_STATIC, STATE_FAILED, "pack failed static validation")


def _content_gate(pack_root: str) -> tuple[Evidence, object | None]:
    """Full RAES associated-artifact byte binding; establishes the subject."""

    try:
        manifest = digest_module.validate_pack_content_manifest(pack_root)
    except (digest_module.PackDigestError, OSError, ValueError):
        return Evidence(GATE_CONTENT_BINDING, STATE_FAILED, "content identity did not byte-bind"), None
    return (
        Evidence(GATE_CONTENT_BINDING, STATE_VERIFIED, "associated-artifact set byte-bound"),
        manifest,
    )


def _publication_gate(profile: object, name: str, version: str, set_digest: str) -> Evidence:
    """The release profile must be the current carrier and name this release."""

    if not isinstance(profile, dict):
        return Evidence(GATE_PUBLICATION, STATE_ABSENT, "no release profile supplied")
    if profile.get("schema_version") != publication_module.PUBLICATION_SCHEMA_VERSION:
        return Evidence(GATE_PUBLICATION, STATE_FAILED, "release profile is not the current carrier")
    identity = publication_module.release_identity(profile)
    pack = identity.get("pack") if isinstance(identity.get("pack"), dict) else {}
    source_set = identity.get("source_set") if isinstance(identity.get("source_set"), dict) else {}
    if pack.get("name") != name or pack.get("version") != version:
        result = Evidence(GATE_PUBLICATION, STATE_FAILED, "release profile names a different pack")
    elif source_set.get("set_digest") != set_digest:
        result = Evidence(GATE_PUBLICATION, STATE_FAILED, "release profile binds a different set digest")
    else:
        result = Evidence(GATE_PUBLICATION, STATE_VERIFIED, "release profile matches the verified subject")
    return result


def _evidence_ref(profile: object, key: str) -> dict | None:
    """Return the ``evidence[key]`` reference mapping from ``profile``, or ``None``."""

    evidence = profile.get("evidence") if isinstance(profile, dict) else None
    ref = evidence.get(key) if isinstance(evidence, dict) else None
    return ref if isinstance(ref, dict) else None


def _sbom_gate(profile: object, sbom_document: object, name: str, version: str, set_digest: str) -> Evidence:
    """SBOM must integrity-match the profile reference and bind the subject."""

    ref = _evidence_ref(profile, "sbom")
    if ref is None:
        return Evidence(GATE_SBOM, STATE_ABSENT, "no SBOM referenced by the release")
    if not isinstance(sbom_document, dict):
        return Evidence(GATE_SBOM, STATE_UNVERIFIED, "SBOM referenced but not supplied")

    component = sbom_document.get("metadata", {}).get("component", {})
    subject = {
        item.get("name"): item.get("value")
        for item in component.get("properties", [])
        if isinstance(item, dict)
    }
    if sbom_module.sbom_digest(sbom_document) != ref.get("digest"):
        result = Evidence(GATE_SBOM, STATE_FAILED, "SBOM bytes do not match the referenced digest")
    elif component.get("name") != name or component.get("version") != version:
        result = Evidence(GATE_SBOM, STATE_FAILED, "SBOM subject names a different pack")
    elif subject.get("raes:associated-artifact-set-digest") != set_digest:
        result = Evidence(GATE_SBOM, STATE_FAILED, "SBOM subject binds a different set digest")
    else:
        result = Evidence(GATE_SBOM, STATE_VERIFIED, "SBOM integrity and subject verified")
    return result


def _provenance_gate(
    profile: object, provenance_document: object, name: str, version: str,
    set_digest: str,
) -> Evidence:
    """Provenance must integrity-match the reference and bind subject + SBOM."""

    ref = _evidence_ref(profile, "provenance")
    sbom_ref = _evidence_ref(profile, "sbom")
    if ref is None:
        return Evidence(GATE_PROVENANCE, STATE_ABSENT, "no provenance referenced by the release")
    if not isinstance(provenance_document, dict):
        return Evidence(GATE_PROVENANCE, STATE_UNVERIFIED, "provenance referenced but not supplied")

    expected_sbom = sbom_ref.get("digest") if isinstance(sbom_ref, dict) else None
    if release_provenance.provenance_digest(provenance_document) != ref.get("digest"):
        result = Evidence(GATE_PROVENANCE, STATE_FAILED, "provenance bytes do not match the referenced digest")
    else:
        diagnostics = release_provenance.validate_release_provenance(
            provenance_document, expected_name=name, expected_version=version,
            expected_set_digest=set_digest, expected_sbom_digest=expected_sbom or "")
        if diagnostics:
            result = Evidence(GATE_PROVENANCE, STATE_FAILED, "provenance bindings do not match the subject")
        else:
            result = Evidence(GATE_PROVENANCE, STATE_VERIFIED, "provenance binds subject, SBOM, and lock")
    return result


def _signature_gate(set_digest: str, provenance_document: object, verifier: SignatureVerifier | None) -> Evidence:
    """Release signature/attestation over the subject, via an injected verifier."""

    if verifier is None:
        return Evidence(GATE_RELEASE_SIGNATURE, STATE_UNAVAILABLE, "no signature verifier configured")
    provenance = provenance_document if isinstance(provenance_document, dict) else {}
    # A broad catch is deliberate: an external verifier failure is a failed gate,
    # not a tool crash.
    try:
        ok = verifier(set_digest, provenance)
    except Exception:
        return Evidence(GATE_RELEASE_SIGNATURE, STATE_FAILED, "signature verification raised")
    return Evidence(
        GATE_RELEASE_SIGNATURE,
        STATE_VERIFIED if ok else STATE_FAILED,
        "release signature verified" if ok else "release signature did not verify",
    )


def _lock_gate(pack_root: str, provenance_document: object) -> Evidence:
    """RAES lock drift: the staged lock must match the attested lock digest.

    ``pack_root`` is external, so ``_sha256_file`` resolves the staged lock path
    and confirms it stays inside the pack before any bytes reach the hash sink. A
    path that escapes that boundary -- for instance a lock symlinked out of the
    pack -- yields digest ``None``, collapsing into the same absent/failed handling
    as a genuinely missing lock rather than reading bytes from outside the pack.
    """

    lock_digest = _sha256_file(pack_root, "sdl", "raes.lock.json")
    predicate = provenance_document.get("predicate", {}) if isinstance(provenance_document, dict) else {}
    attested = predicate.get("lock") if isinstance(predicate.get("lock"), dict) else None
    attested_digest = attested.get("digest") if isinstance(attested, dict) else None

    if lock_digest is None and not attested_digest:
        result = Evidence(GATE_LOCK, STATE_ABSENT, "pack imports no modules")
    elif lock_digest is None or attested_digest is None:
        result = Evidence(GATE_LOCK, STATE_FAILED, "lock presence disagrees with the attested lock")
    elif lock_digest != attested_digest:
        result = Evidence(GATE_LOCK, STATE_FAILED, "raes.lock.json has drifted from the attested digest")
    else:
        result = Evidence(GATE_LOCK, STATE_VERIFIED, "raes.lock.json matches the attested digest")
    return result


def verify_pack_release(
    pack_root: str | os.PathLike[str],
    *,
    release_profile: object,
    sbom_document: object = None,
    provenance_document: object = None,
    signature_verifier: SignatureVerifier | None = None,
    module_signature_verifier: SignatureVerifier | None = None,
) -> VerificationResult:
    """Verify an acquired pack release against every applicable gate.

    ``pack_root`` is the already-staged source pack; ``release_profile`` and the
    SBOM/provenance documents are its release evidence. The result reports each
    gate's evidence state and any blocking diagnostics; a caller promotes only a
    result that is :attr:`~VerificationResult.accepted`, and additionally
    :attr:`~VerificationResult.authenticated` when its policy requires a verified
    signature.
    """

    pack_root = os.fspath(pack_root)
    evidence: list[Evidence] = []
    diagnostics: list[validation.Diagnostic] = []

    static = _static_gate(pack_root)
    evidence.append(static)

    content, manifest = _content_gate(pack_root)
    evidence.append(content)
    if manifest is None:
        # Without a byte-bound subject the remaining gates have nothing to bind
        # to; report them absent so the five states stay meaningful.
        for gate in (GATE_PUBLICATION, GATE_SBOM, GATE_PROVENANCE, GATE_LOCK):
            evidence.append(Evidence(gate, STATE_ABSENT, "no verified subject to bind"))
        evidence.append(Evidence(GATE_RELEASE_SIGNATURE, STATE_ABSENT, "no verified subject to bind"))
        return VerificationResult(subject=None, evidence=tuple(evidence), diagnostics=tuple(diagnostics))

    name = manifest.parent_ref.ref_id
    version = manifest.manifest_version
    set_digest = manifest.set_digest

    evidence.append(_publication_gate(release_profile, name, version, set_digest))
    evidence.append(_sbom_gate(release_profile, sbom_document, name, version, set_digest))
    evidence.append(_provenance_gate(release_profile, provenance_document, name, version, set_digest))
    evidence.append(_signature_gate(set_digest, provenance_document, signature_verifier))
    evidence.append(_lock_gate(pack_root, provenance_document))
    if module_signature_verifier is not None:
        module_ok = _signature_gate(set_digest, provenance_document, module_signature_verifier)
        evidence.append(Evidence(GATE_MODULE_SIGNATURE, module_ok.state, "module signatures " + module_ok.detail))
    else:
        evidence.append(Evidence(GATE_MODULE_SIGNATURE, STATE_UNAVAILABLE, "no module-signature verifier configured"))

    return VerificationResult(subject=set_digest, evidence=tuple(evidence), diagnostics=tuple(diagnostics))


# --------------------------------------------------------------------------- #
# CLI (stable human + JSON projection, 0/1/2/3 exit contract, ADR 0031)
# --------------------------------------------------------------------------- #
ENVELOPE_VERSION = "raes-pack-verify/v1"
EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_USAGE = 2
EXIT_TOOL_FAILURE = 3


def render_json(result: VerificationResult, *, require_signature: bool) -> str:
    """Render one verification result as the stable JSON envelope."""

    document = {
        "version": ENVELOPE_VERSION,
        "accepted": result.accepted and (result.authenticated or not require_signature),
        "content_accepted": result.accepted,
        "authenticated": result.authenticated,
        "subject": result.subject,
        "evidence": [
            {"gate": item.gate, "state": item.state, "detail": item.detail}
            for item in result.evidence
        ],
        "diagnostics": [
            {"code": item.code, "path": item.path} for item in result.diagnostics
        ],
    }
    return json.dumps(document, indent=2, sort_keys=True)


def render_human(result: VerificationResult, *, require_signature: bool) -> str:
    """Render one verification result as readable text."""

    lines = [f"subject: {result.subject or '(none)'}"]
    for item in result.evidence:
        lines.append(f"  [{item.state:12}] {item.gate:20} {item.detail}")
    accepted = result.accepted and (result.authenticated or not require_signature)
    lines.append("ACCEPTED" if accepted else "REJECTED")
    return "\n".join(lines)


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    """Command-line entry point for consumer verification."""

    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    parser = argparse.ArgumentParser(
        prog="raes-pack-verify",
        description="Verify an acquired pack release before install/update.",
    )
    parser.add_argument("--pack", required=True, help="staged source pack directory")
    parser.add_argument(
        "--release", required=True,
        help="release directory containing release.yaml and its evidence files")
    parser.add_argument("--json", action="store_true", help="emit the JSON envelope")
    parser.add_argument(
        "--require-signature", action="store_true",
        help="reject unless the release signature/attestation verifies")
    args = parser.parse_args(argv)

    # A broad catch is deliberate: an unexpected defect here is a tool failure
    # (exit 3), not a signal that the pack is untrusted.
    try:
        profile, sbom_document, provenance_document = load_release_evidence(args.release)
        result = verify_pack_release(
            args.pack, release_profile=profile,
            sbom_document=sbom_document, provenance_document=provenance_document)
    except Exception as exc:
        print(f"raes-pack-verify: internal error ({type(exc).__name__})", file=err)
        return EXIT_TOOL_FAILURE

    render = render_json if args.json else render_human
    print(render(result, require_signature=args.require_signature), file=out)
    accepted = result.accepted and (result.authenticated or not args.require_signature)
    return EXIT_OK if accepted else EXIT_BLOCKING


__all__ = [
    "Evidence",
    "SignatureVerifier",
    "VerificationResult",
    "GATE_CONTENT_BINDING",
    "GATE_LOCK",
    "GATE_MODULE_SIGNATURE",
    "GATE_PROVENANCE",
    "GATE_PUBLICATION",
    "GATE_RELEASE_SIGNATURE",
    "GATE_SBOM",
    "GATE_STATIC",
    "STATE_ABSENT",
    "STATE_FAILED",
    "STATE_UNAVAILABLE",
    "STATE_UNVERIFIED",
    "STATE_VERIFIED",
    "load_release_evidence",
    "main",
    "verify_pack_release",
]
