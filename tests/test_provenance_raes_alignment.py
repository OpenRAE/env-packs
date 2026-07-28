"""Guard: the pack provenance ledger aligns to the RAES reusable-asset trust policy.

Issue #82 (ADR 0009 / ADR 0010): RAES core owns the ecosystem trust contract
``reusable-asset-trust-policy/v1`` (ADR-071), which is authoritative for a
environment pack's *integrity, authenticity, provenance-lock, governance-source,
and artifact-checksum* semantics — a pack is a ``reusable_scenario`` asset in
that vocabulary. This repository is strictly subordinate to RAES: it consumes
that policy as the authority and does **not** define a parallel trust model.

These tests lock the three acceptance invariants of issue #82 so a regression
cannot silently reintroduce a bespoke trust model:

1. The shipped provenance schema **references** the RAES trust policy as the
   authority for integrity/authenticity.
2. Every retained ledger field is **documented** (schema ``$comment`` mapping +
   contract prose) as either RAES-mapped or genuinely pack-domain.
3. The schema **does not re-define** any RAES-owned evidence class as its own
   vocabulary (enum value, ``const``, or property key). Prose that *names* an
   RAES concept to defer to it is allowed; declaring it as pack vocabulary is
   not.

The broad, pack-level anti-extension guard is issue #83's scope; this file is
scoped to the provenance contract's RAES alignment only.
"""

from __future__ import annotations

import importlib.util
import os
import unittest
from collections.abc import Iterator

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_PKG = os.path.join(_REPO, "src", "raes_env_packs")
_CI_PATH = os.path.join(_PKG, "content_ci.py")

# The RAES evidence classes (reusable-asset-trust-policy/v1). The pack ledger may
# name these in prose to defer to RAES, but must not declare them as its own
# schema vocabulary.
RAES_EVIDENCE_CLASSES = frozenset({
    "integrity_digest",
    "authenticity_signature",
    "provenance_lock_record",
    "governance_source",
    "artifact_checksum",
})
# Substring that establishes a document references the RAES trust authority.
RAES_POLICY_MARKER = "reusable-asset-trust-policy"
# Retained top-level ledger blocks whose disposition must be documented.
RETAINED_LEDGER_BLOCKS = ("sources", "artifacts", "content_safety", "review", "overlays")


def _load_ci():
    spec = importlib.util.spec_from_file_location("environment_pack_content_ci_alignment", _CI_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


CI = _load_ci()


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _iter_schema_vocabulary(node: object) -> Iterator[str]:
    """Yield every token a schema declares as its *own* vocabulary.

    That is property keys, ``enum`` items, and ``const`` values — NOT the free
    text of ``title`` / ``description`` / ``$comment`` / ``$id``, where naming an
    RAES concept in order to defer to it is legitimate.
    """
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for key, child in props.items():
                yield str(key)
                yield from _iter_schema_vocabulary(child)
        enum = node.get("enum")
        if isinstance(enum, list):
            for item in enum:
                if isinstance(item, str):
                    yield item
        const = node.get("const")
        if isinstance(const, str):
            yield const
        for key, child in node.items():
            if key in ("properties", "enum", "const"):
                continue
            yield from _iter_schema_vocabulary(child)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_schema_vocabulary(item)


class ProvenanceAcesAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema_path = CI.provenance_schema_path()
        self.schema_text = _read(self.schema_path)
        self.schema = yaml.safe_load(self.schema_text)
        self.assertIsInstance(self.schema, dict)

    def test_schema_references_aces_trust_authority(self) -> None:
        """Acceptance #1: the schema names the RAES trust policy as the authority."""
        lowered = self.schema_text.lower()
        self.assertIn(RAES_POLICY_MARKER, lowered,
                      "provenance schema must reference the RAES reusable-asset trust policy")
        self.assertTrue(
            "adr-071" in lowered or "adr 0010" in lowered,
            "provenance schema must cite the governing ADR (ADR-071 / ADR 0010)")

    def test_schema_documents_field_disposition(self) -> None:
        """Acceptance #2: every retained ledger block's disposition is documented."""
        comment = self.schema.get("$comment")
        self.assertIsInstance(comment, str,
                              "provenance schema must carry a top-level $comment mapping")
        for block in RETAINED_LEDGER_BLOCKS:
            self.assertIn(block, comment,
                          f"schema $comment mapping must document the {block!r} block")

    def test_schema_does_not_redefine_aces_evidence_classes(self) -> None:
        """Acceptance #3: no RAES evidence class is declared as pack vocabulary."""
        vocab = set(_iter_schema_vocabulary(self.schema))
        redefined = vocab & RAES_EVIDENCE_CLASSES
        self.assertEqual(
            redefined, set(),
            f"provenance schema re-defines RAES-owned evidence class(es) as its own "
            f"vocabulary: {sorted(redefined)}; defer these to RAES instead")

    def test_contract_and_docs_reference_aces_policy(self) -> None:
        """Acceptance #1: contract prose + docs reference the RAES trust policy."""
        contract = os.path.join(CI._RES, "contract", "pack-layout.md")
        docs = os.path.join(_REPO, "docs", "environment-packs.md")
        for path in (contract, docs):
            self.assertTrue(os.path.isfile(path), f"missing prose file: {path}")
            self.assertIn(RAES_POLICY_MARKER, _read(path).lower(),
                          f"{os.path.basename(path)} must reference the RAES trust policy")

    def test_example_ledger_still_validates(self) -> None:
        """The alignment change must not break instance validation of the example."""
        example = CI._load_yaml(CI.provenance_example_path(), [], "provenance example")
        self.assertIsInstance(example, dict)
        errors: list[str] = []
        CI._validate_json_schema_subset(example, self.schema, self.schema, "$", errors)
        self.assertEqual(errors, [], f"example ledger no longer validates: {errors}")

    def test_template_ledger_parses_and_references_aces(self) -> None:
        """The author-facing template header names the RAES authority (comment only)."""
        template = os.path.join(CI._RES, "template", "docs", "provenance-ledger.yaml")
        self.assertTrue(os.path.isfile(template))
        text = _read(template)
        self.assertIsInstance(yaml.safe_load(text), dict)
        self.assertIn(RAES_POLICY_MARKER, text.lower(),
                      "template provenance ledger must point at the RAES trust authority")


if __name__ == "__main__":
    unittest.main()
