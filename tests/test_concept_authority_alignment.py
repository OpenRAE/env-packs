"""Guard: pack vocabularies defer governed concepts to RAES concept-authority.

Issue #87 and ADR 0021: RAES core governs the concept vocabularies —
ATT&CK and ATLAS offensive-behavior tactics, UCO concept families, and the
controlled vocabularies — under ``contracts/concept-authority/``. Those
classifications have one semantic home: RAES SDL behavior specifications,
validated by the pinned ``raes.parse_sdl``. This repository consumes them and
never restates them as pack vocabulary.

These tests lock the acceptance invariants of issue #87 so a regression cannot
silently reintroduce a governed vocabulary as a pack-side field:

1. The canonical challenge contract carries no ``challenges[].category``; the
   shared validator rejects it at that exact structured path.
2. The pack-domain provenance ledger carries no ``sources[].kind``.
3. No packaged schema restates an RAES-governed ATT&CK/ATLAS tactic vocabulary
   (tactic id or tactic shortname) as its own ``enum`` / ``const``.
4. The provenance schema, layout contract, docs, and ADR 0021 reference the RAES
   concept-authority as the authority for the governed concepts.

Mirrors ``test_provenance_raes_alignment.py`` (issue #82): naming an RAES concept
in prose to defer to it — or listing one to *forbid* restating it — is
legitimate; declaring it as pack vocabulary is not.
"""

from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

import yaml

from raes_env_packs import validate_pack

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_PKG = _REPO / "src" / "raes_env_packs"
_SCHEMAS_DIR = _PKG / "resources" / "schemas"
_TEMPLATE_DIR = _PKG / "resources" / "template"
_PROVENANCE_SCHEMA = _SCHEMAS_DIR / "provenance.schema.yaml"
_CHALLENGES_TEMPLATE = _TEMPLATE_DIR / "challenges" / "challenges.yaml"
_CONTRACT = _PKG / "resources" / "contract" / "pack-layout.md"
_DOCS = _REPO / "docs" / "environment-packs.md"
_ADR = (
    _REPO
    / "docs"
    / "decisions"
    / "adrs"
    / "0021-adopt-raes-environment-pack-identity.md"
)

# Substring establishing a document references the governed RAES corpus.
CONCEPT_AUTHORITY_MARKER = "concept-authority"

# RAES concept-authority vocabulary ids for the ATT&CK / ATLAS offensive-behaviour
# tactic classifications. The governed terms are read LIVE from the pinned RAES
# distribution (the ADR 0021 seam) rather than snapshotted here, so a term added
# by a future pinned release is enforced automatically and no local catalog can
# drift out of step with the authority.
_TACTIC_VOCABULARY_IDS = (
    "participant-offensive-behavior-activities",
    "participant-ai-offensive-behavior-activities",
)
# ATT&CK (TA0001) and ATLAS (AML.TA0000) tactic identifiers.
_TACTIC_ID_RE = re.compile(r"^(?:AML\.)?TA\d{4}$")


def _governed_tactic_terms() -> frozenset[str]:
    """Governed ATT&CK/ATLAS tactic shortnames from the pinned RAES corpus.

    Read through the public ``raes_contracts.controlled_vocabularies`` API of the
    exactly pinned ``raes`` distribution, which ships the concept-authority
    corpus — the ADR 0021 extensibility seam. Deriving the set instead of
    snapshotting it means the guard tracks the authority automatically.
    """
    from raes_contracts.controlled_vocabularies import (
        load_controlled_vocabulary_catalog,
    )

    catalog = load_controlled_vocabulary_catalog()
    terms: set[str] = set()
    for vocabulary_id in _TACTIC_VOCABULARY_IDS:
        definition = catalog.vocabularies.get(vocabulary_id)
        if definition is not None:
            terms.update(definition.terms)
    return frozenset(terms)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _packaged_schemas() -> list[Path]:
    return sorted(_SCHEMAS_DIR.glob("*.schema.yaml"))


