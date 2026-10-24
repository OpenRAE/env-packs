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
        for var in ("GITHUB_EVENT_PATH", "PR_TITLE", "PR_COMMIT_MESSAGES_FILE"):
            os.environ.pop(var, None)

    def test_valid_conventional_titles_pass(self):
        for title in (
            "feat: add the widget",
            "fix(parser): handle empty input",
            "docs: clarify the contract",
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

    def test_breaking_marker_in_title_rejected(self):
        for title in ("feat!: drop the legacy field", "fix(parser)!: change output"):
            with self.subTest(title=title):
                self.assertEqual(_rules(title), {guard.RULE_BREAKING_MARKER})

    def test_breaking_markers_in_merge_text_rejected(self):
        for text in (
            "Drop the field.\n\nBREAKING CHANGE: the field is gone",
            "BREAKING-CHANGE: the field is gone",
            "feat!: drop the field",
            "* feat(api)!: drop the field\n\n* fix: tidy",
            "intro\n  - fix!: change output",
        ):
            with self.subTest(text=text):
                self.assertEqual(
                    [v.rule_id for v in guard.validate_merge_text(text, source="x")],
                    [guard.RULE_BREAKING_MARKER],
                )

    def test_merge_text_without_markers_passes(self):
        for text in (
            None,
            "",
            "* feat: add the widget\n\n* fix: handle empty input",
            "Release-As: 7.0.0",
            "This breaks nothing important.",
            "Use feat! carefully in prose.",
        ):
            with self.subTest(text=text):
                self.assertEqual(guard.validate_merge_text(text, source="x"), [])

    def _event(self, title, login, body=None):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        pull_request = {"title": title, "user": {"login": login}, "body": body}
        json.dump({"pull_request": pull_request}, fh)
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def _commits(self, *pages):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        json.dump(
            [[{"commit": {"message": message}} for message in page] for page in pages], fh
        )
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        return fh.name

    def test_main_rejects_breaking_footer_in_body(self):
        path = self._event("feat: ok", "someone", body="BREAKING CHANGE: gone")
        self.assertEqual(guard.main(["--event-path", path]), 1)

    def test_main_checks_every_commit_page(self):
        event = self._event("feat: ok", "someone", body="Adds a widget.")
        clean = self._commits(["feat: add"], ["fix: tidy\n\nRelease-As: 7.0.0"])
        self.assertEqual(
            guard.main(["--event-path", event, "--commit-messages-file", clean]), 0
        )
        breaking = self._commits(["feat: add"], ["fix: tidy\n\nBREAKING CHANGE: gone"])
        self.assertEqual(
            guard.main(["--event-path", event, "--commit-messages-file", breaking]), 1
        )

    def test_main_reads_commit_messages_file_from_env(self):
        breaking = self._commits(["feat!: drop"])
        with mock.patch.dict(os.environ, {"PR_COMMIT_MESSAGES_FILE": breaking}):
            self.assertEqual(guard.main(["--title", "feat: ok"]), 1)

    def test_main_fails_closed_on_malformed_commit_messages_file(self):
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        fh.write('{"not": "pages"}')
        fh.close()
        self.addCleanup(os.unlink, fh.name)
        self.assertEqual(
            guard.main(["--title", "feat: ok", "--commit-messages-file", fh.name]), 2
        )

    def test_event_path_validates_human_titles(self):
        self.assertEqual(guard.main(["--event-path", self._event("feat: ok", "someone")]), 0)
        self.assertEqual(guard.main(["--event-path", self._event("nope", "someone")]), 1)

    def test_bot_authors_are_exempt(self):
        # A non-conforming title from a bot author is skipped, not rejected.
        path = self._event("Bump PyYAML from 6.0 to 6.0.1", "dependabot[bot]")
        self.assertEqual(guard.main(["--event-path", path]), 0)


if __name__ == "__main__":
    unittest.main()
