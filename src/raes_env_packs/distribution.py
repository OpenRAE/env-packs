#!/usr/bin/env python3
"""Proposal-first pack distribution: install, update, lock, verify, publish.

ADR 0037 gives distribution one workflow and one result discipline. A *silent*
library produces an immutable, inspectable :class:`OperationPlan`; human, JSON,
Hub, and MCP adapters render that same record. Network, billable, credential,
signing, registry-write, and local filesystem writes are explicit *effects* --
no effect occurs merely because a plan was requested. Applying a plan requires
explicit authorization of that exact proposal, rechecks preconditions, and (for
install and update) verifies the staged bytes against every gate before an atomic
promotion that never deletes or overlays the live target.

A remote selector's mutable tag or channel is resolved to an immutable digest
before any write is confirmed, and every digest is domain-tagged (a RAES
associated-artifact *set* digest, an OCI *manifest* digest, and an *archive*
digest share the ``sha256:`` spelling and must never be confused). Registry
endpoints, credentials, and signing identities are operator configuration, never
portable content: they stay out of plans, receipts, and machine output. A local
CLI is not an authentication boundary; Hub and MCP adapters authenticate and
authorize before invoking this library.
"""

from __future__ import annotations

import argparse
import dataclasses
import gzip
import hashlib
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Protocol

from . import _pack_fs
from . import _transactions
from . import validation
from . import verify as verify_module

# Digest domains. A selector and every result state which domain a supplied
# digest belongs to, because all three spell ``sha256:`` (ADR 0037).
DIGEST_DOMAIN_SET = "raes-associated-artifact-set"
DIGEST_DOMAIN_OCI = "oci-manifest"
DIGEST_DOMAIN_ARCHIVE = "archive-sha256"

# Classified effects. None occurs for a plan; each requires authorization to apply.
EFFECT_NETWORK = "network"
EFFECT_FILESYSTEM_WRITE = "filesystem-write"
EFFECT_REGISTRY_WRITE = "registry-write"
EFFECT_SIGNING = "signing"
EFFECT_CREDENTIAL = "credential"
EFFECT_BILLABLE = "billable"

# Change categories a plan surfaces before applying (ADR 0037).
CHANGE_VERSION = "version"
CHANGE_DEPENDENCY = "dependency"
CHANGE_LOCK = "lock"
CHANGE_TRUST = "trust"
CHANGE_SBOM_SCOPE = "sbom-scope"
CHANGE_COMPATIBILITY = "compatibility"

RECEIPT_NAME = ".raes-pack-receipt.json"
RECEIPT_SCHEMA_VERSION = "environment-pack-install-receipt/v1"

OPERATION_INSTALL = "install"
OPERATION_UPDATE = "update"
OPERATION_LOCK = "lock"
OPERATION_VERIFY = "verify"
OPERATION_PUBLISH = "publish"


class DistributionError(ValueError):
    """One bounded distribution input or precondition failure (payload-free)."""


class TransportUnavailable(DistributionError):
    """A selected transport (registry, signer) is not available in this context."""


@dataclasses.dataclass(frozen=True)
class ArchiveLimits(object):
    """Bounds for safe archive ingestion (defense against resource exhaustion)."""

    max_members: int = 8192
    max_member_bytes: int = 256 * 1024 * 1024
    max_total_bytes: int = 1024 * 1024 * 1024


@dataclasses.dataclass(frozen=True)
class Selector(object):
    """What a distribution operation targets.

    ``reference`` is a mutable tag/channel or an immutable digest; ``digest_domain``
    names the domain of a digest reference. A remote selector is resolved to an
    immutable digest before any write is confirmed.
    """

    repository: str
    reference: str
    digest_domain: str | None = None


@dataclasses.dataclass(frozen=True)
class Effect(object):
    """One classified side effect a plan would cause if applied."""

    kind: str
    description: str


@dataclasses.dataclass(frozen=True)
class Change(object):
    """One proposed change surfaced before applying an update."""

    category: str
    before: str | None
    after: str | None


