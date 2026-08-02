#!/usr/bin/env python3
"""End-to-end pack-distribution rehearsal (issue #191, ADR 0037).

Two rehearsals, one script:

* The **offline** rehearsal runs everywhere with no external tooling: it
  publishes TechVault, exports a deterministic archive, proves clean
  reproduction, then installs, verifies, updates, and reads rollback guidance
  through the archive route. This is the inner-loop confidence check.
* The **registry** rehearsal runs only when a real OCI registry is reachable and
  ``oras`` + ``cosign`` are installed (that is, in the ``pack-distribution``
  ``workflow_dispatch`` job, where a ``registry:2`` service and a keyless
  Sigstore OIDC identity exist). It pushes the release to the registry, signs the
  validated subject with keyless cosign, then pulls, verifies the signature, and
  installs -- the acceptance-criterion "clean consumer can install and verify"
  exercised against real transport and signing.

Nothing here is a unit test; ``tests/`` covers the library. This is the manually
triggered integration harness the workflow invokes.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_REPO, "src"))

from raes_env_packs import distribution as dist  # noqa: E402
from raes_env_packs import release, verify  # noqa: E402

_TECHVAULT = os.path.join(_REPO, "packs", "techvault")


def _log(message: str) -> None:
    print(f"[rehearsal] {message}", flush=True)


def _publish(workdir: str) -> tuple[str, str]:
    """Publish TechVault and return (evidence_dir, archive_path)."""

    release_out = os.path.join(workdir, "release")
    metadata, failures = release.build_release(_TECHVAULT, release_out, publish=True)
    if failures:
        raise SystemExit(f"publish failed: {failures}")
    evidence_dir = os.path.join(release_out, "techvault-0.1.0")
    archive = os.path.join(workdir, "techvault-0.1.0.tar.gz")
    first = dist.export_pack_archive(_TECHVAULT, archive)
    # Clean reproduction: the same source exports byte-identical bytes.
    again = os.path.join(workdir, "techvault-0.1.0-again.tar.gz")
    if dist.export_pack_archive(_TECHVAULT, again) != first:
        raise SystemExit("archive export is not reproducible")
    _log(f"published + exported archive {first}")
    return evidence_dir, archive


def offline_rehearsal(workdir: str) -> None:
    """Publish -> export -> install -> verify -> update -> rollback, no network."""

    evidence_dir, archive = _publish(workdir)
    selector = dist.Selector(
        repository="local", reference=archive, digest_domain=dist.DIGEST_DOMAIN_ARCHIVE)
    transport = dist.ArchiveTransport()
    target = os.path.join(workdir, "consumer", "techvault")

    install = dist.plan_install(
        _TECHVAULT, evidence_dir, target, selector=selector, transport=transport)
    if not install.applicable:
        raise SystemExit(f"install plan not applicable: {install.render_human()}")
    # The offline route carries no signature; accept unsigned explicitly. The
    # authenticated path is exercised by the registry rehearsal.
    receipt = dist.apply_install(
        install, _TECHVAULT, evidence_dir, target,
        authorized=True, selector=selector, transport=transport,
        require_signature=False)
    _log(f"installed; receipt subject {receipt['subject']['digest']}")

    result = dist.plan_verify(target, evidence_dir).verification
    if not result.accepted:
        raise SystemExit("installed pack did not verify")
    _log("installed pack verifies")

    update = dist.plan_update(
        target, _TECHVAULT, evidence_dir, selector=selector, transport=transport)
    _log(f"update plan changes: {[c.category for c in update.changes]}")
    dist.apply_install(
        update, _TECHVAULT, evidence_dir, target,
        authorized=True, selector=selector, transport=transport,
        require_signature=False)

    prior = dist.read_receipt(target)
    if prior is None or prior.get("subject", {}).get("digest") is None:
        raise SystemExit("no receipt for rollback guidance")
    _log(f"rollback guidance available: pinned subject {prior['subject']['digest']}")
    _log("OFFLINE REHEARSAL PASSED")


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    _log("$ " + " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, **kwargs)


def registry_rehearsal(registry: str, workdir: str) -> None:
    """Push -> keyless-sign -> pull -> verify-signature -> install, over a registry."""

    evidence_dir, archive = _publish(workdir)
    repo = f"{registry}/techvault"
    tag = "0.1.0"
    ref = f"{repo}:{tag}"

    # Stage the archive and its evidence together so oras pushes one artifact.
    push_dir = os.path.join(workdir, "push")
    os.makedirs(push_dir, exist_ok=True)
    shutil.copy(archive, push_dir)
    evidence_files = [
        ("release.yaml", "application/yaml"),
        ("techvault-0.1.0.cdx.json", "application/vnd.cyclonedx+json"),
        ("techvault-0.1.0.provenance.json", "application/vnd.in-toto+json"),
    ]
    for name, _media in evidence_files:
        shutil.copy(os.path.join(evidence_dir, name), push_dir)
    _run(
        ["oras", "push", "--plain-http", ref,
         f"{os.path.basename(archive)}:application/gzip",
         *[f"{name}:{media}" for name, media in evidence_files]],
        cwd=push_dir, capture_output=True)
    # oras prints the pushed manifest digest; resolve it explicitly to sign by digest.
    digest = subprocess.run(
        ["oras", "resolve", "--plain-http", ref],
        check=True, text=True, capture_output=True).stdout.strip()
    by_digest = f"{repo}@{digest}"
    _log(f"pushed {ref} -> {by_digest}")

    # Keyless Sigstore signature over the OCI subject (OIDC identity in CI).
    _run(["cosign", "sign", "--yes", "--allow-http-registry", by_digest],
         capture_output=True)
    _log("cosign keyless signature created")

    identity = os.environ.get(
        "REHEARSAL_CERT_IDENTITY_REGEXP", "https://github.com/OpenRAE/.+")
    issuer = os.environ.get(
        "REHEARSAL_CERT_OIDC_ISSUER", "https://token.actions.githubusercontent.com")

    def cosign_verifier(subject_set_digest: str, provenance: dict) -> bool:
        """Verify the cosign signature and that provenance binds the subject."""

        try:
            _run(["cosign", "verify", "--allow-http-registry",
                  "--certificate-identity-regexp", identity,
                  "--certificate-oidc-issuer", issuer, by_digest],
                 capture_output=True)
        except subprocess.CalledProcessError:
            return False
        subject = provenance.get("subject", [{}])[0].get("digest", {})
        return subject.get("raesAssociatedArtifactSet") == subject_set_digest.split(":", 1)[-1]

    # Pull into a clean consumer. The pulled bytes and pulled evidence — never the
    # local source tree — are the only inputs to verification and install, so this
    # proves a clean consumer can install exactly what the registry served.
    pulled = os.path.join(workdir, "pulled")
    os.makedirs(pulled, exist_ok=True)
    _run(["oras", "pull", "--plain-http", ref], cwd=pulled, capture_output=True)
    pulled_archive = os.path.join(pulled, os.path.basename(archive))
    if not os.path.isfile(pulled_archive):
        raise SystemExit("pulled artifact is missing the pack archive")

    # Stage the pulled archive into a clean, pack-named consumer directory and
    # verify those staged bytes against the pulled evidence (release.yaml + SBOM +
    # provenance now live under `pulled/`).
    staged = os.path.join(workdir, "consumer", "techvault")
    os.makedirs(os.path.dirname(staged), exist_ok=True)
    dist.stage_pack_archive(pulled_archive, staged)
    profile, sbom_doc, prov_doc = verify.load_release_evidence(pulled)
    result = verify.verify_pack_release(
        staged, release_profile=profile, sbom_document=sbom_doc,
        provenance_document=prov_doc, signature_verifier=cosign_verifier)
    if not (result.accepted and result.authenticated):
        raise SystemExit(f"pulled release failed verification: "
                         f"accepted={result.accepted} authenticated={result.authenticated}")
    _log("pulled release verified (content + authenticity)")

    # Clean-consumer install of the pulled release, signature required.
    selector = dist.Selector(
        repository=repo, reference=pulled_archive, digest_domain=dist.DIGEST_DOMAIN_ARCHIVE)
    transport = dist.ArchiveTransport()
    target = os.path.join(workdir, "installed", "techvault")
    plan = dist.plan_install(
        staged, pulled, target, selector=selector, transport=transport,
        signature_verifier=cosign_verifier)
    dist.apply_install(
        plan, staged, pulled, target, authorized=True,
        selector=selector, transport=transport,
        signature_verifier=cosign_verifier, require_signature=True)
    _log("clean consumer installed the pulled, signed release")
    _log("REGISTRY REHEARSAL PASSED")


def main() -> int:
    with tempfile.TemporaryDirectory() as workdir:
        offline_rehearsal(os.path.join(workdir, "offline"))
        registry = os.environ.get("REHEARSAL_REGISTRY")
        have_tools = shutil.which("oras") and shutil.which("cosign")
        if registry and have_tools:
            registry_rehearsal(registry, os.path.join(workdir, "registry"))
        else:
            _log("registry rehearsal skipped (set REHEARSAL_REGISTRY + install oras/cosign)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
