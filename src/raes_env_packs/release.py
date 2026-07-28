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

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# content_ci is a sibling module, imported after the sys.path insert above.
import content_ci as cc
from raes_env_packs import validation

REPO = cc._REPO
PACKS_ROOT = cc.PACKS_ROOT
METADATA_SCHEMA_VERSION = 1

# Boundary group -> release tier directory. This mapping is the single
# parameter over the boundary vocabulary (extensibility seam); the tool never
# guesses a tier from an ad hoc directory name. The runtime-visibility tier is
# the *group*; the per-row ``export`` distribution class is recorded as metadata,
# not used to pick the tier.
BOUNDARY_TIERS = {
    "participant_visible": "participant",
    "operator_only": "operator",
    "oracle_only": "oracle",
    "commercial": "commercial",
}
PARTICIPANT_TIER = "participant"

# The contract version line lives in the packaged contract source as a single,
# machine-detectable marker so consumers detect contract drift without parsing
# prose.
_CONTRACT_VERSION_RE = re.compile(r"Environment-pack contract version:\**\s*`([^`]+)`")
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


def _safe_member(path: str, root_real: str) -> bool:
    """A copyable member: not a symlink and resolving inside the pack root."""
    return not os.path.islink(path) and _within(root_real, path)


def _stage(src: str, dst: str, pack_root: str) -> tuple[int, list[str]]:
    """Copy a file or directory tree to ``dst``; return ``(file_count, errors)``.

    Every copied member is re-validated against ``pack_root``: ``_safe_pack_path``
    only vets the declared boundary row, but a directory row can contain a
    symlinked descendant pointing outside the pack (or at an operator/oracle
    source), and ``shutil.copy2`` follows file symlinks by default. ``os.walk``
    does not descend into symlinked directories (``followlinks=False``), and any
    symlinked file or otherwise-escaping member is rejected rather than copied, so
    a pack cannot smuggle out-of-boundary content into a release artifact.
    """
    root_real = os.path.realpath(pack_root)
    if not _safe_member(src, root_real):
        return 0, [f"member {os.path.relpath(src, pack_root)} is a symlink or escapes pack root"]
    if not os.path.isdir(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return 1, []
    return _stage_tree(src, dst, pack_root, root_real)


def _stage_tree(src: str, dst: str, pack_root: str,
                root_real: str) -> tuple[int, list[str]]:
    """Stage tree."""
    count = 0
    errors: list[str] = []
    for dirpath, _dirs, files in os.walk(src):
        rel = os.path.relpath(dirpath, src)
        target = dst if rel == "." else os.path.join(dst, rel)
        os.makedirs(target, exist_ok=True)
        for fname in files:
            fsrc = os.path.join(dirpath, fname)
            if not _safe_member(fsrc, root_real):
                errors.append(
                    f"member {os.path.relpath(fsrc, pack_root)} is a symlink or "
                    "escapes pack root")
                continue
            shutil.copy2(fsrc, os.path.join(target, fname))
            count += 1
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


def _stage_boundary_row(pc: "PackContracts", pack_root: str, group: str, tier: str,
                        row: object, staging: str,
                        tier_stats: dict[str, dict[str, object]]) -> list[str]:
    """Stage boundary row."""
    rel = row.get("path") if isinstance(row, dict) else None
    if not isinstance(rel, str):
        return []
    ok, why = _safe_pack_path(pack_root, rel)
    src = os.path.join(pack_root, rel)
    if not ok:
        problem = why
    elif not os.path.exists(src):
        problem = "does not exist"
    else:
        problem = None
    if problem:
        return [f"{pc.name}: boundary {group} path {rel} {problem}"]
    export = row.get("export")
    copied, stage_errors = _stage(
        src, os.path.join(staging, tier, os.path.normpath(rel)), pack_root)
    tier_stats[tier]["file_count"] += copied
    if isinstance(export, str):
        tier_stats[tier]["exports"][export] = (
            tier_stats[tier]["exports"].get(export, 0) + copied)
    return [f"{pc.name}: boundary {group} {err}" for err in stage_errors]


def _stage_boundaries(pc: "PackContracts", pack_root: str, boundaries: object,
                      staging: str, tier_stats: dict[str, dict[str, object]]) -> list[str]:
    """Stage boundaries."""
    if not isinstance(boundaries, dict):
        return []
    failures: list[str] = []
    for group, tier in BOUNDARY_TIERS.items():
        for row in (boundaries.get(group) or []):
            failures += _stage_boundary_row(
                pc, pack_root, group, tier, row, staging, tier_stats)
    return failures


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
    metadata["artifact_tiers"] = tier_stats

    release_root, staging, failures = _resolve_release_paths(pc, out_dir, version)
    if failures:
        return metadata, failures

    if os.path.exists(staging):
        shutil.rmtree(staging)
    # validated path; creates the resolved out_dir as a parent
    os.makedirs(staging)
    try:
        boundaries = (pc.compatibility or {}).get("artifact_boundaries")
        # Reject a participant/restricted boundary overlap before copying any
        # row (ADR 0013): release must be independently safe even if the shared
        # validation gate did not run first. On overlap, skip staging entirely so
        # no boundary row is copied; the participant leak scan is defense-in-depth,
        # not the declaration boundary.
        overlap_fields = validation._boundary_overlaps(boundaries)
        if overlap_fields:
            failures += [
                f"{pc.name}: artifact boundary {field} overlaps an "
                "operator/oracle/private root; refusing to stage a participant export"
                for field in overlap_fields]
        else:
            failures += _stage_boundaries(pc, pack_root, boundaries, staging, tier_stats)
            # The participant tier is the one surface that must never carry an
            # operator token; re-run the redacted leak scan over the *staged*
            # artifact.
            failures += [
                f"{pc.name}: participant release artifact leaks a {label} at "
                f"{PARTICIPANT_TIER}/{locator} (match redacted)"
                for label, locator in scan_tier_for_leaks(
                    os.path.join(staging, PARTICIPANT_TIER))]
        if failures:
            return metadata, failures

        with open(os.path.join(staging, "release.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump(metadata, fh, sort_keys=False)
        # Atomic promote: replace any prior build so stale files never linger.
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


def release_metadata(pack_root: str, *, include_build_provenance: bool = False,
                     repo_root: str = REPO) -> dict[str, object]:
    """Release metadata."""
    pc = PackContracts(pack_root)
    compat = pc.compatibility or {}
    version, digest = load_contract_version()

    supported = _supported_bundle_ids(compat)
    runtime = _runtime_profile_ids(compat)

    metadata: dict[str, object] = {
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
        "pack": {
            "name": pc.name,
            "title": pc.pack_yaml.get("title"),
            "version": str(pc.pack_yaml.get("version") or "0.0.0"),
            "status": pc.pack_yaml.get("status"),
        },
        "contract": {"version": version, "source": CONTRACT_SOURCE_LABEL, "digest": digest},
        "supported_profiles": supported,
        "runtime_profiles": runtime,
        "provenance_summary": _provenance_summary(pc.provenance),
    }
    if include_build_provenance:
        metadata["build_provenance"] = {"git_commit": _git_commit(repo_root)}
    return metadata


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
