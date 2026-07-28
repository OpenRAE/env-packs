#!/usr/bin/env python3
"""Pack build / lint / release / profile-smoke gate (issue #49).

Packages a RAES environment pack and verifies every *supported* delivery
profile before release. This is a **static, read-only** quality and export gate
over committed source — it never stands up a range, calls cloud/CTFd/Terraform/
Docker, mutates state, or uploads. It derives release views from the existing
source-of-truth contracts and reuses ``environment_pack_content_ci.py`` for pack
discovery, path containment, and the redacted operator-token leak scan; it does
not duplicate schema validation or redaction logic.

What it enforces / produces:

  * **lint** — a pack must not claim a delivery bundle as ``supported`` that it
    does not actually ship: ``pack.compatibility.yaml.delivery_bundles[].status:
    supported`` must agree with ``pack.yaml.contents.profile_bundles``, the
    ``pack.yaml.profile_bundles`` index, and ``profiles/bundles.yaml`` (bundle id
    present, every shared/participant/operator entrypoint + validation reference
    present on disk). ``planned`` / ``not_shipped`` rows are honest metadata and
    need no shipped content.
  * **build** — assemble a boundary-split release tree: each
    ``artifact_boundaries`` group is staged into its own release root
    (participant / operator / oracle / commercial), then the leak scan is re-run
    over the participant tier so no operator token reaches a packaged
    participant artifact. Paths are containment-checked; ``..`` / absolute /
    symlink-escape paths are rejected.
  * **metadata** — emit versioned ``release.yaml``: pack version, the
    environment-pack contract version from the bundled contract plus a digest,
    the supported delivery profiles, compatible runtime profiles, and a
    *bounded* provenance summary (counts and review-gate statuses only).
  * **smoke** — prove delivery-bundle selection changes participant exposure and
    that restricted non-participant material never appears in a participant
    view.
  * **check** — the CI entry point: lint + smoke + build-to-tempdir over every
    releasable pack; non-releasable packs are explicit skips, never silent
    partial success.

Stdlib + PyYAML only. Run locally exactly as CI does:

    raes-pack-release check --pack ./path/to/pack
    raes-pack-release check --packs-root ./path/to/packs
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile

import yaml
from raes_contracts.associated_artifacts import associated_artifact_set_digest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# content_ci is a sibling module, imported after the sys.path insert above.
import content_ci as cc
from raes_env_packs import _pack_fs
from raes_env_packs import digest as digest_module
from raes_env_packs import publication, validation

REPO = cc._REPO
PACKS_ROOT = cc.PACKS_ROOT
METADATA_SCHEMA_VERSION = 1

# Boundary group -> release tier / publication view. This mapping is the single
# parameter over the boundary vocabulary (extensibility seam); the tool never
# guesses a tier from an ad hoc directory name. The runtime-visibility tier is
# the *group*; the per-row ``export`` distribution class is recorded as metadata,
# not used to pick the tier.
#
# The authored compatibility label ``oracle_only`` maps to the ``restricted``
# publication view (ADR 0028). The view is a release-boundary exposure class and
# gains no scenario or validation-oracle meaning from the label that fed it.
BOUNDARY_TIERS = {
    "participant_visible": "participant",
    "operator_only": "operator",
    "oracle_only": "restricted",
    "commercial": "commercial",
}
PARTICIPANT_TIER = "participant"

# Generated release views use a fixed safe mode instead of inheriting the source
# file's ownership, ACLs, extended attributes, or set-id bits. ``shutil.copy2``
# would carry a set-user-id or world-writable bit straight into a distributed
# artifact; a derived view is new content, not a copy of the author's filesystem
# metadata (ADR 0028).
#
# Owner-only. A release tree holds the operator, restricted, and commercial
# boundary tiers beside the participant one, so granting group or world read to
# the build output would expose restricted material to every local account.
# Distribution happens through a separate packaging step that sets the
# permissions appropriate to its own transport.
STAGED_FILE_MODE = 0o600
_STAGE_CHUNK = 64 * 1024

# The contract version line lives in the packaged contract source as a single,
# machine-detectable marker so consumers detect contract drift without parsing
# prose.
_CONTRACT_VERSION_RE = re.compile(r"Environment-pack contract version:\**\s*`([^`]+)`")
_CANONICAL_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CONTRACT_SOURCE = os.path.join(cc._RES, "contract", "pack-layout.md")
CONTRACT_SOURCE_LABEL = "contract/pack-layout.md"


# --------------------------------------------------------------------------
# Contract version
# --------------------------------------------------------------------------
def load_contract_version() -> tuple[str | None, str]:
    """Return ``(version, "sha256:<digest>")`` for the packaged contract source.

    The digest lets a release manifest pin the exact contract text it was built
    against, so a consumer can detect drift without re-parsing the prose.
    """
    with open(_CONTRACT_SOURCE, "rb") as fh:
        raw = fh.read()
    body = raw.decode("utf-8", errors="replace")
    m = _CONTRACT_VERSION_RE.search(body)
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    return (m.group(1) if m else None), digest


# --------------------------------------------------------------------------
# Path containment (sink-side path-traversal validation, Sonar S8707)
# --------------------------------------------------------------------------
def _within(root_real: str, candidate: str) -> bool:
    """True when ``candidate`` resolves to ``root_real`` or a descendant of it."""
    real = os.path.realpath(candidate)
    return real == root_real or os.path.commonpath([root_real, real]) == root_real


def _resolved_within(base_real: str, *parts: str) -> str:
    """Resolve ``base_real``/``parts`` and confirm it stays inside ``base_real``.

    Returns the realpath-resolved, containment-validated path to hand to the
    filesystem sink — so a path built from external input (CLI ``--pack`` /
    ``--out``) is validated *before* every read/write, and an absolute, ``..``,
    or symlink-escaping component raises rather than escaping the tree (Sonar
    pythonsecurity:S8707).
    """
    candidate = os.path.realpath(os.path.join(base_real, *parts))
    if candidate != base_real and os.path.commonpath([base_real, candidate]) != base_real:
        raise ValueError(f"path escapes {base_real!r}")
    return candidate


# --------------------------------------------------------------------------
# Pack contract loading
# --------------------------------------------------------------------------
class PackContracts(object):
    """The committed contracts the release tool reads, loaded once per pack."""

    def __init__(self, pack_root: str) -> None:
        """Initialize the instance."""
        self.pack_root = os.path.abspath(pack_root)
        self._root_real = os.path.realpath(self.pack_root)
        self.pack_yaml = self._read("pack.yaml") or {}
        self.name = self.pack_yaml.get("name") or os.path.basename(self.pack_root)
        self.compatibility = self._read_pointer(self.pack_yaml.get("compatibility_manifest"))
        self.provenance = self._read_pointer(self.pack_yaml.get("provenance_ledger"))
        self.publication = self._read_pointer(self.pack_yaml.get("publication_supply"))
        self.bundles = self._read(os.path.join("profiles", "bundles.yaml"))

    def _read(self, rel: str) -> object:
        """Read a pack-relative YAML file, validated at the open() sink."""
        try:
            path = _resolved_within(self._root_real, rel)
            if not os.path.isfile(path):
                return None
            with open(path, "r", encoding="utf-8") as fh:
                return yaml.safe_load(fh)
        except (ValueError, OSError, yaml.YAMLError):
            return None

    def _read_pointer(self, rel: object) -> object:
        """Read pointer."""
        return self._read(rel) if isinstance(rel, str) else None

    @property
    def supported_bundles(self) -> list[dict[str, object]]:
        """Supported bundles."""
        compat = self.compatibility or {}
        return [b for b in (compat.get("delivery_bundles") or [])
                if isinstance(b, dict) and b.get("status") == "supported"]

    @property
    def manifest_bundle_rows(self) -> dict[str, dict[str, object]]:
        """Manifest bundle rows."""
        rows = (self.bundles or {}).get("bundles") or []
        return {r.get("id"): r for r in rows if isinstance(r, dict) and r.get("id")}


def is_releasable(pack_root: str) -> bool:
    """A pack is releasable when it declares artifact boundaries to split on."""
    compat = PackContracts(pack_root).compatibility
    return isinstance(compat, dict) and isinstance(compat.get("artifact_boundaries"), dict)


# --------------------------------------------------------------------------
# Leak scanning (delegates to the canonical redaction discipline)
# --------------------------------------------------------------------------
def scan_text_for_leaks(text: str) -> list[tuple[str, int]]:
    """Return ``(class_label, line_no)`` for operator tokens in ``text``.

    Reports the token *class* and a line locator only — never the match — so a
    release manifest or log surface cannot itself leak operator vocabulary
    (issue #138 discipline, reused from ``environment_pack_content_ci``).
    """
    leaks: list[tuple[str, int]] = []
    for pat, label in cc.TOKEN_PATTERNS:
        if m := pat.search(text):
            leaks.append((label, text.count("\n", 0, m.start()) + 1))
    return leaks


def scan_tier_for_leaks(tier_dir: str) -> list[tuple[str, str]]:
    """Return ``(class_label, "relpath:line")`` for every text file under a tier."""
    leaks: list[tuple[str, str]] = []
    if not os.path.isdir(tier_dir):
        return leaks
    for fp in cc._iter_text_files(tier_dir):
        for label, line_no in cc._token_leaks(fp):
            leaks.append((label, f"{os.path.relpath(fp, tier_dir)}:{line_no}"))
    return leaks


# --------------------------------------------------------------------------
# Lint (AC1: fail fast when a supported bundle lacks shipped content)
# --------------------------------------------------------------------------
def _entry_failures(pack_root: str, name: str, bid: str, key: str,
                    entries: object) -> list[str]:
    """Entry failures."""
    out: list[str] = []
    for entry in entries or []:
        if not isinstance(entry, str):
            continue
        rel = os.path.join("profiles", entry)
        if not cc._path_inside_pack(pack_root, rel):
            out.append(f"{name}: bundle {bid} {key} entry {entry} escapes pack root")
        elif not os.path.exists(os.path.join(pack_root, rel)):
            out.append(f"{name}: bundle {bid} {key} references missing file {entry}")
    return out


def _lint_bundle(pc: "PackContracts", pack_root: str, bundle: dict[str, object],
                 manifest_rows: dict[str, dict[str, object]],
                 index_ids: set[object]) -> list[str]:
    """Lint one supported delivery bundle against its shipped content."""
    bid = bundle.get("bundle_id")
    row = manifest_rows.get(bid)
    if row is None:
        return [f"{pc.name}: supported delivery bundle {bid} has no row in "
                "profiles/bundles.yaml"]
    failures: list[str] = []
    if index_ids and bid not in index_ids:
        failures.append(
            f"{pc.name}: supported delivery bundle {bid} missing from pack.yaml "
            "profile_bundles index")
    for key in ("shared_includes", "participant_entrypoints", "operator_entrypoints"):
        failures += _entry_failures(pack_root, pc.name, bid, key, row.get(key))
    for vref in (bundle.get("validation") or []):
        vpath = vref.get("path") if isinstance(vref, dict) else None
        if isinstance(vpath, str) and not os.path.exists(os.path.join(pack_root, vpath)):
            failures.append(
                f"{pc.name}: supported delivery bundle {bid} validation reference "
                f"missing: {vpath}")
    return failures


def lint_pack(pack_root: str) -> list[str]:
    """Verify a pack ships every delivery bundle it advertises as supported."""
    pc = PackContracts(pack_root)
    supported = pc.supported_bundles
    if not supported:
        # nothing claimed supported -> nothing to ship
        return []

    failures: list[str] = []
    contents = pc.pack_yaml.get("contents") or {}
    if contents.get("profile_bundles") is not True:
        failures += [
            f"{pc.name}: delivery bundle {b.get('bundle_id')} is status=supported "
            "but pack.yaml contents.profile_bundles is not true" for b in supported]

    index = pc.pack_yaml.get("profile_bundles") or {}
    index_ids = {x.get("id") for x in (index.get("bundles") or []) if isinstance(x, dict)}
    for bundle in supported:
        failures += _lint_bundle(pc, pack_root, bundle, pc.manifest_bundle_rows, index_ids)
    return failures


# --------------------------------------------------------------------------
# Build (AC2: separate participant / operator / oracle / commercial artifacts)
# --------------------------------------------------------------------------
# A release directory component (pack name / version) must be a single, path-safe
# slug: pack-controlled metadata must never inject a separator, ``..``, or an
# absolute path that would let the release tree be written outside ``--out``.
_SAFE_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def _is_safe_slug(value: str) -> bool:
    """Is safe slug."""
    return bool(value) and value not in (".", "..") and \
        _SAFE_SLUG_RE.fullmatch(value) is not None


def _safe_pack_path(pack_root: str, rel: str) -> tuple[bool, str]:
    """Safe pack path."""
    if not rel or os.path.isabs(rel):
        return False, "is absolute or empty"
    if not cc._path_inside_pack(pack_root, rel):
        return False, "escapes pack root"
    within = _within(os.path.realpath(pack_root), os.path.join(pack_root, rel))
    return (True, "") if within else (False, "resolves outside pack root (symlink escape)")


def _stage(root_fd: int, pack_root: str, rel: str, dst: str,
           staged: list[str] | None = None) -> tuple[int, list[str]]:
    """Stage one boundary row (file or directory) to ``dst``.

    Returns ``(file_count, errors)``. Enumeration finds candidate names; the
    authoritative read is always a root-anchored, no-follow descriptor open, so
    the safety decision and the copy are the *same* file object. Validating a
    pathname and then re-opening it leaves a window in which a component can be
    swapped for a symlink between the check and the copy, which is exactly how
    out-of-boundary content would reach a release artifact.
    """
    src = os.path.join(pack_root, os.path.normpath(rel))
    if os.path.isdir(src) and not os.path.islink(src):
        return _stage_tree(root_fd, pack_root, rel, dst, staged)
    return _stage_member(root_fd, rel, dst, staged)


def _stage_member(root_fd: int, rel: str, dst: str,
                  staged: list[str] | None = None) -> tuple[int, list[str]]:
    """Copy one member's bytes through a root-anchored descriptor.

    ``_pack_fs.open_member`` walks every path component with ``O_NOFOLLOW`` from
    the pack root and rejects anything that is not a singly-linked regular file,
    so symlinks, hardlinks, special files, and escaping paths fail closed here
    rather than being copied.
    """
    try:
        fd = _pack_fs.open_member(root_fd, rel)
    except _pack_fs.PackFilesystemError:
        return 0, [f"member {rel} is a symlink or escapes pack root"]
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # Content only, then a fixed safe mode: `shutil.copy2` would preserve the
        # source's set-user-id, set-group-id, or world-writable bits and hand
        # them to everyone who unpacks the release. A generated view is derived
        # content; its permissions are ours to set, not the author's to
        # propagate.
        with open(dst, "wb") as out:
            while chunk := os.read(fd, _STAGE_CHUNK):
                out.write(chunk)
        os.chmod(dst, STAGED_FILE_MODE)
    except OSError:
        return 0, [f"member {rel} could not be staged"]
    finally:
        os.close(fd)
    if staged is not None:
        staged.append(rel)
    return 1, []


def _pack_relpath(path: str, pack_root: str) -> str:
    """Pack-relative, forward-slash path for one staged member."""
    return os.path.relpath(path, pack_root).replace(os.sep, "/")


def _stage_tree(root_fd: int, pack_root: str, rel: str, dst: str,
                staged: list[str] | None = None) -> tuple[int, list[str]]:
    """Stage every member beneath one boundary directory row."""
    count = 0
    errors: list[str] = []
    src = os.path.join(pack_root, os.path.normpath(rel))
    base = rel.replace(os.sep, "/").rstrip("/")
    # os.walk does not descend into symlinked directories by default, and each
    # file below is re-opened through a root-anchored no-follow descriptor.
    for dirpath, _dirs, files in os.walk(src):
        suffix = os.path.relpath(dirpath, src)
        target = dst if suffix == "." else os.path.join(dst, suffix)
        os.makedirs(target, exist_ok=True)
        for fname in sorted(files):
            member = _pack_relpath(os.path.join(dirpath, fname), pack_root)
            if not member.startswith(f"{base}/"):
                errors.append(f"member {member} escapes boundary row {base}")
                continue
            copied, member_errors = _stage_member(
                root_fd, member, os.path.join(target, fname), staged)
            count += copied
            errors += member_errors
    return count, errors


def _resolve_release_paths(pc: "PackContracts", out_dir: str,
                           version: str) -> tuple[str | None, str | None, list[str]]:
    """Validate pack-controlled name/version and resolve the staging + release
    roots, both contained under the resolved ``out_dir`` (Sonar S8707)."""
    failures = [
        f"{pc.name}: pack {label} {value!r} is not a path-safe slug"
        for label, value in (("name", pc.name), ("version", version))
        if not _is_safe_slug(value)]
    if failures:
        return None, None, failures
    out_real = os.path.realpath(out_dir)
    try:
        release_root = _resolved_within(out_real, f"{pc.name}-{version}")
        staging = _resolved_within(out_real, f".{pc.name}-{version}.staging")
    except ValueError:
        return None, None, [f"{pc.name}: release root escapes the output directory"]
    return release_root, staging, []


class _Staging(object):
    """The invariants one staging pass carries across every boundary row."""

    def __init__(self, pc: "PackContracts", pack_root: str, staging: str,
                 tier_stats: dict[str, dict[str, object]],
                 staged_by_view: dict[str, list[str]] | None,
                 root_fd: int) -> None:
        """Initialize the instance."""
        self.pc = pc
        self.pack_root = pack_root
        self.staging = staging
        self.tier_stats = tier_stats
        self.staged_by_view = staged_by_view
        self.root_fd = root_fd

    def staged_for(self, tier: str) -> list[str] | None:
        """The per-view staged-path accumulator, when one is being collected."""
        if self.staged_by_view is None:
            return None
        return self.staged_by_view.setdefault(tier, [])

    def record(self, tier: str, export: object, copied: int) -> None:
        """Tally staged files and their distribution classes for one view."""
        self.tier_stats[tier]["file_count"] += copied
        if isinstance(export, str):
            self.tier_stats[tier]["exports"][export] = (
                self.tier_stats[tier]["exports"].get(export, 0) + copied)


def _row_problem(pack_root: str, rel: str) -> str | None:
    """Why a declared boundary path cannot be staged, or ``None`` when it can."""
    ok, why = _safe_pack_path(pack_root, rel)
    if not ok:
        return why
    if not os.path.exists(os.path.join(pack_root, rel)):
        return "does not exist"
    return None


def _stage_boundary_row(ctx: "_Staging", group: str, tier: str,
                        row: object) -> list[str]:
    """Stage one declared boundary row into its release view."""
    rel = row.get("path") if isinstance(row, dict) else None
    if not isinstance(rel, str):
        return []
    problem = _row_problem(ctx.pack_root, rel)
    if problem:
        return [f"{ctx.pc.name}: boundary {group} path {rel} {problem}"]
    copied, stage_errors = _stage(
        ctx.root_fd, ctx.pack_root, rel,
        os.path.join(ctx.staging, tier, os.path.normpath(rel)),
        ctx.staged_for(tier))
    ctx.record(tier, row.get("export"), copied)
    return [f"{ctx.pc.name}: boundary {group} {err}" for err in stage_errors]


def _stage_boundaries(pc: "PackContracts", pack_root: str, boundaries: object,
                      staging: str, tier_stats: dict[str, dict[str, object]],
                      staged_by_view: dict[str, list[str]] | None = None) -> list[str]:
    """Stage every boundary row through one root-anchored descriptor."""
    if not isinstance(boundaries, dict):
        return []
    failures: list[str] = []
    try:
        _root_real, root_fd = _pack_fs.open_root(pack_root)
    except _pack_fs.PackFilesystemError:
        return [f"{pc.name}: pack root is not a safe directory to stage from"]
    ctx = _Staging(pc, pack_root, staging, tier_stats, staged_by_view, root_fd)
    try:
        for group, tier in BOUNDARY_TIERS.items():
            for row in (boundaries.get(group) or []):
                failures += _stage_boundary_row(ctx, group, tier, row)
    finally:
        os.close(root_fd)
    return failures


def _stage_views(pc: "PackContracts", pack_root: str, staging: str,
                 tier_stats: dict[str, dict[str, object]],
                 staged_by_view: dict[str, list[str]]) -> list[str]:
    """Stage every boundary group and re-scan the staged participant tier.

    A participant/restricted boundary overlap is rejected before any row is
    copied (ADR 0013): release must be independently safe even if the shared
    validation gate did not run first. On overlap nothing is staged at all; the
    participant leak scan is defense in depth, not the declaration boundary.
    """
    boundaries = (pc.compatibility or {}).get("artifact_boundaries")
    overlap_fields = validation._boundary_overlaps(boundaries)
    if overlap_fields:
        return [
            f"{pc.name}: artifact boundary {field} overlaps an "
            "operator/oracle/private root; refusing to stage a participant export"
            for field in overlap_fields]
    failures = _stage_boundaries(
        pc, pack_root, boundaries, staging, tier_stats, staged_by_view)
    # The participant tier is the one surface that must never carry an operator
    # token; re-run the redacted leak scan over the *staged* artifact.
    return failures + [
        f"{pc.name}: participant release artifact leaks a {label} at "
        f"{PARTICIPANT_TIER}/{locator} (match redacted)"
        for label, locator in scan_tier_for_leaks(
            os.path.join(staging, PARTICIPANT_TIER))]


def build_release(pack_root: str, out_dir: str, *,
                  include_build_provenance: bool = False) -> tuple[dict[str, object], list[str]]:
    """Assemble the boundary-split release tree and its metadata.

    Returns ``(metadata, failures)``. The release tree is treated as an atomic
    derived artifact: everything is staged into a scratch directory and fully
    validated (path containment, symlink rejection, participant leak scan) there;
    only on success is the scratch tree atomically promoted to the final release
    root (replacing any prior build, so a later run never inherits stale files).
    On any failure the scratch tree is removed, so a containment violation or
    participant leak never leaves a half-built, mislabeled, or partial artifact
    behind.
    """
    pc = PackContracts(pack_root)
    version = str(pc.pack_yaml.get("version") or "0.0.0")
    tier_stats: dict[str, dict[str, object]] = {
        tier: {"file_count": 0, "exports": {}} for tier in sorted(set(BOUNDARY_TIERS.values()))
    }
    metadata = release_metadata(pack_root, include_build_provenance=include_build_provenance)
    staged_by_view: dict[str, list[str]] = {}
    release_root, staging, failures = _resolve_release_paths(pc, out_dir, version)
    if failures:
        return metadata, failures

    if os.path.exists(staging):
        shutil.rmtree(staging)
    # validated path; creates the resolved out_dir as a parent
    os.makedirs(staging)
    try:
        failures += _stage_views(pc, pack_root, staging, tier_stats, staged_by_view)
        # The release carrier is a consumer contract, so it is validated before
        # it is written: shape against the packaged schema, and every supply
        # claim joined back to the RAES-authored requirement. An unverifiable
        # claim fails the build rather than shipping inside a release artifact.
        # Staged-byte facts belong to the view they describe, and are copied only
        # after staging has actually counted them -- reading the counters earlier
        # would freeze every view at zero files.
        for view in metadata["release"]["views"]:
            view.update(tier_stats.get(view["view"], {"file_count": 0, "exports": {}}))
        bind_failures, view_members = _bind_view_sets(
            pack_root, metadata, staged_by_view, staging)
        failures += bind_failures
        failures += _publication_failures(pc, pack_root, metadata, view_members)
        failures += _immutability_failures(pc, release_root, metadata)
        if failures:
            return metadata, failures

        with open(os.path.join(staging, "release.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(metadata, fh, sort_keys=False)
        # Atomic promote. Replacing is safe only because the immutability check
        # above proved any already-published release binds the same identities;
        # an identity-equivalent rebuild is idempotent, a divergent one refused.
        if os.path.exists(release_root):
            shutil.rmtree(release_root)
        os.replace(staging, release_root)
        staging = None
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
    return metadata, failures


# --------------------------------------------------------------------------
# Release metadata (AC4)
# --------------------------------------------------------------------------
def _tally(rows: object, key: str) -> dict[str, int]:
    """Tally."""
    out: dict[str, int] = {}
    for row in rows or []:
        if isinstance(row, dict) and isinstance(row.get(key), str):
            out[row[key]] = out.get(row[key], 0) + 1
    return out


def _gate_status(review: dict[str, object]) -> dict[str, object]:
    """Gate status."""
    out: dict[str, object] = {}
    for gate in (review.get("gates") or []):
        if isinstance(gate, dict) and isinstance(gate.get("gate_id"), str):
            out[gate["gate_id"]] = gate.get("status")
    return out


def _provenance_summary(ledger: object) -> dict[str, object]:
    """A bounded, leak-safe projection of the provenance ledger.

    Counts and review-gate statuses only — never source/review prose, artifact
    paths, restricted operator vocabulary, or customer-specific detail.
    """
    ledger = ledger if isinstance(ledger, dict) else {}
    sources = ledger.get("sources") or []
    artifacts = ledger.get("artifacts") or []
    safety = ledger.get("content_safety") or {}
    all_true = bool(safety) and all(safety.get(flag) is True for flag in cc.CONTENT_SAFETY_FLAGS)
    return {
        "sources": len(sources) if isinstance(sources, list) else 0,
        "artifacts": len(artifacts) if isinstance(artifacts, list) else 0,
        "artifact_classes": _tally(artifacts, "classification"),
        "content_safety": {"all_true": all_true},
        "review": _gate_status(ledger.get("review") or {}),
    }


def _git_commit(repo_root: str) -> str | None:
    """Git commit."""
    import subprocess
    try:
        out = subprocess.run(["git", "-C", repo_root, "rev-parse", "HEAD"],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _supported_bundle_ids(compat: dict[str, object]) -> list[str]:
    """Supported bundle ids."""
    return sorted(
        b.get("bundle_id") for b in (compat.get("delivery_bundles") or [])
        if isinstance(b, dict) and b.get("status") == "supported" and b.get("bundle_id"))


def _runtime_profile_ids(compat: dict[str, object]) -> list[str]:
    """Runtime profile ids."""
    return sorted(
        rp.get("profile_id") for rp in (compat.get("runtime_profiles") or [])
        if isinstance(rp, dict) and rp.get("status") in ("supported", "required")
        and rp.get("profile_id"))


def _immutability_failures(pc: "PackContracts", release_root: str,
                           metadata: dict[str, object]) -> list[str]:
    """Refuse to overwrite an already-published release with other identities.

    Reusing a pack id and version for a different semantic parent or byte set is
    a new release, not a replacement. Only an identity-equivalent rebuild may be
    idempotent, so a divergent build is refused before anything is promoted and
    the published artifact is left untouched.
    """
    published_path = os.path.join(release_root, "release.yaml")
    if not os.path.isfile(published_path):
        return []
    published = _read_published_profile(published_path)
    if published is None:
        return [f"{pc.name}: published release.yaml is unreadable; refusing to "
                "overwrite an immutable release"]
    same = (publication.release_identity(published)
            == publication.release_identity(metadata))
    return [] if same else [
        f"{pc.name}: release {metadata['release']['pack']['version']} is already "
        "published with different bound identities; an immutable release is "
        "not replaced (publish a new version instead)"]


def _read_published_profile(path: str) -> object | None:
    """Load an already-published profile, or ``None`` when it cannot be read."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return None


def _staged_descriptor(descriptor: object, staged_path: str) -> object:
    """Rebind one authored descriptor to the bytes actually staged.

    Deriving from the pack root would describe whatever the source tree holds at
    derivation time, which is not necessarily what was copied moments earlier.
    Hashing the staged file instead binds the advertised set to the bytes that
    are about to be promoted.
    """
    sha = hashlib.sha256()
    size = 0
    fd = os.open(staged_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        while chunk := os.read(fd, 65536):
            sha.update(chunk)
            size += len(chunk)
    finally:
        os.close(fd)
    checksum = descriptor.checksum.model_copy(update={"value": sha.hexdigest()})
    return descriptor.model_copy(update={"checksum": checksum, "size_bytes": size})


def _view_descriptors(manifest: object, by_path: dict[str, str],
                      rels: object, view: str,
                      staging: str | None) -> tuple[dict[str, object], int]:
    """Project the authored descriptors for one view onto its staged bytes.

    Returns ``(artifacts, unreadable_count)``. Descriptors are rebound to the
    staged file rather than the pack root, so the advertised set describes the
    bytes about to be promoted.
    """
    artifacts: dict[str, object] = {}
    unreadable = 0
    for rel in sorted(set(rels or ())):
        artifact_id = by_path.get(rel)
        if artifact_id is None:
            continue
        authored = manifest.artifacts[artifact_id]
        if staging is None:
            artifacts[artifact_id] = authored
            continue
        try:
            artifacts[artifact_id] = _staged_descriptor(
                authored, os.path.join(staging, view, os.path.normpath(rel)))
        except OSError:
            unreadable += 1
    return artifacts, unreadable


def _bind_view_sets(pack_root: str, metadata: dict[str, object],
                    staged_by_view: dict[str, list[str]],
                    staging: str | None = None
                    ) -> tuple[list[str], dict[str, set[str]]]:
    """Give every non-empty view its own RAES associated-artifact set identity.

    Set identity does not inherit: a filtered view is a different payload set
    than the source pack, so reusing the pack's set digest would misidentify it.
    The view manifest is the pack's own authored manifest *restricted* to the
    files staged into that view, which keeps derivation reproducible -- RAES
    descriptors carry a ``created_at`` that is not recoverable from bytes, so
    minting fresh descriptors would make an unchanged release re-identify itself
    on every rebuild.
    """
    members: dict[str, set[str]] = {}
    if not staged_by_view:
        return [], members
    try:
        manifest = digest_module.derive_pack_content_manifest(pack_root)
        by_path = {
            rel: artifact_id
            for artifact_id, rel in digest_module._artifact_paths(
                manifest, _manifest_pointer(pack_root)).items()
        }
    except (digest_module.PackDigestError, OSError, ValueError):
        return [], members

    pack = metadata["release"]["pack"]
    failures: list[str] = []
    for view in metadata["release"]["views"]:
        name = view["view"]
        artifacts, read_failures = _view_descriptors(
            manifest, by_path, staged_by_view.get(name, ()), name, staging)
        failures += [
            f"{pack['name']}: staged {name} member could not be read for "
            "view identity derivation"
            for _ in range(read_failures)
        ]
        if not artifacts:
            # An empty view stays empty; RAES manifests require a non-empty
            # payload set, and inventing a placeholder artifact would be a lie.
            continue
        view_manifest = manifest.model_copy(update={
            "manifest_id": f"{pack['name']}-{name}-associated-artifacts",
            "manifest_version": pack["version"],
            "artifacts": artifacts,
            "set_digest": "sha256:" + "0" * 64,
        })
        view_manifest = view_manifest.model_copy(update={
            "set_digest": associated_artifact_set_digest(view_manifest)})
        view["set"] = {
            "manifest_id": view_manifest.manifest_id,
            "set_digest": view_manifest.set_digest,
        }
        # Membership index: the governed digests a publication row in this view
        # may claim to supply. Without it a row could advertise a trusted
        # artifact while the view actually exposes unrelated bytes.
        members[name] = {
            f"{descriptor.checksum.algorithm}:{descriptor.checksum.value}"
            for descriptor in artifacts.values()
        }
        if staging:
            # The manifest is written beside the view, never inside it: a set
            # cannot contain the document that describes it. Without emitting it
            # a consumer holds a set digest but no descriptors to verify against.
            with open(os.path.join(staging, f"{name}-associated-artifacts.json"),
                      "w", encoding="utf-8") as fh:
                fh.write(view_manifest.model_dump_json(indent=2) + "\n")
    return failures, members


def _manifest_pointer(pack_root: str) -> str:
    """The pack-relative associated-artifact manifest carrier, if declared."""
    pointer = PackContracts(pack_root).pack_yaml.get("associated_artifact_manifest")
    return pointer if isinstance(pointer, str) else ""


def _authored_requirements(pack_root: str) -> tuple[dict[str, object], list[str]]:
    """Index this pack's authored requirements, and report the author-static result.

    The release gate does not assume another command already validated the pack:
    it runs the same shared author-static authority. Invoking that gate and then
    ignoring its verdict would leave the ADR 0028 precondition unestablished --
    an invalid pack could pass publication validation, and claims could be judged
    against a partial scenario set. The bounded failures are returned so the
    caller can refuse promotion.
    """
    try:
        result, scenarios = validation._validate_pack_for_author_ci(pack_root)
    except (OSError, ValueError):
        return {}, ["pack could not be validated for publication"]
    errors = [] if result.ok else list(result.errors)
    return publication.authored_artifact_requirements(scenarios), errors


def _publication_failures(pc: "PackContracts", pack_root: str,
                          metadata: dict[str, object],
                          view_members: dict[str, set[str]] | None = None) -> list[str]:
    """Validate the emitted publication profile, as release-gate failures.

    Diagnostics stay bounded: a stable code and a field path, never artifact
    bytes, locator values, or credentials.
    """
    requirements, invalid = _authored_requirements(pack_root)
    # ADR 0028: a publication cannot be emitted for a pack that does not pass the
    # shared author-static contract. Refuse rather than publish against a
    # partially parsed pack.
    failures = [f"{pc.name}: pack is not publishable: {code}" for code in invalid]
    failures += [
        f"{pc.name}: publication profile {violation.code} at {violation.path}"
        for violation in publication.validate_publication_document(
            metadata, requirements=requirements, view_members=view_members)
    ]
    return failures


def _semantic_binding(pack_root: str) -> tuple[dict[str, object], dict[str, object]] | None:
    """Return ``(semantic_parent, source_set)`` for a content-identified pack.

    Both come from the RAES associated-artifact manifest the pack declares, so
    this repository binds to RAES's own parent reference and set digest rather
    than deriving a second release identity. ``None`` means the pack declares no
    content identity, and no publication can be emitted for it (ADR 0028).
    """
    try:
        manifest = digest_module.derive_pack_content_manifest(pack_root)
    except (digest_module.PackDigestError, OSError, ValueError):
        return None
    # RAES names these ``ref_id`` / ``ref_digest`` on its parent reference model.
    parent = manifest.parent_ref
    parent_ref = getattr(parent, "ref_id", None)
    if not isinstance(parent_ref, str) or not parent_ref:
        return None
    semantic_parent: dict[str, object] = {"parent_ref": parent_ref}
    # The parent digest is optional upstream: a scenario parent may be
    # referenced by id alone. Carry it only when RAES actually supplied one,
    # rather than inventing a placeholder digest that would look like evidence.
    parent_digest = getattr(parent, "ref_digest", None)
    if isinstance(parent_digest, str) and _CANONICAL_DIGEST_RE.fullmatch(parent_digest):
        semantic_parent["digest"] = parent_digest
    return (
        semantic_parent,
        {"manifest_id": manifest.manifest_id, "set_digest": manifest.set_digest},
    )


def _authored_supply(pc: "PackContracts") -> dict[str, object]:
    """Read the pack's optional declaration of what this release supplies.

    Derivation cannot invent which permitted assets an author chose to ship, so
    the supply rows are authored. They are validated against RAES author
    authority before emission; absence simply means the release publishes
    nothing, which is a valid release and implies nothing about satisfiability.
    """
    declared = pc.publication if isinstance(pc.publication, dict) else {}
    return {
        "publications": declared.get("publications") or [],
        "capability_claims": declared.get("capability_claims") or [],
        "availability": declared.get("availability") or [],
        "channels": declared.get("channels") or [],
    }


def release_metadata(pack_root: str, *, include_build_provenance: bool = False,
                     repo_root: str = REPO) -> dict[str, object]:
    """Emit the immutable publication profile for one pack release (ADR 0028)."""
    pc = PackContracts(pack_root)
    compat = pc.compatibility or {}
    version, digest = load_contract_version()
    supply = _authored_supply(pc)

    summary: dict[str, object] = {
        "contract": {"version": version, "source": CONTRACT_SOURCE_LABEL, "digest": digest},
        "supported_profiles": _supported_bundle_ids(compat),
        "runtime_profiles": _runtime_profile_ids(compat),
        "provenance_summary": _provenance_summary(pc.provenance),
    }
    if include_build_provenance:
        summary["build_provenance"] = {"git_commit": _git_commit(repo_root)}

    release: dict[str, object] = {
        "pack": {
            "name": pc.name,
            "version": str(pc.pack_yaml.get("version") or "0.0.0"),
        },
        "views": _release_views(supply),
    }
    # A pack that has not opted into content identity (ADR 0012) carries no
    # binding blocks at all rather than empty ones. Such a release may still be
    # built; it simply cannot make a publication or capability claim, which the
    # profile validator enforces.
    binding = _semantic_binding(pack_root)
    if binding is not None:
        release["semantic_parent"], release["source_set"] = binding

    profile: dict[str, object] = {
        "schema_version": publication.PUBLICATION_SCHEMA_VERSION,
        "summary": summary,
        "release": release,
        "distribution": {
            "availability": supply["availability"],
            "channels": supply["channels"],
        },
    }
    return profile


def _release_views(supply: dict[str, object]) -> list[dict[str, object]]:
    """Build one publication view per stable release view.

    Views are derived from the ``BOUNDARY_TIERS`` seam, so a new authored
    boundary group becomes a view through that one mapping. Each view starts
    empty; per-view set identity is bound during the build once the view's exact
    bytes are staged.
    """
    by_view: dict[str, list[object]] = {view: [] for view in sorted(set(BOUNDARY_TIERS.values()))}
    claims_by_view: dict[str, list[object]] = {view: [] for view in by_view}
    # An authored row naming an unknown view is a defect in the supply, not a
    # row to drop: silently filtering it here would let the build succeed while
    # omitting a publication the author declared. Route it to a real view so the
    # schema-backed validation that follows can reject it by name.
    fallback = PARTICIPANT_TIER
    for row in supply["publications"]:
        if isinstance(row, dict):
            view = row.get("view")
            by_view[view if view in by_view else fallback].append(
                {k: v for k, v in row.items() if k != "view"}
                if view in by_view else dict(row))
    for claim in supply["capability_claims"]:
        if isinstance(claim, dict):
            view = claim.get("view")
            claims_by_view[view if view in claims_by_view else fallback].append(
                {k: v for k, v in claim.items() if k != "view"}
                if view in claims_by_view else dict(claim))
    return [
        {
            "view": view,
            "completeness": "non-exhaustive",
            "publications": by_view[view],
            "capability_claims": claims_by_view[view],
        }
        for view in sorted(by_view)
    ]


# --------------------------------------------------------------------------
# Smoke (AC3: delivery-bundle selection changes participant exposure)
# --------------------------------------------------------------------------
def _under_participant(rel: str) -> bool:
    """Under participant."""
    parts = rel.replace("\\", "/").split("/")
    if parts and parts[0] == "_shared":
        return True
    return len(parts) >= 2 and parts[1] == "participant"


def bundle_participant_views(pack_root: str) -> dict[str, list[str]]:
    """Map each supported bundle id to its sorted participant exposure set.

    The participant view of a bundle is the shared, participant-safe content plus
    the bundle's own participant entrypoints — exactly what a participant of that
    delivery profile receives, and never restricted non-participant surfaces.
    """
    pc = PackContracts(pack_root)
    supported = {b.get("bundle_id") for b in pc.supported_bundles}
    views: dict[str, list[str]] = {}
    for bid, row in pc.manifest_bundle_rows.items():
        if supported and bid not in supported:
            continue
        files: list[str] = []
        for key in ("shared_includes", "participant_entrypoints"):
            for entry in (row.get(key) or []):
                if isinstance(entry, str):
                    files.append("profiles/" + entry)
        views[bid] = sorted(files)
    return views


def _missing_entrypoints(pc: "PackContracts", pack_root: str, bid: object,
                         row: dict[str, object]) -> list[str]:
    """Missing entrypoints."""
    out: list[str] = []
    for key in ("shared_includes", "participant_entrypoints", "operator_entrypoints"):
        for entry in (row.get(key) or []):
            if isinstance(entry, str) and not os.path.exists(
                    os.path.join(pack_root, "profiles", entry)):
                out.append(f"{pc.name}: bundle {bid} missing entrypoint {entry}")
    return out


def _operator_under_participant(pc: "PackContracts", bid: object,
                                row: dict[str, object]) -> list[str]:
    """Operator under participant."""
    out: list[str] = []
    for entry in (row.get("operator_entrypoints") or []):
        if isinstance(entry, str) and _under_participant(entry):
            out.append(
                f"{pc.name}: bundle {bid} operator entrypoint {entry} sits under a "
                "participant root")
    return out


def _smoke_bundle(pc: "PackContracts", pack_root: str, bundle: dict[str, object],
                  rows: dict[str, dict[str, object]]) -> list[str]:
    """Check one supported bundle's required entrypoints exist and that its
    operator entrypoints never sit under a participant root."""
    bid = bundle.get("bundle_id")
    row = rows.get(bid)
    if row is None:
        return [f"{pc.name}: supported bundle {bid} missing from profiles/bundles.yaml"]
    return (_missing_entrypoints(pc, pack_root, bid, row)
            + _operator_under_participant(pc, bid, row))


def _smoke_view_leaks(pc: "PackContracts", pack_root: str,
                      views: dict[str, list[str]]) -> list[str]:
    """Smoke view leaks."""
    failures: list[str] = []
    for bid, files in views.items():
        for rel in files:
            full = os.path.join(pack_root, rel)
            if os.path.isfile(full):
                failures += [
                    f"{pc.name}: bundle {bid} participant view leaks a {label} at "
                    f"{rel}:{line_no} (match redacted)"
                    for label, line_no in cc._token_leaks(full)]
    return failures


def smoke_pack(pack_root: str) -> list[str]:
    """Smoke-test that profile selection changes participant exposure correctly."""
    pc = PackContracts(pack_root)
    supported = pc.supported_bundles
    if not supported:
        return []

    failures: list[str] = []
    for bundle in supported:
        failures += _smoke_bundle(pc, pack_root, bundle, pc.manifest_bundle_rows)

    views = bundle_participant_views(pack_root)
    failures += _smoke_view_leaks(pc, pack_root, views)

    distinct = {frozenset(v) for v in views.values()}
    if len(views) >= 2 and len(distinct) < 2:
        failures.append(
            f"{pc.name}: delivery-bundle selection does not change participant exposure "
            "(all supported bundle participant views are identical)")
    return failures


# --------------------------------------------------------------------------
# check (CI entry point)
# --------------------------------------------------------------------------
def check(
    packs: list[str] | None = None,
    *,
    packs_root: str | None = None,
) -> list[str]:
    """Lint + smoke + build-to-tempdir over every releasable pack."""
    failures: list[str] = []
    if packs is not None:
        pack_roots = tuple(_resolve_pack(pack) for pack in packs)
    else:
        root = os.path.abspath(packs_root) if packs_root is not None else PACKS_ROOT
        pack_roots = tuple(
            os.path.join(root, name)
            for name in cc._packs(
                root,
                failures,
                require_root=packs_root is not None,
            )
        )
    checked = 0
    for pack_root in pack_roots:
        name = os.path.basename(pack_root)
        if not is_releasable(pack_root):
            print(f"  [skip] {name}: not releasable "
                  "(no compatibility manifest with artifact_boundaries)")
            continue
        checked += 1
        before = len(failures)
        failures += lint_pack(pack_root)
        failures += smoke_pack(pack_root)
        with tempfile.TemporaryDirectory() as out:
            _meta, build_failures = build_release(pack_root, out)
            failures += build_failures
        status = "ok" if len(failures) == before else "fail"
        print(f"  [{status}] {name} release checks")
    if checked == 0:
        print("  [warn] no releasable packs found")
    return failures


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _resolve_pack(arg: str) -> str:
    """Resolve pack."""
    if os.path.isdir(arg):
        return os.path.abspath(arg)
    candidate = os.path.join(PACKS_ROOT, arg)
    if os.path.isdir(candidate):
        return candidate
    raise SystemExit(f"pack not found: {arg}")


def _report(label: str, failures: list[str]) -> int:
    """Report."""
    if failures:
        print(f"{label}: FAIL ({len(failures)} issue(s))")
        for f in failures:
            print(" - " + f)
        return 1
    print(f"{label}: PASS")
    return 0


def _cmd_metadata(args: argparse.Namespace) -> int:
    """Cmd metadata."""
    print(yaml.safe_dump(release_metadata(_resolve_pack(args.pack)), sort_keys=False))
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    """Cmd build."""
    _meta, failures = build_release(
        _resolve_pack(args.pack), args.out,
        include_build_provenance=args.build_provenance)
    return _report("PACK BUILD", failures)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="RAES pack build / lint / release / profile-smoke gate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("lint", "smoke", "metadata"):
        sp = sub.add_parser(cmd)
        sp.add_argument("--pack", required=True)
    bp = sub.add_parser("build")
    bp.add_argument("--pack", required=True)
    bp.add_argument("--out", required=True)
    bp.add_argument("--build-provenance", action="store_true")
    cp = sub.add_parser("check")
    check_target = cp.add_mutually_exclusive_group()
    check_target.add_argument("--all", action="store_true")
    check_target.add_argument("--pack")
    check_target.add_argument(
        "--packs-root",
        help="Directory whose direct child directories are all pack candidates.",
    )
    args = parser.parse_args(argv)

    dispatch = {
        "lint": lambda: _report("PACK LINT", lint_pack(_resolve_pack(args.pack))),
        "smoke": lambda: _report("PROFILE SMOKE", smoke_pack(_resolve_pack(args.pack))),
        "metadata": lambda: _cmd_metadata(args),
        "build": lambda: _cmd_build(args),
        "check": lambda: _report(
            "PACK RELEASE GATE",
            check(
                [args.pack] if args.pack else None,
                packs_root=args.packs_root,
            ),
        ),
    }
    handler = dispatch.get(args.cmd)
    return handler() if handler else 2


if __name__ == "__main__":
    raise SystemExit(main())
