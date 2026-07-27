"""Static contract for the ownership-boundary guidance (issue #138).

The four-way boundary — RAES semantics, this repository's format, the downstream
scenario or experiment owner, and APTL runtime realization — is a cross-repo
agreement recorded here and in APTL's issue #589 ownership note. Prose drifts
silently: an edit that collapses two owners into one, drops the rule that a pack
never selects runtime implementation, or lets the APTL reference go stale would
leave both sides claiming a boundary they no longer state.

Mirrors the existing documentation-contract tests
(tests/test_readthedocs_config.py) and reuses the same unittest stack rather than
introducing another prose-validation framework. It asserts the load-bearing
claims, not wording.
"""

from __future__ import annotations

import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DOC = _ROOT / "docs" / "ownership-boundary.md"
_PACKS_DOC = _ROOT / "docs" / "scenario-packs.md"

# The APTL-side record this guidance agrees with. Both halves are load-bearing:
# the issue is the decision, the note is its durable statement.
_APTL_ISSUE = "https://github.com/Brad-Edwards/aptl/issues/589"
_APTL_NOTE = "issue-589-scenario-pack-capture-ownership-preflight.md"

# One responsibility phrase per owner. Each must survive independently; losing
# one is how a four-way boundary quietly becomes a three-way one.
_OWNER_RESPONSIBILITIES = {
    "RAES": "portable scenario, workflow, capture, evidence, and inventory",
    "env-packs": (
        "layout contract, templates, schemas, validation, release tooling, and "
        "adoption guidance"
    ),
    "downstream": "experiment design, and the execution choices made with a pack",
    "APTL": (
        "admitted-plan realization, lab lifecycle, trusted source acquisition, "
        "backend observation, and APTL-local evidence persistence"
    ),
}

# What a pack must never be able to select. Criterion five of issue #138 is a
# negative claim, so it needs a positive assertion here to stay true.
_PACK_MUST_NOT_SELECT = (
    "shell commands",
    "host paths",
    "persistence paths",
    "collector implementations",
    "credentials",
)


def _flat(path: pathlib.Path) -> str:
    """Read a page with its line wrapping collapsed.

    The assertions below are about claims, not layout, so re-wrapping a
    paragraph must not fail them.
    """
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class OwnershipBoundaryDocTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _flat(_DOC)

    def test_doc_exists(self) -> None:
        self.assertTrue(_DOC.is_file(), "docs/ownership-boundary.md must exist (#138)")

    def test_names_four_distinct_owners(self) -> None:
        for owner in ("RAES", "RAESystem/env-packs", "APTL"):
            with self.subTest(owner=owner):
                self.assertIn(owner, self.text, f"the boundary must name {owner}")
        self.assertIn(
            "downstream scenario or experiment owner",
            self.text,
            "the downstream scenario or experiment owner is the fourth owner and "
            "must be named distinctly from the format owner (#138)",
        )

    def test_each_owner_keeps_its_responsibilities(self) -> None:
        for owner, phrase in _OWNER_RESPONSIBILITIES.items():
            with self.subTest(owner=owner):
                self.assertIn(
                    phrase, self.text,
                    f"the guidance must still state what {owner} owns (#138)",
                )

    def test_format_owner_is_not_the_scenario_owner(self) -> None:
        # The whole point of the four-way split: owning the format is not owning
        # a workload authored in it.
        self.assertIn(
            "not a scenario", self.text,
            "the guidance must distinguish owning the format from owning a "
            "particular experiment or scenario (#138)",
        )

    def test_pack_cannot_select_runtime_implementation(self) -> None:
        self.assertIn("A pack does not select runtime implementation", self.text)
        for item in _PACK_MUST_NOT_SELECT:
            with self.subTest(item=item):
                self.assertIn(
                    item, self.text,
                    f"the guidance must state that a pack cannot select {item} "
                    "(#138)",
                )

    def test_links_the_aptl_ownership_record(self) -> None:
        self.assertIn(
            _APTL_ISSUE, self.text,
            "the guidance must link APTL issue #589's ownership record (#138)",
        )
        self.assertIn(
            _APTL_NOTE, self.text,
            "the guidance must link the note APTL #589 produced, not just the "
            "issue (#138)",
        )

    def test_reachable_from_the_pack_definition(self) -> None:
        # A boundary nobody navigates to does not constrain anything.
        self.assertIn(
            "ownership-boundary.md",
            _flat(_PACKS_DOC),
            "docs/scenario-packs.md must cross-reference the ownership boundary",
        )


if __name__ == "__main__":
    unittest.main()