@dataclasses.dataclass(frozen=True)
class OperationPlan(object):
    """An immutable, inspectable record of a proposed distribution operation."""

    operation: str
    route: str
    selector: Selector | None
    resolved: dict
    changes: tuple[Change, ...]
    effects: tuple[Effect, ...]
    verification: verify_module.VerificationResult | None
    diagnostics: tuple[validation.Diagnostic, ...]

    @property
    def applicable(self) -> bool:
        """True when the plan has no blocking diagnostic and verified its bytes.

        A plan with an effect is still only *applicable*; applying it additionally
        requires explicit authorization.
        """

        if self.diagnostics:
            return False
        return self.verification is None or self.verification.accepted

    def render_json(self) -> str:
        """Render the plan as the stable JSON envelope for Hub/MCP delegation."""

        document = {
            "version": "raes-pack-dist/v1",
            "operation": self.operation,
            "route": self.route,
            "applicable": self.applicable,
            "selector": dataclasses.asdict(self.selector) if self.selector else None,
            "resolved": self.resolved,
            "changes": [dataclasses.asdict(change) for change in self.changes],
            "effects": [dataclasses.asdict(effect) for effect in self.effects],
            "verification": _verification_json(self.verification),
            "diagnostics": [
                {"code": item.code, "path": item.path} for item in self.diagnostics
            ],
        }
        return json.dumps(document, indent=2, sort_keys=True)

    def render_human(self) -> str:
        """Render the plan as readable text."""

        lines = [f"operation: {self.operation}  route: {self.route}"]
        if self.selector is not None:
            lines.append(f"selector: {self.selector.repository}@{self.selector.reference}")
        for key in sorted(self.resolved):
            lines.append(f"resolved.{key}: {self.resolved[key]}")
        for change in self.changes:
            lines.append(f"change[{change.category}]: {change.before} -> {change.after}")
        for effect in self.effects:
            lines.append(f"effect[{effect.kind}]: {effect.description}")
        if self.verification is not None:
            for item in self.verification.evidence:
                lines.append(f"  [{item.state:12}] {item.gate}")
        for item in self.diagnostics:
            lines.append(f"diagnostic: {item.code} {item.path or ''}")
        lines.append("APPLICABLE" if self.applicable else "NOT-APPLICABLE")
        return "\n".join(lines)


def _verification_json(result: verify_module.VerificationResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "accepted": result.accepted,
        "authenticated": result.authenticated,
        "subject": result.subject,
        "evidence": [
            {"gate": item.gate, "state": item.state} for item in result.evidence
        ],
    }


# --------------------------------------------------------------------------- #
# Deterministic archive route (offline, reproducible, safely ingested)
# --------------------------------------------------------------------------- #
def _sorted_regular_files(pack_root: str) -> list[str]:
    """Return pack-relative regular files in stable order, symlinks excluded."""

    out: list[str] = []
    for dirpath, dirs, files in os.walk(pack_root):
        dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(dirpath, d)))
        for name in sorted(files):
            full = os.path.join(dirpath, name)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            out.append(os.path.relpath(full, pack_root).replace(os.sep, "/"))
    return sorted(out)


