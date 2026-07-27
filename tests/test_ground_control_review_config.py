"""Static contract for the /implement pre-push review posture (issue #140).

Ground Control's own configuration layer validates the *shape* of these keys and
supplies defaults when they are absent, so a dropped key does not fail there --
it silently falls back. That fallback is exactly the regression this repo cares
about: the review posture would change without any diff to point at.

So this guards the *values*, not the schema. Ground Control remains the schema
authority; nothing here restates its validation rules.

Mirrors the existing config-contract tests (tests/test_readthedocs_config.py,
tests/test_scorecard_workflow.py) and reuses the same unittest + PyYAML stack
rather than introducing another config-validation framework.
"""

from __future__ import annotations

import pathlib
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CONFIG = _ROOT / ".ground-control.yaml"


def _workflow() -> dict:
    data = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise AssertionError(".ground-control.yaml must declare a `workflow` mapping")
    return workflow


class _IntPinAssertions:
    """Assert an integer pin without letting a boolean satisfy it.

    `bool` subclasses `int` and `True == 1` / `False == 0`, so a bare
    assertEqual against 1 or 0 accepts a YAML `true`/`false`. Ground Control
    would reject those at its own schema boundary, but the assertion would have
    already passed -- so the pin would read as verified while the config that
    ships is invalid. Kept as one helper so every integer pin below is checked
    the same way.
    """

    def assertIntPin(self, actual: object, expected: int, message: str) -> None:
        self.assertNotIsInstance(
            actual, bool,
            f"{message} -- got the boolean {actual!r}, not the integer "
            f"{expected!r}",
        )
        self.assertIsInstance(actual, int, message)
        self.assertEqual(actual, expected, message)


class PrePushReviewCapTests(_IntPinAssertions, unittest.TestCase):
    """One Codex cycle and one test-quality cycle before push."""

    def setUp(self) -> None:
        self.workflow = _workflow()

    def test_codex_review_cap_is_pinned_to_one(self) -> None:
        section = self.workflow.get("codex_review")
        self.assertIsInstance(
            section, dict,
            "workflow.codex_review must be declared explicitly; relying on the "
            "Ground Control default lets a change to that default silently alter "
            "this repo's review posture (#140)",
        )
        self.assertIntPin(
            section.get("pre_push_cap"), 1,
            "workflow.codex_review.pre_push_cap must be 1 (#140)",
        )

    def test_test_quality_review_cap_is_pinned_to_one(self) -> None:
        section = self.workflow.get("test_quality_review")
        self.assertIsInstance(
            section, dict,
            "workflow.test_quality_review must be declared explicitly (#140)",
        )
        self.assertIntPin(
            section.get("pre_push_cap"), 1,
            "workflow.test_quality_review.pre_push_cap must be 1 (#140)",
        )


class ReviewDispositionTests(_IntPinAssertions, unittest.TestCase):
    """Reaching a review cap must always escalate to a human."""

    def setUp(self) -> None:
        self.disposition = _workflow().get("review_disposition")
        self.assertIsInstance(
            self.disposition, dict,
            "workflow.review_disposition must be declared explicitly (#140)",
        )

    def test_automatic_disposition_is_disabled(self) -> None:
        # assertIs, not assertEqual: YAML `0`/`no`/`""` are all falsy but only
        # the boolean is the declared contract.
        self.assertIs(
            self.disposition.get("enabled"), False,
            "automatic disposition of the review cap must be off so reaching a "
            "cap escalates to a human (#140)",
        )

    def test_mode_remains_shadow(self) -> None:
        self.assertEqual(self.disposition.get("mode"), "shadow")

    def test_no_automatic_overrides_are_granted(self) -> None:
        # Inert while `enabled` is false, but pinned to 0 so enabling disposition
        # later cannot also hand out automatic extra cycles as a side effect.
        self.assertIntPin(
            self.disposition.get("max_auto_overrides"), 0,
            "review_disposition.max_auto_overrides must be 0 (#140)",
        )

    def test_judge_does_not_participate(self) -> None:
        judge = self.disposition.get("judge")
        self.assertIsInstance(judge, dict, "review_disposition.judge must be declared")
        self.assertIs(judge.get("enabled"), False)


class ReviewConfigPlacementTests(unittest.TestCase):
    def test_review_keys_live_under_workflow(self) -> None:
        # Ground Control reads these from `workflow:`. At the top level they
        # parse fine and are ignored, which is the quiet way this pin dies.
        data = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
        for key in ("codex_review", "test_quality_review", "review_disposition"):
            with self.subTest(key=key):
                self.assertNotIn(
                    key, data,
                    f"{key} must be nested under `workflow:`, not declared at the "
                    "top level where Ground Control will not read it (#140)",
                )


if __name__ == "__main__":
    unittest.main()