def _iter_schema_enum_const(node: object) -> Iterator[str]:
    """Yield every ``enum`` item and ``const`` value a schema declares.

    Deliberately excludes property keys: a pack packaging field such as the
    compatibility manifest's top-level ``assets`` is a homograph of the UCO
    ``assets`` concept family, so only closed-value vocabulary (``enum`` /
    ``const``) is checked for a governed-term restatement.
    """
    if isinstance(node, dict):
        enum = node.get("enum")
        if isinstance(enum, list):
            for item in enum:
                if isinstance(item, str):
                    yield item
        const = node.get("const")
        if isinstance(const, str):
            yield const
        for value in node.values():
            yield from _iter_schema_enum_const(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_schema_enum_const(item)


class ProvenanceSourceKindRemovedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = yaml.safe_load(_read(_PROVENANCE_SCHEMA))
        self.assertIsInstance(self.schema, dict)

    def _source_item_schema(self) -> dict:
        sources = (self.schema.get("properties") or {}).get("sources") or {}
        item = sources.get("items")
        self.assertIsInstance(item, dict, "sources[] must declare an items schema")
        return item

    def test_source_kind_property_is_gone(self) -> None:
        """Acceptance: the ledger no longer declares a local `sources[].kind`."""
        props = self._source_item_schema().get("properties") or {}
        self.assertNotIn(
            "kind", props,
            "provenance sources[] must not carry a local `kind` classification; "
            "governed concept vocabulary lives in RAES concept-authority (ADR 0021)")

    def test_source_kind_is_not_required(self) -> None:
        required = self._source_item_schema().get("required") or []
        self.assertNotIn("kind", required)

    def test_source_kind_is_rejected_as_unknown(self) -> None:
        """A ledger that still carries `kind` is rejected (additionalProperties)."""
        item = self._source_item_schema()
        self.assertIs(
            item.get("additionalProperties"), False,
            "sources[] must be closed so a reintroduced `kind` fails validation")


class ConceptAuthorityRestatementTests(unittest.TestCase):
    def test_no_schema_restates_aces_tactic_vocabulary(self) -> None:
        """Acceptance: governed ATT&CK/ATLAS tactics are not pack vocabulary."""
        governed = _governed_tactic_terms()
        self.assertTrue(
            governed, "expected governed tactic terms from the pinned RAES corpus")
        for path in _packaged_schemas():
            schema = yaml.safe_load(_read(path))
            values = set(_iter_schema_enum_const(schema))
            tactic_ids = {v for v in values if _TACTIC_ID_RE.fullmatch(v)}
            restated = values & governed
            self.assertEqual(
                tactic_ids, set(),
                f"{path.name} restates RAES tactic id(s) as pack vocabulary: "
                f"{sorted(tactic_ids)}; defer to RAES SDL / concept-authority")
            self.assertEqual(
                restated, set(),
                f"{path.name} restates RAES-governed tactic term(s) as pack "
                f"vocabulary: {sorted(restated)}; defer to RAES SDL")

    def test_authority_is_referenced_in_schema_contract_and_docs(self) -> None:
        """Acceptance: the governed authority is named where it applies."""
        for path in (_PROVENANCE_SCHEMA, _CONTRACT, _DOCS, _ADR):
            self.assertTrue(path.is_file(), f"missing file: {path}")
            self.assertIn(
                CONCEPT_AUTHORITY_MARKER, _read(path).lower(),
                f"{path.name} must reference the RAES concept-authority")


class ChallengeCategoryTemplateTests(unittest.TestCase):
    def test_template_challenges_declare_no_category(self) -> None:
        """The bundled challenge template carries no `category` field."""
        doc = yaml.safe_load(_read(_CHALLENGES_TEMPLATE))
        challenges = (doc or {}).get("challenges") or []
        for entry in challenges:
            if isinstance(entry, dict):
                self.assertNotIn("category", entry)


class ChallengeCategoryGuardTests(unittest.TestCase):
    """The shared validator rejects `challenges[].category` for a real pack."""

    def _pack(self, challenges_yaml: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        root = tmp / "catpack"
        (root / "challenges").mkdir(parents=True)
        (root / "pack.yaml").write_text(
            "name: catpack\ntitle: Cat\nversion: 0.1.0\n", encoding="utf-8")
        (root / "challenges" / "challenges.yaml").write_text(
            challenges_yaml, encoding="utf-8")
        return root

    def test_category_is_rejected_at_exact_path(self) -> None:
        root = self._pack(
            "challenges:\n  - flag_id: f1\n    category: corporate\n")
        errors = validate_pack(root).errors
        self.assertTrue(
            any(e.startswith("challenges.category.forbidden") for e in errors),
            f"category must be rejected; got {errors}")

    def test_category_free_challenges_carry_no_forbidden_code(self) -> None:
        root = self._pack(
            "challenges:\n  - flag_id: f1\n    title: Mind the Mailbox\n")
        errors = validate_pack(root).errors
        self.assertFalse(
            any(e.startswith("challenges.category.forbidden") for e in errors),
            f"category-free challenges must not trip the guard; got {errors}")


if __name__ == "__main__":
    unittest.main()
