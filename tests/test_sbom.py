"""Tests for per-pack CycloneDX SBOM generation (ADR 0037, ASP-0004)."""

from __future__ import annotations

import unittest

from raes_env_packs import sbom
from raes_env_packs.component_boundary import Component

_SET_DIGEST = "sha256:" + "a" * 64


def _component(**overrides) -> Component:
    base = {
        "id": "comp-image",
        "scope": "pinned",
        "kind": "container-image",
        "authority": "raes-artifact",
        "ref": "registry.example/app",
        "version": "1.2.3",
        "digest": "sha256:" + "b" * 64,
        "license": "Apache-2.0",
        "provenance": None,
        "upstream_sbom": None,
        "description": "app image",
    }
    base.update(overrides)
    return Component(**base)


def _generate(components) -> dict:
    return sbom.generate_sbom(
        pack_name="techvault",
        pack_version="0.1.0",
        set_digest=_SET_DIGEST,
        components=components,
    )


class GenerationTests(unittest.TestCase):
    def test_document_has_cyclonedx_shape(self) -> None:
        doc = _generate([_component()])
        self.assertEqual(doc["bomFormat"], "CycloneDX")
        self.assertEqual(doc["specVersion"], "1.5")
        self.assertTrue(doc["serialNumber"].startswith("urn:uuid:"))
        self.assertEqual(doc["metadata"]["component"]["name"], "techvault")
        self.assertEqual(doc["metadata"]["component"]["version"], "0.1.0")

    def test_subject_is_bound_to_the_set_digest(self) -> None:
        props = {
            item["name"]: item["value"]
            for item in _generate([])["metadata"]["component"]["properties"]
        }
        self.assertEqual(
            props["raes:associated-artifact-set-digest"], _SET_DIGEST
        )
        self.assertEqual(props["raes:digest-domain"], "raes-associated-artifact-set")

    def test_rejects_non_canonical_set_digest(self) -> None:
        with self.assertRaises(ValueError):
            sbom.generate_sbom(
                pack_name="p", pack_version="1", set_digest="deadbeef", components=[]
            )

    def test_component_mapping(self) -> None:
        entry = _generate([_component()])["components"][0]
        self.assertEqual(entry["type"], "container")
        self.assertEqual(entry["scope"], "required")
        self.assertEqual(entry["version"], "1.2.3")
        self.assertEqual(entry["hashes"], [{"alg": "SHA-256", "content": "b" * 64}])
        self.assertEqual(entry["licenses"], [{"license": {"name": "Apache-2.0"}}])

    def test_external_component_is_optional_and_hashless(self) -> None:
        entry = _generate([
            _component(scope="external", authority="author-declared-external", digest=None)
        ])["components"][0]
        self.assertEqual(entry["scope"], "optional")
        self.assertNotIn("hashes", entry)

    def test_upstream_sbom_is_referenced_not_flattened(self) -> None:
        entry = _generate([_component(upstream_sbom="techvault-upstream-cdx")])["components"][0]
        refs = entry["externalReferences"]
        self.assertEqual(refs[0]["type"], "bom")
        self.assertIn("techvault-upstream-cdx", refs[0]["url"])

    def test_output_is_deterministic(self) -> None:
        a = sbom.sbom_bytes(_generate([_component()]))
        b = sbom.sbom_bytes(_generate([_component()]))
        self.assertEqual(a, b)

    def test_digest_is_canonical_sha256(self) -> None:
        digest = sbom.sbom_digest(_generate([_component()]))
        self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")

    def test_timestamp_is_omitted_by_default(self) -> None:
        self.assertNotIn("timestamp", _generate([])["metadata"])


class ValidationTests(unittest.TestCase):
    def _validate(self, doc, **overrides) -> list:
        kwargs = {
            "expected_name": "techvault",
            "expected_version": "0.1.0",
            "expected_set_digest": _SET_DIGEST,
            "expected_component_refs": frozenset({"comp-image"}),
        }
        kwargs.update(overrides)
        return sbom.validate_sbom_document(doc, **kwargs)

    def test_generated_document_passes_its_own_gate(self) -> None:
        self.assertEqual(self._validate(_generate([_component()])), [])

    def test_subject_mismatch_is_flagged(self) -> None:
        codes = {d.code for d in self._validate(_generate([_component()]), expected_name="other")}
        self.assertIn("sbom.subject-mismatch", codes)

    def test_subject_digest_mismatch_is_flagged(self) -> None:
        codes = {
            d.code
            for d in self._validate(
                _generate([_component()]), expected_set_digest="sha256:" + "c" * 64
            )
        }
        self.assertIn("sbom.subject-digest-mismatch", codes)

    def test_missing_component_coverage_is_flagged(self) -> None:
        codes = {
            d.code
            for d in self._validate(
                _generate([]), expected_component_refs=frozenset({"comp-image"})
            )
        }
        self.assertIn("sbom.coverage-missing", codes)

    def test_non_cyclonedx_document_is_rejected(self) -> None:
        codes = {d.code for d in self._validate({"bomFormat": "SPDX", "specVersion": "2.3"})}
        self.assertIn("sbom.format", codes)


if __name__ == "__main__":
    unittest.main()
