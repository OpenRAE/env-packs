"""Tests for the repo-wide pack build / lint / release / profile-smoke gate.

These exercise ``scripts/ci/pack_release.py`` (issue #49): the static, read-only
release workflow that derives boundary-split release artifacts, lints
profile-support consistency, and smoke-tests that delivery-bundle selection
changes participant exposure. The gate must:

  * fail fast when a pack claims a *supported* delivery bundle it does not ship;
  * separate participant / operator / restricted-private artifacts into
    distinct release roots, and keep restricted material out of the participant
    view;
  * never leak operator tokens into a packaged participant artifact (the leak
    scan is re-run over the staged participant tier);
  * emit versioned release metadata carrying the pack version, the
    environment-pack contract version + digest, the supported profiles, and a
    *bounded* provenance summary (counts/statuses only — no restricted operator vocabulary,
    flags, secrets, or customer-specific prose).

All cases use synthetic temp packs so no real environment pack has to be committed
to this definition/tools repo.
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from unittest import mock

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)  # tests/ sits at the repo root
_PR_PATH = os.path.join(_REPO, "src", "raes_env_packs", "release.py")


def _load_module():
    spec = importlib.util.spec_from_file_location("pack_release_undertest", _PR_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


PR = _load_module()


def _write(path: str, body: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)


def _make_pack(root: str, *, delivery_bundles, profile_bundles=False,
               bundles=None, participant_files=None, boundaries=None):
    """Scaffold a minimal pack the release tool can read.

    Only the fields ``pack_release`` consumes are written; full schema
    validation is ``environment_pack_content_ci.py``'s job, not this gate's.
    """
    # The pack name must equal its directory name for the shared author-static
    # contract to accept it, and a temp-directory basename is not a valid pack
    # slug. Build the pack in a properly named child and return that root; the
    # release gate now requires the author-static gate to pass before it will
    # emit a publication profile (ADR 0028).
    name = "synthpack"
    root = os.path.join(root, name)
    pack_yaml = {
        "name": name,
        "title": "Synthetic test pack",
        "version": "0.1.0",
        "status": "draft",
        "contents": {"profile_bundles": profile_bundles},
        "compatibility_manifest": "pack.compatibility.yaml",
        "provenance_ledger": "docs/provenance-ledger.yaml",
    }
    if profile_bundles:
        pack_yaml["profile_bundles"] = {
            "manifest": "profiles/bundles.yaml",
            "bundles": [{"id": b["id"]} for b in (bundles or [])],
        }
    _write(os.path.join(root, "pack.yaml"), yaml.safe_dump(pack_yaml))

    compat = {
        "schema_version": "environment-pack-compatibility/v2",
        "pack": {"name": name, "title": "Synthetic test pack", "version": "0.1.0",
                 "status": "draft",
                 "source": {"requirement": None, "issues": [], "upstream_references": []}},
        "platform_features": [],
        "assets": [],
        "operator_surfaces": [],
        "validation": {"commands": [], "gates": []},
        "artifact_boundaries": boundaries if boundaries is not None else {
            "participant_visible": [{"path": "assets/briefing/", "export": "public"}],
            "operator_only": [],
            "oracle_only": [],
            "commercial": [],
        },
        "runtime_profiles": [],
        "delivery_bundles": delivery_bundles,
    }
    _write(os.path.join(root, "pack.compatibility.yaml"), yaml.safe_dump(compat))

    _write(os.path.join(root, "assets", "briefing", "brief.md"), "# Mission brief\n")
    # A valid pack ships at least one RAES SDL start-state document.
    _write(os.path.join(root, "sdl", "example.sdl.yaml"),
           f"name: {name}\nnodes:\n  target:\n    type: vm\n")

    prov = {
        "schema_version": "environment-pack-provenance/v3",
        "pack": {"name": name},
        "sources": [{"source_id": "orig", "name": "Original design",
                     "license": "proprietary", "usage": "generated-from",
                     "attribution_required": False}],
        "artifacts": [{"artifact_id": "a1", "path": "assets/", "classification": "open"}],
        "content_safety": {
            "no_real_malware": True, "no_real_third_party_targets": True,
            "no_real_credentials": True, "no_sensitive_data": True,
            "offensive_tooling_boundary": True,
        },
        "review": {"status": "approved", "gates": [
            {"gate_id": "licensing", "status": "approved"},
            {"gate_id": "attribution", "status": "approved"},
            {"gate_id": "sensitive-data", "status": "approved"},
            {"gate_id": "offensive-tooling", "status": "approved"},
        ]},
    }
    _write(os.path.join(root, "docs", "provenance-ledger.yaml"), yaml.safe_dump(prov))

    if bundles is not None:
        _write(os.path.join(root, "profiles", "bundles.yaml"), yaml.safe_dump({
            "schema_version": 1,
            "required_bundles": [b["id"] for b in bundles],
            "bundles": bundles,
        }))
    for rel in (participant_files or []):
        _write(os.path.join(root, "profiles", rel), "content\n")
    return root


# --------------------------------------------------------------------------
# Contract version (AC4 substrate)
# --------------------------------------------------------------------------
class ContractVersionTests(unittest.TestCase):
    def test_reads_version_and_digest_from_readme(self):
        version, digest = PR.load_contract_version()
        self.assertEqual(version, "7")
        self.assertTrue(digest.startswith("sha256:"))
        self.assertEqual(len(digest), len("sha256:") + 64)


# --------------------------------------------------------------------------
# AC1 — fail fast when a supported bundle lacks shipped content
# --------------------------------------------------------------------------
class LintTests(unittest.TestCase):
    def test_supported_bundle_without_profile_layer_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[
                {"bundle_id": "guided", "status": "supported", "audience": "guided"}])
            failures = PR.lint_pack(tmp)
            self.assertTrue(failures)
            self.assertTrue(any("guided" in f for f in failures))

    def test_supported_bundle_missing_entrypoint_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(
                tmp, profile_bundles=True,
                bundles=[{"id": "guided", "audience": "participant",
                          "participant_entrypoints": ["guided/participant/plan.md"],
                          "operator_entrypoints": []}],
                participant_files=[],  # plan.md intentionally absent
                delivery_bundles=[{"bundle_id": "guided", "status": "supported",
                                   "audience": "guided"}])
            failures = PR.lint_pack(tmp)
            self.assertTrue(failures)

    def test_planned_bundle_without_content_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[
                {"bundle_id": "guided", "status": "planned", "audience": "guided"},
                {"bundle_id": "unguided", "status": "not_shipped", "audience": "unguided"}])
            self.assertEqual(PR.lint_pack(tmp), [])


# --------------------------------------------------------------------------
# AC2 — build separates participant / operator / oracle artifacts
# --------------------------------------------------------------------------
class BuildTests(unittest.TestCase):
    def test_build_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[],
                       boundaries={
                           "participant_visible": [{"path": "../escape", "export": "public"}],
                           "operator_only": [], "oracle_only": [], "commercial": []})
            _, failures = PR.build_release(tmp, out)
            self.assertTrue(failures)
            self.assertTrue(any("escape" in f.lower() or "contain" in f.lower()
                                for f in failures))

    def test_build_rejects_participant_restricted_boundary_overlap(self):
        # A participant root that contains a restricted operator root must be
        # rejected before any boundary row is copied (issue #112, ADR 0013).
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[], boundaries={
                "participant_visible": [{"path": "docs/", "export": "public"}],
                "operator_only": [{"path": "docs/runbook.md", "export": "operator"}],
                "oracle_only": [], "commercial": []})
            _, failures = PR.build_release(tmp, out)
            self.assertTrue(
                any("overlaps an operator/oracle/private root" in f for f in failures),
                failures)
            # Rejected before staging: no release tree or scratch dir remains.
            self.assertEqual(os.listdir(out), [])

    def test_failed_build_leaves_no_release_root(self):
        # A failing build must not leave a partial/half-built release tree behind.
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[],
                       boundaries={
                           "participant_visible": [{"path": "../escape", "export": "public"}],
                           "operator_only": [], "oracle_only": [], "commercial": []})
            meta, failures = PR.build_release(tmp, out)
            self.assertTrue(failures)
            root = os.path.join(out, meta["release"]["pack"]["name"] + "-"
                                + meta["release"]["pack"]["version"])
            self.assertFalse(os.path.exists(root))
            # No scratch staging directory should survive either.
            self.assertEqual(os.listdir(out), [])

    def test_build_rejects_nested_symlink_escape(self):
        # A boundary directory row is valid, but a symlinked file inside it points
        # outside the pack — staging must reject it, not follow it into the artifact.
        with tempfile.TemporaryDirectory() as tmp, \
                tempfile.TemporaryDirectory() as out, \
                tempfile.TemporaryDirectory() as outside:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[])
            secret = os.path.join(outside, "operator-secret.md")
            with open(secret, "w", encoding="utf-8") as fh:
                fh.write("out-of-pack secret\n")
            os.symlink(secret, os.path.join(tmp, "assets", "briefing", "leak.md"))
            meta, failures = PR.build_release(tmp, out)
            self.assertTrue(failures)
            self.assertTrue(any("symlink" in f.lower() for f in failures))
            root = os.path.join(out, meta["release"]["pack"]["name"] + "-"
                                + meta["release"]["pack"]["version"])
            # Failed build leaves nothing; the secret never reaches a release tree.
            self.assertFalse(os.path.exists(
                os.path.join(root, "participant", "assets", "briefing", "leak.md")))

    def test_rebuild_does_not_inherit_stale_files(self):
        # The release root is atomically replaced, so a file removed from source
        # between builds must not linger in a later build's artifact.
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[])
            stale = os.path.join(tmp, "assets", "briefing", "stale.md")
            with open(stale, "w", encoding="utf-8") as fh:
                fh.write("# stale\n")
            meta, failures = PR.build_release(tmp, out)
            self.assertEqual(failures, [])
            root = os.path.join(out, meta["release"]["pack"]["name"] + "-"
                                + meta["release"]["pack"]["version"])
            staged_stale = os.path.join(root, "participant", "assets", "briefing", "stale.md")
            self.assertTrue(os.path.isfile(staged_stale))
            os.remove(stale)
            _, failures = PR.build_release(tmp, out)
            self.assertEqual(failures, [])
            self.assertFalse(os.path.exists(staged_stale))

    def test_build_rejects_unsafe_pack_name(self):
        # A pack-controlled name with a path separator must not steer the release
        # root out of --out; the build fails before any file is written.
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            tmp = _make_pack(tmp, profile_bundles=False, delivery_bundles=[])
            pack_yaml_path = os.path.join(tmp, "pack.yaml")
            with open(pack_yaml_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            data["name"] = "../evil"
            with open(pack_yaml_path, "w", encoding="utf-8") as fh:
                yaml.safe_dump(data, fh)
            _, failures = PR.build_release(tmp, out)
            self.assertTrue(failures)
            self.assertTrue(any("slug" in f.lower() for f in failures))
            self.assertEqual(os.listdir(out), [])


# --------------------------------------------------------------------------
# AC3 — profile selection changes exposed content
# --------------------------------------------------------------------------
class SmokeTests(unittest.TestCase):
    # Negative cases exercise every failure-detection branch of smoke_pack via
    # synthetic packs, so a regression that disables detection (a flipped
    # existence check, a dropped under-participant branch, a leak scan that stops
    # running) fails the suite.

    def test_supported_bundle_missing_manifest_row_is_reported(self):
        # A bundle marked supported but absent from profiles/bundles.yaml.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(tmp, profile_bundles=False, bundles=None,
                       delivery_bundles=[{"bundle_id": "guided", "status": "supported",
                                          "audience": "guided"}])
            failures = PR.smoke_pack(tmp)
            self.assertTrue(failures)
            self.assertTrue(any("missing from profiles/bundles.yaml" in f
                                for f in failures))

    def test_missing_entrypoint_file_is_reported(self):
        # A participant entrypoint absent from disk must be caught by smoke, not
        # only by lint.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(
                tmp, profile_bundles=True,
                bundles=[{"id": "guided", "audience": "participant",
                          "participant_entrypoints": ["guided/participant/plan.md"],
                          "operator_entrypoints": []}],
                participant_files=[],  # plan.md intentionally absent
                delivery_bundles=[{"bundle_id": "guided", "status": "supported",
                                   "audience": "guided"}])
            failures = PR.smoke_pack(tmp)
            self.assertTrue(failures)
            self.assertTrue(any("missing entrypoint" in f for f in failures))

    def test_operator_entrypoint_under_participant_root_is_reported(self):
        # An operator entrypoint that resolves under a participant root would expose
        # operator material to participants. The file exists, so only the
        # under-participant branch (not missing-entrypoint) fires.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(
                tmp, profile_bundles=True,
                bundles=[{"id": "guided", "audience": "participant",
                          "participant_entrypoints": [],
                          "operator_entrypoints": ["guided/participant/secret.md"]}],
                participant_files=["guided/participant/secret.md"],
                delivery_bundles=[{"bundle_id": "guided", "status": "supported",
                                   "audience": "guided"}])
            failures = PR.smoke_pack(tmp)
            self.assertTrue(failures)
            self.assertTrue(any("sits under a participant root" in f for f in failures))

    def test_operator_token_in_participant_view_is_reported(self):
        # A participant entrypoint whose body carries an operator token must be
        # caught by the smoke leak scan over participant views.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(
                tmp, profile_bundles=True,
                bundles=[{"id": "guided", "audience": "participant",
                          "participant_entrypoints": ["guided/participant/brief.md"],
                          "operator_entrypoints": []}],
                participant_files=["guided/participant/brief.md"],
                delivery_bundles=[{"bundle_id": "guided", "status": "supported",
                                   "audience": "guided"}])
            # Plant an operator token (an ATT&CK technique id) in the participant view.
            _write(os.path.join(tmp, "profiles", "guided", "participant", "brief.md"),
                   "Participant brief referencing T1059 by mistake.\n")
            failures = PR.smoke_pack(tmp)
            self.assertTrue(failures)
            self.assertTrue(any("participant view leaks" in f for f in failures))

    def test_identical_participant_views_are_reported(self):
        # Two supported bundles with identical participant views means profile
        # selection does not change participant exposure (AC3 violation).
        with tempfile.TemporaryDirectory() as tmp:
            tmp = _make_pack(
                tmp, profile_bundles=True,
                bundles=[{"id": "guided", "audience": "participant",
                          "participant_entrypoints": ["shared/plan.md"],
                          "operator_entrypoints": []},
                         {"id": "unguided", "audience": "participant",
                          "participant_entrypoints": ["shared/plan.md"],
                          "operator_entrypoints": []}],
                participant_files=["shared/plan.md"],
                delivery_bundles=[{"bundle_id": "guided", "status": "supported",
                                   "audience": "guided"},
                                  {"bundle_id": "unguided", "status": "supported",
                                   "audience": "unguided"}])
            failures = PR.smoke_pack(tmp)
            self.assertTrue(failures)
            self.assertTrue(any("identical" in f for f in failures))


# --------------------------------------------------------------------------
# Whole-repo guard — the gate is green on the current repo
# --------------------------------------------------------------------------
class CheckAllTests(unittest.TestCase):
    def test_identity_equivalent_rebuild_is_idempotent(self):
        """Rebuilding the same release from the same bytes is allowed."""
        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(pack, delivery_bundles=[])
            first, failures = PR.build_release(pack, out)
            self.assertEqual(failures, [])
            second, failures = PR.build_release(pack, out)
            self.assertEqual(failures, [])
            from raes_env_packs import publication

            self.assertEqual(
                publication.release_identity(second),
                publication.release_identity(first),
            )

    def test_rebuild_with_different_bytes_at_the_same_version_is_refused(self):
        """A published release is immutable; different bytes are a new release."""
        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(pack, delivery_bundles=[])
            meta, failures = PR.build_release(pack, out)
            self.assertEqual(failures, [])
            root = os.path.join(out, meta["release"]["pack"]["name"] + "-"
                                + meta["release"]["pack"]["version"])
            # Simulate an already-published release bound to other bytes.
            written = os.path.join(root, "release.yaml")
            with open(written, encoding="utf-8") as fh:
                published = yaml.safe_load(fh)
            published["release"]["semantic_parent"] = {
                "parent_ref": "synthpack", "digest": "sha256:" + "a" * 64}
            published["release"]["source_set"] = {
                "manifest_id": "synthpack-associated-artifacts",
                "set_digest": "sha256:" + "b" * 64}
            _write(written, yaml.safe_dump(published))

            _meta, failures = PR.build_release(pack, out)
            self.assertTrue(
                any("immutable" in f for f in failures),
                f"expected an immutability refusal, got {failures}")
            # The published release must still be intact.
            self.assertTrue(os.path.isfile(written))
            with open(written, encoding="utf-8") as fh:
                self.assertEqual(yaml.safe_load(fh), published)

    def test_emitted_profile_validates_against_the_publication_schema(self):
        """The release carrier is a checked consumer contract, not a summary."""
        from raes_env_packs import publication

        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(pack, delivery_bundles=[])
            meta, failures = PR.build_release(pack, out)
            self.assertEqual(failures, [])
            self.assertEqual(
                meta["schema_version"], publication.PUBLICATION_SCHEMA_VERSION
            )
            written = os.path.join(
                out, "synthpack-" + meta["release"]["pack"]["version"], "release.yaml"
            )
            with open(written, encoding="utf-8") as fh:
                on_disk = yaml.safe_load(fh)
            self.assertEqual(
                publication.validate_publication_document(on_disk, requirements={}), []
            )

    def test_build_refuses_a_supply_claim_that_contradicts_raes_authority(self):
        """A release cannot publish an asset for a requirement no author declared."""
        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(pack, delivery_bundles=[])
            pack_yaml = os.path.join(pack, "pack.yaml")
            with open(pack_yaml, encoding="utf-8") as fh:
                manifest = yaml.safe_load(fh)
            manifest["publication_supply"] = "publication-supply.yaml"
            _write(pack_yaml, yaml.safe_dump(manifest))
            _write(os.path.join(pack, "publication-supply.yaml"), yaml.safe_dump({
                "publications": [{
                    "view": "participant",
                    "publication_id": "pub-1",
                    "requirement_id": "never-authored",
                    "requirement_address": "provision/node/target/source-artifact",
                    "mechanism": {
                        "mechanism": "exact-artifact",
                        "profile": "raes-artifact-satisfaction",
                        "version": "1",
                        "digest": "sha256:" + "c" * 64,
                    },
                }],
            }))
            _meta, failures = PR.build_release(pack, out)
            self.assertTrue(
                any("publication." in f for f in failures),
                f"expected a publication authority failure, got {failures}")

    def test_supply_row_with_an_unknown_view_is_reported_not_dropped(self):
        """Silently filtering an unknown view would ship an incomplete release."""
        with tempfile.TemporaryDirectory() as pack, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(pack, delivery_bundles=[])
            pack_yaml = os.path.join(pack, "pack.yaml")
            with open(pack_yaml, encoding="utf-8") as fh:
                manifest = yaml.safe_load(fh)
            manifest["publication_supply"] = "publication-supply.yaml"
            _write(pack_yaml, yaml.safe_dump(manifest))
            _write(os.path.join(pack, "publication-supply.yaml"), yaml.safe_dump({
                "publications": [{
                    "view": "catalog-only",          # not a publication view
                    "publication_id": "pub-1",
                    "requirement_id": "web-image",
                    "requirement_address": "provision.nodes.target.source.source-artifact",
                    "mechanism": {
                        "mechanism": "exact-artifact",
                        "profile": "raes-artifact-satisfaction",
                        "version": "1",
                        "digest": "sha256:" + "c" * 64,
                    },
                }],
            }))
            _meta, failures = PR.build_release(pack, out)
            self.assertTrue(
                any("publication." in f for f in failures),
                f"unknown supply view was silently dropped, got {failures}")

    def test_staging_rejects_a_hardlinked_member(self):
        """Descriptor-anchored staging fails closed on a non-singly-linked file."""
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(parent, delivery_bundles=[])
            target = os.path.join(pack, "assets", "briefing", "brief.md")
            link = os.path.join(pack, "assets", "briefing", "hardlink.md")
            try:
                os.link(target, link)
            except OSError:  # pragma: no cover - platform without hardlinks
                self.skipTest("hardlinks unavailable")
            _meta, failures = PR.build_release(pack, out)
            self.assertTrue(
                any("hardlink.md" in f or "brief.md" in f for f in failures),
                f"a hardlinked member was staged anyway, got {failures}")

    def test_staging_rejects_a_special_file_member(self):
        """A FIFO in a boundary row must not be opened or copied."""
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(parent, delivery_bundles=[])
            fifo = os.path.join(pack, "assets", "briefing", "pipe")
            try:
                os.mkfifo(fifo)
            except (AttributeError, OSError):  # pragma: no cover - platform gap
                self.skipTest("FIFOs unavailable")
            _meta, failures = PR.build_release(pack, out)
            self.assertTrue(
                any("pipe" in f for f in failures),
                f"a special file was staged anyway, got {failures}")

    def test_publication_is_refused_for_a_pack_that_fails_the_shared_gate(self):
        """Invoking the author-static gate and ignoring its verdict would publish
        a consumer contract for a pack that does not satisfy the pack contract."""
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(parent, delivery_bundles=[])
            # Break the pack contract without touching anything the release
            # tool reads directly.
            os.remove(os.path.join(pack, "sdl", "example.sdl.yaml"))
            _meta, failures = PR.build_release(pack, out)
            self.assertTrue(
                any("not publishable" in f for f in failures),
                f"an invalid pack was published anyway, got {failures}")

    def test_view_file_counts_describe_the_staged_bytes(self):
        """A view frozen at zero files would misdescribe the promoted release."""
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as out:
            pack = _make_pack(parent, delivery_bundles=[])
            meta, failures = PR.build_release(pack, out)
            self.assertEqual(failures, [])
            participant = next(
                v for v in meta["release"]["views"] if v["view"] == "participant")
            self.assertGreater(
                participant["file_count"], 0,
                "participant view reports no files despite staging content")
            self.assertEqual(participant["exports"], {"public": participant["file_count"]})

    def test_check_all_passes_on_current_repo(self):
        failures = PR.check()
        self.assertEqual(failures, [], "\n".join(failures))

    def test_check_packs_root_uses_shared_discovery_and_surfaces_its_failures(self):
        def fail_discovery(root, failures, *, require_root=False):
            self.assertEqual(root, "/catalog/packs")
            self.assertTrue(require_root)
            failures.append("PACK-ROOT DISCOVERY FAILED: root unreadable")
            return ()

        with mock.patch.object(PR.cc, "_packs", side_effect=fail_discovery):
            failures = PR.check(packs_root="/catalog/packs")

        self.assertEqual(
            failures,
            ["PACK-ROOT DISCOVERY FAILED: root unreadable"],
        )

    def test_check_missing_explicit_packs_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            failures = PR.check(packs_root=os.path.join(tmp, "missing"))

        self.assertEqual(
            failures,
            ["PACK-ROOT DISCOVERY FAILED: root could not be inspected"],
        )

    def test_check_accepts_an_explicit_pack_path(self):
        with tempfile.TemporaryDirectory() as pack_root, \
                mock.patch.object(PR, "is_releasable", return_value=False) as releasable:
            self.assertEqual(PR.check([pack_root]), [])

        releasable.assert_called_once_with(pack_root)


if __name__ == "__main__":
    unittest.main()
