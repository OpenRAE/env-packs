"""Tests for the published-release path: SBOM + provenance evidence (ADR 0037)."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

import yaml

from raes_env_packs import release, release_provenance
from raes_env_packs import sbom as sbom_module

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_TECHVAULT = os.path.join(_REPO, "packs", "techvault")


class LocalProjectionTests(unittest.TestCase):
    def test_local_projection_carries_v2_but_no_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            metadata, failures = release.build_release(_TECHVAULT, out)
            self.assertEqual(failures, [])
            self.assertEqual(metadata["schema_version"], "environment-pack-publication/v2")
            self.assertNotIn("evidence", metadata)
            self.assertFalse(
                os.path.exists(os.path.join(out, "techvault-0.1.0",
                                            "techvault-0.1.0.cdx.json"))
            )


class PublishedReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._out = tempfile.TemporaryDirectory()
        cls.metadata, cls.failures = release.build_release(
            _TECHVAULT, cls._out.name, publish=True)
        cls.release_root = os.path.join(cls._out.name, "techvault-0.1.0")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._out.cleanup()

    def test_publish_succeeds_and_emits_evidence_block(self) -> None:
        self.assertEqual(self.failures, [])
        evidence = self.metadata["evidence"]
        self.assertEqual(evidence["sbom"]["format"], "CycloneDX")
        self.assertRegex(evidence["sbom"]["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertRegex(evidence["provenance"]["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(evidence["builder"]["id"], release._builder_id())

    def test_evidence_files_are_written_beside_the_views(self) -> None:
        for name in ("techvault-0.1.0.cdx.json", "techvault-0.1.0.provenance.json",
                     "release.yaml"):
            self.assertTrue(os.path.isfile(os.path.join(self.release_root, name)), name)

    def test_written_sbom_digest_matches_the_evidence_reference(self) -> None:
        import hashlib
        with open(os.path.join(self.release_root, "techvault-0.1.0.cdx.json"), "rb") as fh:
            raw = fh.read()
        self.assertEqual(
            "sha256:" + hashlib.sha256(raw).hexdigest(),
            self.metadata["evidence"]["sbom"]["digest"],
        )

    def test_sbom_covers_the_pinned_container_images(self) -> None:
        with open(os.path.join(self.release_root, "techvault-0.1.0.cdx.json")) as fh:
            doc = json.load(fh)
        self.assertEqual(doc["bomFormat"], "CycloneDX")
        self.assertGreaterEqual(len(doc["components"]), 30)
        containers = [c for c in doc["components"] if c["type"] == "container"]
        self.assertGreaterEqual(len(containers), 10)
        # The metadata component is bound to the release subject.
        props = {p["name"]: p["value"] for p in doc["metadata"]["component"]["properties"]}
        self.assertIn("raes:associated-artifact-set-digest", props)

    def test_written_evidence_passes_its_own_consumer_gate(self) -> None:
        with open(os.path.join(self.release_root, "techvault-0.1.0.cdx.json")) as fh:
            sbom_doc = json.load(fh)
        with open(os.path.join(self.release_root, "techvault-0.1.0.provenance.json")) as fh:
            prov_doc = json.load(fh)
        set_digest = self.metadata["release"]["source_set"]["set_digest"]
        refs = frozenset(c["bom-ref"] for c in sbom_doc["components"])
        self.assertEqual(
            sbom_module.validate_sbom_document(
                sbom_doc, expected_name="techvault", expected_version="0.1.0",
                expected_set_digest=set_digest, expected_component_refs=refs),
            [],
        )
        self.assertEqual(
            release_provenance.validate_release_provenance(
                prov_doc, expected_name="techvault", expected_version="0.1.0",
                expected_set_digest=set_digest,
                expected_sbom_digest=self.metadata["evidence"]["sbom"]["digest"]),
            [],
        )


class ContentIdentityMandatoryTests(unittest.TestCase):
    def _releasable_pack_without_content_identity(self, root: str) -> str:
        pack = os.path.join(root, "nocid")
        os.makedirs(os.path.join(pack, "assets"))
        with open(os.path.join(pack, "assets", "brief.txt"), "w", encoding="utf-8") as fh:
            fh.write("participant briefing\n")
        with open(os.path.join(pack, "pack.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump({
                "name": "nocid", "version": "0.1.0",
                "compatibility_manifest": "pack.compatibility.yaml",
            }, fh)
        with open(os.path.join(pack, "pack.compatibility.yaml"), "w", encoding="utf-8") as fh:
            yaml.safe_dump({
                "schema_version": "environment-pack-compatibility/v2",
                "artifact_boundaries": {
                    "participant_visible": [{"path": "assets/brief.txt", "export": "public"}],
                },
            }, fh)
        return pack

    def test_publishing_without_content_identity_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            pack = self._releasable_pack_without_content_identity(root)
            with tempfile.TemporaryDirectory() as out:
                _meta, failures = release.build_release(pack, out, publish=True)
        self.assertTrue(
            any("content identity" in failure for failure in failures),
            failures,
        )


if __name__ == "__main__":
    unittest.main()