def export_pack_archive(pack_root: str | os.PathLike[str], dest_path: str | os.PathLike[str]) -> str:
    """Write a byte-deterministic tar.gz of a pack and return its archive digest.

    Stable ordering, zeroed timestamps, fixed ownership, and normalized modes make
    the repository route and the archive route reproduce the same bytes, so the
    archive digest is a stable transport identity distinct from the RAES set
    digest.
    """

    pack_root = os.fspath(pack_root)
    dest_path = os.fspath(dest_path)
    members = _sorted_regular_files(pack_root)
    # gzip embeds an mtime and the source filename; pin both to empty so the
    # archive is byte-identical across builds and destinations.
    with open(dest_path, "wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for rel in members:
                    info = tarfile.TarInfo(name=rel)
                    full = os.path.join(pack_root, rel)
                    info.size = os.path.getsize(full)
                    info.mtime = 0
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.type = tarfile.REGTYPE
                    with open(full, "rb") as handle:
                        tar.addfile(info, handle)
    return archive_digest(dest_path)


def archive_digest(archive_path: str | os.PathLike[str]) -> str:
    """Return the canonical ``sha256:`` transport digest of an archive."""

    hasher = hashlib.sha256()
    with open(archive_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def stage_pack_archive(
    archive_path: str | os.PathLike[str],
    staging_dir: str | os.PathLike[str],
    *,
    limits: ArchiveLimits | None = None,
) -> None:
    """Safely extract a pack archive into an empty staging directory.

    Every archive member is checked before materialization: absolute or escaping
    paths, symlinks, hardlinks, character/block/fifo/device special files,
    duplicate normalized names, oversized members, an excessive member count, and
    an excessive expanded total all fail closed. Members are written with a fixed
    safe mode, never the archive's own, so a hostile archive cannot set an
    executable, set-id, or world-writable bit on extracted content.
    """

    active = limits or ArchiveLimits()
    staging = Path(staging_dir)
    seen: set[str] = set()
    count = 0
    total = 0
    with tarfile.open(archive_path, "r:*") as tar:
        for member in tar:
            count += 1
            if count > active.max_members:
                raise DistributionError("archive exceeds the member-count limit")
            if member.issym() or member.islnk():
                raise DistributionError("archive contains a link member")
            if member.ischr() or member.isblk() or member.isfifo() or member.isdev():
                raise DistributionError("archive contains a special-file member")
            if member.isdir():
                continue
            if not member.isfile():
                raise DistributionError("archive contains an unsupported member type")
            try:
                rel = _pack_fs.normalize_relpath(member.name, error_type=DistributionError)
            except DistributionError:
                raise DistributionError("archive member name is unsafe")
            if rel in seen:
                raise DistributionError("archive contains a duplicate member")
            seen.add(rel)
            if member.size > active.max_member_bytes:
                raise DistributionError("archive member exceeds the size limit")
            total += member.size
            if total > active.max_total_bytes:
                raise DistributionError("archive expands beyond the total-size limit")
            source = tar.extractfile(member)
            if source is None:
                raise DistributionError("archive member could not be read")
            target = staging / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as out:
                shutil.copyfileobj(source, out, length=65536)


def _stage_tree(src: str, staging: str) -> None:
    """Copy a trusted local pack tree into staging, excluding symlinks."""

    for rel in _sorted_regular_files(src):
        target = os.path.join(staging, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(os.path.join(src, rel), "rb") as source:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with open(fd, "wb") as out:
                shutil.copyfileobj(source, out, length=65536)


# --------------------------------------------------------------------------- #
# Transport seam (repository/archive offline; OCI via injected adapter)
# --------------------------------------------------------------------------- #
class Transport(Protocol):
    """The seam between deterministic evidence derivation and distribution.

    A concrete transport resolves a mutable selector to an immutable digest and
    stages the referenced bytes into a private directory. Registry and signing
    adapters (oras, cosign) implement this by shelling to those tools with bounded,
    adapted output; the offline archive/repository routes implement it directly.
    """

    def resolve(self, selector: Selector) -> str: ...

    def stage(self, selector: Selector, staging_dir: str) -> None: ...


@dataclasses.dataclass(frozen=True)
class ArchiveTransport(object):
    """The offline archive route: a selector reference is a local archive path."""

    def resolve(self, selector: Selector) -> str:
        return archive_digest(selector.reference)

    def stage(self, selector: Selector, staging_dir: str) -> None:
        stage_pack_archive(selector.reference, staging_dir)


# --------------------------------------------------------------------------- #
# Consumer receipt (drift detection + rollback guidance; outside pack files)
# --------------------------------------------------------------------------- #
def build_receipt(
    *,
    selector: Selector | None,
    transport_digest: str | None,
    result: verify_module.VerificationResult,
    evidence: dict | None,
) -> dict:
    """Build a consumer-local receipt for drift detection and rollback guidance.

    It records the resolved reference, the verified RAES subject, the transport
    digest, the evidence digests, and the verification observations. It is not a
    portable pack schema or lock, and it carries no credential or endpoint secret.
    """

    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "repository_reference": (
            {"repository": selector.repository, "reference": selector.reference}
            if selector else None
        ),
        "subject": {"digest": result.subject, "domain": DIGEST_DOMAIN_SET},
        "transport": {"digest": transport_digest, "domain": DIGEST_DOMAIN_ARCHIVE}
        if transport_digest else None,
        "evidence": {
            "sbom": (evidence or {}).get("sbom", {}).get("digest"),
            "provenance": (evidence or {}).get("provenance", {}).get("digest"),
        },
        "verification": [
            {"gate": item.gate, "state": item.state} for item in result.evidence
        ],
    }


def write_receipt(target_dir: str | os.PathLike[str], receipt: dict) -> None:
    """Write a receipt beside an installed pack, outside the pack's own files."""

    path = Path(target_dir).parent / f"{Path(target_dir).name}{RECEIPT_NAME}"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_receipt(target_dir: str | os.PathLike[str]) -> dict | None:
    """Read the receipt beside an installed pack, or ``None`` when absent."""

    path = Path(target_dir).parent / f"{Path(target_dir).name}{RECEIPT_NAME}"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Plans (no effects occur here)
# --------------------------------------------------------------------------- #
def _verify_staged(
    staging: str, evidence_dir: str,
    *, signature_verifier: verify_module.SignatureVerifier | None = None,
) -> verify_module.VerificationResult:
    """Load the release evidence and verify the staged bytes against it.

    ``signature_verifier`` is threaded through so a plan's verification reflects
    authenticity, not just content integrity, and so an apply can fail closed on
    an unauthenticated published release.
    """

    profile, sbom_document, provenance_document = verify_module.load_release_evidence(evidence_dir)
    return verify_module.verify_pack_release(
        staging, release_profile=profile,
        sbom_document=sbom_document, provenance_document=provenance_document,
        signature_verifier=signature_verifier)


def plan_verify(pack_root: str, evidence_dir: str) -> OperationPlan:
    """Plan a read-only verification of an acquired release (no effects)."""

    result = _verify_staged(pack_root, evidence_dir)
    return OperationPlan(
        operation=OPERATION_VERIFY, route="repository", selector=None,
        resolved={"subject": result.subject or "", "subject_domain": DIGEST_DOMAIN_SET},
        changes=(), effects=(), verification=result, diagnostics=())


def plan_lock(pack_root: str, evidence_dir: str) -> OperationPlan:
    """Plan the resolved, drift-detectable lock for reproducible installs.

    The lock surfaces the exact subject digest and, when present, the attested
    module lock digest a consumer pins against. It is read-only.
    """

    profile, _sbom, provenance = verify_module.load_release_evidence(evidence_dir)
    predicate = provenance.get("predicate", {}) if isinstance(provenance, dict) else {}
    lock = predicate.get("lock") if isinstance(predicate.get("lock"), dict) else None
    result = _verify_staged(pack_root, evidence_dir)
    resolved = {
        "subject": result.subject or "",
        "subject_domain": DIGEST_DOMAIN_SET,
        "lock_digest": (lock or {}).get("digest") or "",
    }
    return OperationPlan(
        operation=OPERATION_LOCK, route="repository", selector=None,
        resolved=resolved, changes=(), effects=(), verification=result, diagnostics=())


def plan_install(
    source: str,
    evidence_dir: str,
    target_dir: str,
    *,
    selector: Selector | None = None,
    transport: Transport | None = None,
    signature_verifier: verify_module.SignatureVerifier | None = None,
) -> OperationPlan:
    """Plan an install: stage, verify, and classify the filesystem effect.

    No bytes are promoted. The plan stages the source into a private scratch area,
    verifies it against its evidence, and records the exact target it authorizes,
    whether that target already existed, and (for a remote selector) the resolved
    immutable transport digest. ``apply_install`` binds to those recorded facts, so
    a plan cannot be applied to a different target or a drifted source.
    """

    diagnostics: list[validation.Diagnostic] = []
    effects = [Effect(EFFECT_FILESYSTEM_WRITE, f"write pack into {os.path.basename(target_dir)}")]
    resolved: dict = {"target": os.path.abspath(target_dir), "target_existed": os.path.exists(target_dir)}
    if selector is not None and transport is not None:
        effects.insert(0, Effect(EFFECT_NETWORK, f"fetch {selector.repository}"))
        resolved["transport_digest"] = transport.resolve(selector)
        resolved["transport_domain"] = selector.digest_domain or DIGEST_DOMAIN_OCI
    if resolved["target_existed"]:
        diagnostics.append(validation.Diagnostic("distribution.target-exists", path=target_dir))

    with tempfile.TemporaryDirectory() as scratch:
        # The staged directory is named after the pack: static validation requires
        # pack.yaml.name to equal the directory basename.
        staging = os.path.join(scratch, os.path.basename(os.path.abspath(target_dir)))
        os.makedirs(staging)
        _stage_source(source, staging, selector, transport)
        result = _verify_staged(staging, evidence_dir, signature_verifier=signature_verifier)
        resolved["subject"] = result.subject or ""
        resolved["subject_domain"] = DIGEST_DOMAIN_SET
    return OperationPlan(
        operation=OPERATION_INSTALL, route="archive" if selector else "repository",
        selector=selector, resolved=resolved, changes=(Change(CHANGE_VERSION, None, resolved.get("subject")),),
        effects=tuple(effects), verification=result, diagnostics=tuple(diagnostics))


def plan_update(
    current_target: str,
    source: str,
    evidence_dir: str,
    *,
    selector: Selector | None = None,
    transport: Transport | None = None,
    signature_verifier: verify_module.SignatureVerifier | None = None,
) -> OperationPlan:
    """Plan an update: show the proposed changes before applying them.

    Version, lock, SBOM-scope, and compatibility changes relative to the installed
    receipt are surfaced so a consumer sees exactly what an apply would alter. The
    plan records the exact target and resolved subject an apply is bound to.
    """

    receipt = read_receipt(current_target) or {}
    prior_subject = (receipt.get("subject") or {}).get("digest")
    prior_sbom = (receipt.get("evidence") or {}).get("sbom")

    with tempfile.TemporaryDirectory() as scratch:
        staging = os.path.join(scratch, os.path.basename(os.path.abspath(current_target)))
        os.makedirs(staging)
        _stage_source(source, staging, selector, transport)
        result = _verify_staged(staging, evidence_dir, signature_verifier=signature_verifier)

    profile, _sbom, provenance = verify_module.load_release_evidence(evidence_dir)
    new_sbom = (profile.get("evidence", {}).get("sbom", {}) if isinstance(profile, dict) else {}).get("digest")
    changes = [Change(CHANGE_VERSION, prior_subject, result.subject)]
    if prior_sbom != new_sbom:
        changes.append(Change(CHANGE_SBOM_SCOPE, prior_sbom, new_sbom))
    resolved = {
        "subject": result.subject or "", "subject_domain": DIGEST_DOMAIN_SET,
        "target": os.path.abspath(current_target), "target_existed": os.path.exists(current_target),
    }
    if selector is not None and transport is not None:
        resolved["transport_digest"] = transport.resolve(selector)
        resolved["transport_domain"] = selector.digest_domain or DIGEST_DOMAIN_OCI
    return OperationPlan(
        operation=OPERATION_UPDATE, route="archive" if selector else "repository",
        selector=selector, resolved=resolved, changes=tuple(changes),
        effects=(Effect(EFFECT_FILESYSTEM_WRITE, f"replace pack at {os.path.basename(current_target)}"),),
        verification=result, diagnostics=())


def plan_publish(
    release_root: str,
    *,
    selector: Selector,
    signed: bool = True,
) -> OperationPlan:
    """Plan a publish of a built release: classify the signing/registry effects.

    A publish is planned over an already-built published release tree (containing
    ``release.yaml`` and its evidence). Applying it would sign the locally
    validated subject and push it to the registry -- explicit signing, credential,
    registry-write, and network effects. No push happens while planning.
    """

    profile, _sbom, _provenance = verify_module.load_release_evidence(release_root)
    diagnostics: list[validation.Diagnostic] = []
    if not isinstance(profile, dict) or "evidence" not in profile:
        diagnostics.append(validation.Diagnostic("distribution.not-a-published-release", path=release_root))
    subject = ""
    if isinstance(profile, dict):
        source_set = profile.get("release", {}).get("source_set", {})
        subject = source_set.get("set_digest", "") if isinstance(source_set, dict) else ""
    effects = [
        Effect(EFFECT_NETWORK, f"contact {selector.repository}"),
        Effect(EFFECT_CREDENTIAL, "use registry credentials from the operator's helper"),
        Effect(EFFECT_REGISTRY_WRITE, f"push the release to {selector.repository}"),
    ]
    if signed:
        effects.append(Effect(EFFECT_SIGNING, "sign the validated set-digest subject"))
    return OperationPlan(
        operation=OPERATION_PUBLISH, route="oci", selector=selector,
        resolved={"subject": subject, "subject_domain": DIGEST_DOMAIN_SET},
        changes=(), effects=tuple(effects), verification=None, diagnostics=tuple(diagnostics))


def _stage_source(source: str, staging: str, selector, transport) -> None:
    """Stage the source bytes into ``staging`` via the archive or repository route."""

    if selector is not None and transport is not None:
        transport.stage(selector, staging)
    else:
        _stage_tree(source, staging)


# --------------------------------------------------------------------------- #
# Apply (effects occur only here, and only when authorized)
# --------------------------------------------------------------------------- #
def apply_install(
    plan: OperationPlan,
    source: str,
    evidence_dir: str,
    target_dir: str,
    *,
    authorized: bool,
    selector: Selector | None = None,
    transport: Transport | None = None,
    signature_verifier: verify_module.SignatureVerifier | None = None,
    require_signature: bool = True,
) -> dict:
    """Apply an install/update plan: re-verify staged bytes, then promote atomically.

    The apply is bound to the exact effect-bearing proposal, not merely to "some
    applicable plan":

    * only an install or update plan may be applied (a read-only ``verify``/
      ``lock`` or a ``publish`` plan is refused);
    * the supplied ``target_dir`` must equal the target the plan authorized, and
      the target-existence precondition the plan saw must still hold (an install
      refuses a target that appeared after planning; an update refuses a target
      that vanished);
    * the re-verified subject and, for a remote route, the resolved transport
      digest must equal the plan's, so a drifted source cannot be substituted.

    Promotion additionally **fails closed on authenticity**: a published release
    must verify its signature (``require_signature=True``, the default). Without a
    configured signature verifier the release-signature gate is ``unavailable``
    and the apply refuses rather than promoting integrity-only, self-consistent
    bytes an attacker without the signing identity could forge. A caller with no
    signing infrastructure opts out explicitly with ``require_signature=False``.

    Refuses unless the exact proposal was authorized. Promotes with a no-replace
    move for a fresh install or an atomic exchange for an update; the live target
    is never deleted or overlaid before replacement. Returns the written receipt.
    """

    if not authorized:
        raise DistributionError("apply requires explicit authorization of the plan")
    if plan.operation not in (OPERATION_INSTALL, OPERATION_UPDATE):
        raise DistributionError(f"apply requires an install or update plan, not {plan.operation}")
    if not plan.applicable:
        raise DistributionError("plan is not applicable; refusing to apply")
    if os.path.abspath(target_dir) != plan.resolved.get("target"):
        raise DistributionError("apply target does not match the authorized plan target")

    target_exists = os.path.exists(target_dir)
    if plan.operation == OPERATION_INSTALL and target_exists:
        raise DistributionError("install target now exists; re-plan before applying")
    if plan.operation == OPERATION_UPDATE and not target_exists:
        raise DistributionError("update target no longer exists; plan an install")

    parent = os.path.dirname(os.path.abspath(target_dir)) or "."
    os.makedirs(parent, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix=".pack-stage-", dir=parent)
    # Stage under the pack's own name so validation and the promoted directory
    # agree with pack.yaml.name.
    staging = os.path.join(scratch, os.path.basename(os.path.abspath(target_dir)))
    os.makedirs(staging)
    try:
        _stage_source(source, staging, selector, transport)
        if selector is not None and transport is not None:
            resolved_digest = plan.resolved.get("transport_digest")
            if resolved_digest is not None and transport.resolve(selector) != resolved_digest:
                raise DistributionError("remote transport digest drifted from the plan")
        result = _verify_staged(staging, evidence_dir, signature_verifier=signature_verifier)
        if not result.accepted:
            raise DistributionError("staged bytes failed verification at apply time")
        if result.subject != plan.resolved.get("subject"):
            raise DistributionError("staged subject differs from the authorized plan")
        if require_signature and not result.authenticated:
            raise DistributionError(
                "release is not authenticated; supply a signature verifier or "
                "set require_signature=False to accept an unsigned release")
        target = Path(target_dir)
        if target.exists():
            # Atomic swap: the live target is never deleted before replacement.
            # After the exchange `staging` holds the previous tree, which the
            # scratch cleanup in `finally` retires.
            _transactions.exchange(Path(staging), target)
        else:
            _transactions.publish_noreplace(Path(staging), target)
        profile, _sbom, _provenance = verify_module.load_release_evidence(evidence_dir)
        evidence = profile.get("evidence") if isinstance(profile, dict) else None
        transport_digest = plan.resolved.get("transport_digest")
        receipt = build_receipt(
            selector=selector, transport_digest=transport_digest,
            result=result, evidence=evidence)
        write_receipt(target_dir, receipt)
        return receipt
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# --------------------------------------------------------------------------- #
# CLI (proposal-first: prints the plan; only --apply, explicitly, causes effects)
# --------------------------------------------------------------------------- #
EXIT_OK = 0
EXIT_BLOCKING = 1
EXIT_USAGE = 2
EXIT_TOOL_FAILURE = 3


def _emit(plan: OperationPlan, *, as_json: bool, out) -> None:
    print(plan.render_json() if as_json else plan.render_human(), file=out)


def main(argv: list[str] | None = None, *, stdout=None, stderr=None) -> int:
    """Command-line entry point for the proposal-first distribution workflow."""

    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    parser = argparse.ArgumentParser(
        prog="raes-pack-dist",
        description="Inspectable install/update/lock/verify/publish plans; "
                    "effects occur only with explicit --apply.")
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in ("verify", "lock"):
        sp = sub.add_parser(verb)
        sp.add_argument("--pack", required=True)
        sp.add_argument("--release", required=True)
        sp.add_argument("--json", action="store_true")
    for verb in ("install", "update"):
        sp = sub.add_parser(verb)
        sp.add_argument("--pack", required=True)
        sp.add_argument("--release", required=True)
        sp.add_argument("--target", required=True)
        sp.add_argument("--archive", help="install from a deterministic pack archive")
        sp.add_argument("--apply", action="store_true",
                        help="authorize and perform the plan's effects")
        sp.add_argument(
            "--allow-unsigned", action="store_true",
            help="accept a release whose signature cannot be verified (this CLI "
                 "configures no signature verifier, so it fails closed by default)")
        sp.add_argument("--json", action="store_true")
    pp = sub.add_parser("publish")
    pp.add_argument("--release", required=True)
    pp.add_argument("--repository", required=True)
    pp.add_argument("--reference", required=True)
    pp.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        return _dispatch(args, out=out, err=err)
    except DistributionError as exc:
        print(f"raes-pack-dist: {exc}", file=err)
        return EXIT_BLOCKING
    except Exception as exc:  # noqa: BLE001 -- a defect is a tool failure, not an untrusted pack
        print(f"raes-pack-dist: internal error ({type(exc).__name__})", file=err)
        return EXIT_TOOL_FAILURE


def _dispatch(args: argparse.Namespace, *, out, err) -> int:
    if args.verb == "verify":
        plan = plan_verify(args.pack, args.release)
        _emit(plan, as_json=args.json, out=out)
        return EXIT_OK if plan.applicable else EXIT_BLOCKING
    if args.verb == "lock":
        plan = plan_lock(args.pack, args.release)
        _emit(plan, as_json=args.json, out=out)
        return EXIT_OK if plan.applicable else EXIT_BLOCKING
    if args.verb == "publish":
        selector = Selector(repository=args.repository, reference=args.reference)
        plan = plan_publish(args.release, selector=selector)
        _emit(plan, as_json=args.json, out=out)
        return EXIT_OK if plan.applicable else EXIT_BLOCKING

    selector = transport = None
    if args.archive:
        selector = Selector(repository="local", reference=args.archive,
                            digest_domain=DIGEST_DOMAIN_ARCHIVE)
        transport = ArchiveTransport()
    planner = plan_install if args.verb == "install" else plan_update
    if args.verb == "install":
        plan = planner(args.pack, args.release, args.target,
                       selector=selector, transport=transport)
    else:
        plan = planner(args.target, args.pack, args.release,
                       selector=selector, transport=transport)
    _emit(plan, as_json=args.json, out=out)
    if not args.apply:
        return EXIT_OK if plan.applicable else EXIT_BLOCKING
    apply_install(plan, args.pack, args.release, args.target,
                  authorized=True, selector=selector, transport=transport,
                  require_signature=not args.allow_unsigned)
    print(f"applied: {args.verb} -> {args.target}", file=err)
    return EXIT_OK


__all__ = [
    "ArchiveLimits",
    "ArchiveTransport",
    "Change",
    "DistributionError",
    "Effect",
    "OperationPlan",
    "Selector",
    "Transport",
    "TransportUnavailable",
    "apply_install",
    "archive_digest",
    "build_receipt",
    "export_pack_archive",
    "main",
    "plan_install",
    "plan_lock",
    "plan_publish",
    "plan_update",
    "plan_verify",
    "read_receipt",
    "stage_pack_archive",
    "write_receipt",
]
