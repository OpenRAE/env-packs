"""Tests for pack-release provenance statements (ADR 0037, ASP-0004)."""

from __future__ import annotations

import unittest

from raes_env_packs import release_provenance as rp

_SET = "sha256:" + "a" * 64
_SBOM = "sha256:" + "b" * 64
_LOCK = "sha256:" + "c" * 64


_TOP_LEVEL_KEYS = ("pack_name", "pack_version", "set_digest")


def _build(**overrides) -> dict:
    top = {
        "pack_name": "techvault",
        "pack_version": "0.1.0",
        "set_digest": _SET,
    }
    facts = {
        "semantic_parent": {"parent_ref": "techvault", "digest": None},
        "source_revision": "abc123",
        "builder_id": "github-actions://openrae/env-packs",
        "lock": {"digest": _LOCK, "modules": [{"module_id": "infra.identity"}]},
        "view_sets": [{"view": "participant", "set_digest": _SET}],
        "sbom": {"digest": _SBOM, "format": "CycloneDX", "path": "techvault-0.1.0.cdx.json"},
    }
    for key, value in overrides.items():
        target = top if key in _TOP_LEVEL_KEYS else facts
        target[key] = value
    return rp.build_release_provenance(**top, facts=rp.ReleaseFacts(**facts))


class BuildTests(unittest.TestCase):
    def test_statement_shape(self) -> None:
        doc = _build()
        self.assertEqual(doc["_type"], rp.STATEMENT_TYPE)
        self.assertEqual(doc["predicateType"], rp.PREDICATE_TYPE)
        subject = doc["subject"][0]
        self.assertEqual(subject["name"], "techvault@0.1.0")
        self.assertEqual(subject["digest"], {rp.SUBJECT_DIGEST_ALG: "a" * 64})

    def test_predicate_binds_every_release_fact(self) -> None:
        predicate = _build()["predicate"]
        self.assertEqual(predicate["pack"], {"name": "techvault", "version": "0.1.0"})
        self.assertEqual(predicate["source_revision"], "abc123")
        self.assertEqual(predicate["builder"]["id"], "github-actions://openrae/env-packs")
        self.assertEqual(predicate["lock"]["digest"], _LOCK)
        self.assertEqual(predicate["sbom"]["digest"], _SBOM)
        self.assertEqual(predicate["views"][0]["view"], "participant")

    def test_rejects_non_canonical_set_digest(self) -> None:
        with self.assertRaises(ValueError):
            _build(set_digest="nope")

    def test_output_is_deterministic(self) -> None:
        first = rp.provenance_bytes(_build())
        second = rp.provenance_bytes(_build())
        self.assertEqual(first, second)

    def test_digest_is_canonical(self) -> None:
        self.assertRegex(rp.provenance_digest(_build()), r"^sha256:[0-9a-f]{64}$")

    def test_lockless_pack_records_null_lock(self) -> None:
        self.assertIsNone(_build(lock=None)["predicate"]["lock"])


class ValidateTests(unittest.TestCase):
    def _validate(self, doc, **overrides) -> set:
        kwargs = {
            "expected_name": "techvault",
            "expected_version": "0.1.0",
            "expected_set_digest": _SET,
            "expected_sbom_digest": _SBOM,
        }
        kwargs.update(overrides)
        return {d.code for d in rp.validate_release_provenance(doc, **kwargs)}

    def test_generated_statement_passes(self) -> None:
        self.assertEqual(self._validate(_build()), set())

    def test_subject_mismatch(self) -> None:
        self.assertIn(
            "provenance.subject-mismatch",
            self._validate(_build(), expected_set_digest="sha256:" + "d" * 64),
        )

    def test_pack_mismatch(self) -> None:
        self.assertIn("provenance.pack-mismatch", self._validate(_build(), expected_version="9.9.9"))

    def test_sbom_digest_mismatch(self) -> None:
        self.assertIn(
            "provenance.sbom-digest-mismatch",
            self._validate(_build(), expected_sbom_digest="sha256:" + "e" * 64),
        )

    def test_source_revision_checked_only_when_expected(self) -> None:
        self.assertEqual(self._validate(_build()), set())
        self.assertIn(
            "provenance.source-mismatch",
            self._validate(_build(), expected_source_revision="different"),
        )

    def test_lock_digest_checked_only_when_expected(self) -> None:
        self.assertIn(
            "provenance.lock-mismatch",
            self._validate(_build(), expected_lock_digest="sha256:" + "f" * 64),
        )

    def test_wrong_predicate_type_is_rejected(self) -> None:
        doc = _build()
        doc["predicateType"] = "https://example/other"
        self.assertIn("provenance.predicate-type", self._validate(doc))

    def test_missing_sbom_binding(self) -> None:
        doc = _build()
        del doc["predicate"]["sbom"]
        self.assertIn("provenance.binding-missing", self._validate(doc))


if __name__ == "__main__":
    unittest.main()
