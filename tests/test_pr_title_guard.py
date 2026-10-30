"""Tests for the repository-side PR title guard (tools/check_pr_title.py).

The CI workflow and these tests call the same ``validate_pr_title``, so the
policy can't drift between the workflow YAML and local enforcement (ADR 0006).
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_GUARD = Path(__file__).resolve().parents[1] / "tools" / "check_pr_title.py"
_spec = importlib.util.spec_from_file_location("check_pr_title", _GUARD)
guard = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
# Register before exec so @dataclass annotation resolution can find the module.
sys.modules[_spec.name] = guard
_spec.loader.exec_module(guard)


def _rules(title: str) -> set[str]:
    return {v.rule_id for v in guard.validate_pr_title(title)}


class PrTitleGuardTests(unittest.TestCase):
    def setUp(self):
        # main() falls back to the ambient GITHUB_EVENT_PATH / PR_TITLE when those
        # inputs are not passed explicitly. Under a bot-authored PR (e.g. a
        # dependabot run), GITHUB_EVENT_PATH points at a real event whose author
        # is `<bot>[bot]`, which would silently trigger main()'s automated-author
        # exemption and mask the `--title` assertions below (return 0, not 1).
        # Scrub those vars so each test exercises only the inputs it passes.
        env = mock.patch.dict(os.environ, clear=False)
        env.start()
        self.addCleanup(env.stop)
        for var in ("GITHUB_EVENT_PATH", "PR_TITLE"):
            os.environ.pop(var, None)

    def test_valid_conventional_titles_pass(self):
        for title in (
            "feat: add the widget",
            "fix(parser): handle empty input",
            "docs: clarify the contract",
            "feat!: drop the legacy field",
            "chore: bump dev deps",
        ):
            with self.subTest(title=title):
                self.assertEqual(guard.validate_pr_title(title), [])

    def test_branded_prefixes_rejected(self):
        for title in ("[claude] feat: x", "[Codex] fix: y", "  [openai] docs: z"):
            with self.subTest(title=title):
                self.assertIn(guard.RULE_AGENT_BRAND, _rules(title))

    def test_tool_name_later_in_subject_is_allowed(self):
        self.assertEqual(guard.validate_pr_title("docs: document the claude adapter"), [])

    def test_non_conventional_rejected(self):
        for title in ("add the widget", "Fix: thing", "feat add thing", "wip: stuff"):
            with self.subTest(title=title):
                self.assertIn(guard.RULE_CONVENTIONAL, _rules(title))

    def test_uppercase_subject_rejected(self):
        self.assertIn(guard.RULE_SUBJECT_LOWERCASE, _rules("feat: Add the widget"))

    def test_empty_rejected(self):
        self.assertIn(guard.RULE_EMPTY, _rules("   "))

    def test_main_accepts_via_title_arg(self):
        self.assertEqual(guard.main(["--title", "feat: ok"]), 0)

    def test_main_rejects_via_title_arg(self):
        self.assertEqual(guard.main(["--title", "[claude] nope"]), 1)

    def _event(self, title, login):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump({"pull_request": {"title": title, "user": {"login": login}}}, fh)
        fh.close()
        return fh.name

    def test_event_path_validates_human_titles(self):
        self.assertEqual(guard.main(["--event-path", self._event("feat: ok", "someone")]), 0)
        self.assertEqual(guard.main(["--event-path", self._event("nope", "someone")]), 1)

    def test_bot_authors_are_exempt(self):
        # A non-conforming title from a bot author is skipped, not rejected.
        path = self._event("Bump PyYAML from 6.0 to 6.0.1", "dependabot[bot]")
        self.assertEqual(guard.main(["--event-path", path]), 0)


if __name__ == "__main__":
    unittest.main()
