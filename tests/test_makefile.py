"""Contract for the repository Makefile's promotion helper (issue #156).

``make devmain`` opens the ``dev`` -> ``main`` promotion PR. The behaviour that
matters cannot be observed without opening a real pull request, so the target is
driven here against a **fake ``gh``** substituted through the Makefile's ``GH``
seam. Nothing in this module touches the live GitHub API.

Three of these tests guard failure modes that are cheap to reintroduce and
expensive to discover in production:

* A bare ``make`` must not open a pull request. Without an explicit default
  goal, Make runs the *first* target in the file, so adding a target above
  ``devmain`` -- or reordering the file -- would turn an idle ``make`` into a
  live promotion PR against whatever ``dev`` currently holds.
* ``gh`` must be allowed to fail. GitHub is the authoritative duplicate
  boundary: it refuses a second open PR for the same head/base pair. Silencing
  that error (a ``-`` recipe prefix, ``|| true``, redirected stderr) would turn
  "a promotion is already open" into a silent success.
* The title must stay non-releasing and distinct. release-please owns
  ``chore(main): release X.Y.Z`` on ``main``; a promotion subject that collided
  with it, or that carried a releasing type, would corrupt the release decision
  (ADR 0008, ADR 0019).

Mirrors the existing static-contract tests (tests/test_readthedocs_config.py,
tests/test_workflow_permissions.py) and reuses the same unittest stack rather
than introducing another harness.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_MAKEFILE = _ROOT / "Makefile"

# The promotion subject is a policy constant, not a preference. `chore` does not
# release (ADR 0008 rubric) and the unscoped form cannot collide with
# release-please's own `chore(main): release X.Y.Z` PR.
_EXPECTED_TITLE = "chore: promote dev to main"

_HAVE_MAKE = shutil.which("make") is not None


def _write_fake_gh(tmpdir: pathlib.Path, exit_code: int = 0) -> tuple[pathlib.Path, pathlib.Path]:
    """Create a stand-in for `gh` that records its argv and exits `exit_code`.

    Arguments are recorded NUL-separated because the PR body is deliberately
    multi-line; a newline-separated record could not be parsed back unambiguously.
    """
    record = tmpdir / "argv"
    script = tmpdir / "fake-gh"
    script.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\0' \"$@\" > '{record}'\n"
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script, record


def _run_make(*goals: str, gh: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", *goals, f"GH={gh}"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )


def _argv(record: pathlib.Path) -> list[str]:
    if not record.exists():
        return []
    raw = record.read_bytes().decode("utf-8")
    return [part for part in raw.split("\0") if part != ""]


@unittest.skipUnless(_HAVE_MAKE, "make is not installed")
class DevmainInvocationTests(unittest.TestCase):
    """`make devmain` must ask `gh` for exactly the promotion PR and nothing else."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmpdir = pathlib.Path(self._tmp.name)
        self.gh, self.record = _write_fake_gh(tmpdir)
        self.addCleanup(self._tmp.cleanup)

    def _devmain_argv(self) -> list[str]:
        result = _run_make("devmain", gh=self.gh)
        self.assertEqual(
            result.returncode, 0,
            f"make devmain failed unexpectedly:\n{result.stdout}\n{result.stderr}",
        )
        argv = _argv(self.record)
        self.assertTrue(argv, "devmain did not invoke gh at all")
        return argv

    def test_creates_a_pull_request(self) -> None:
        argv = self._devmain_argv()
        self.assertEqual(argv[:2], ["pr", "create"])

    def test_promotes_dev_into_main(self) -> None:
        # The direction is the whole point; a flipped base/head would open a
        # main -> dev PR, which is sync-main-to-dev.yml's job, not this one.
        argv = self._devmain_argv()
        self.assertIn("--base", argv)
        self.assertEqual(argv[argv.index("--base") + 1], "main")
        self.assertIn("--head", argv)
        self.assertEqual(argv[argv.index("--head") + 1], "dev")

    def test_title_is_the_deterministic_non_releasing_subject(self) -> None:
        argv = self._devmain_argv()
        self.assertIn("--title", argv)
        title = argv[argv.index("--title") + 1]
        self.assertEqual(title, _EXPECTED_TITLE)
        # Never GitHub's branch-name default, which is what shipped on #122/#134/#144.
        self.assertNotEqual(title.strip().lower(), "dev")
        # A releasing type here would let the promotion subject, rather than the
        # commits being promoted, drive the version bump.
        self.assertRegex(title, r"^(chore|docs|refactor|test|ci|build)(\([^)]*\))?: ")
        # release-please owns `chore(main): release ...`; this must not look like it.
        self.assertNotIn("release", title.lower())

    def test_body_tells_the_merger_not_to_squash(self) -> None:
        argv = self._devmain_argv()
        self.assertIn("--body", argv)
        body = argv[argv.index("--body") + 1]
        self.assertTrue(body.strip(), "the promotion PR body must not be empty")
        lowered = body.lower()
        self.assertIn("merge commit", lowered)
        self.assertRegex(
            lowered, r"(do not|don't|never|not) squash",
            "the body must forbid squashing, which is the failure this helper exists to prevent",
        )
        self.assertIn(
            "release-please", lowered,
            "the body must give the reason, not just the instruction",
        )

    def test_does_not_delegate_the_body_to_the_template_or_an_editor(self) -> None:
        # --fill / --web / an editor would let PULL_REQUEST_TEMPLATE.md supply
        # unchecked boilerplate, which is what the hand-opened promotions carried.
        argv = self._devmain_argv()
        for forbidden in ("--fill", "--fill-first", "--web", "--editor"):
            self.assertNotIn(forbidden, argv)

    def test_opens_the_pr_and_nothing_else(self) -> None:
        # The helper must not approve, merge, enable auto-merge, tag, or publish.
        argv = self._devmain_argv()
        joined = " ".join(argv)
        for forbidden in ("--auto", "--merge", "--squash", "--rebase", "--admin"):
            self.assertNotIn(forbidden, argv, f"devmain must not pass {forbidden}")
        self.assertNotIn("pr merge", joined)
        self.assertNotIn("pr review", joined)


@unittest.skipUnless(_HAVE_MAKE, "make is not installed")
class MakefileSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_bare_make_does_not_open_a_pull_request(self) -> None:
        gh, record = _write_fake_gh(self.tmpdir)
        result = _run_make(gh=gh)
        self.assertEqual(
            result.returncode, 0,
            f"a bare `make` must succeed harmlessly:\n{result.stdout}\n{result.stderr}",
        )
        self.assertEqual(
            _argv(record), [],
            "a bare `make` invoked gh -- the default goal must never open a PR",
        )

    def test_gh_failure_fails_the_target(self) -> None:
        # GitHub rejects a duplicate promotion PR with a nonzero exit. That error
        # is the duplicate guard; swallowing it would silently report success.
        gh, _ = _write_fake_gh(self.tmpdir, exit_code=1)
        result = _run_make("devmain", gh=gh)
        self.assertNotEqual(
            result.returncode, 0,
            "make devmain must propagate a failing gh instead of reporting success",
        )


class MakefileStaticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(_MAKEFILE.is_file(), "the repository must have a Makefile")
        self.text = _MAKEFILE.read_text(encoding="utf-8")

    def test_targets_are_phony(self) -> None:
        phony = " ".join(re.findall(r"^\.PHONY:(.*)$", self.text, re.MULTILINE)).split()
        self.assertIn("devmain", phony)
        self.assertIn("help", phony)

    def test_declares_a_safe_default_goal(self) -> None:
        match = re.search(r"^\.DEFAULT_GOAL\s*:=\s*(\S+)", self.text, re.MULTILINE)
        self.assertIsNotNone(match, ".DEFAULT_GOAL must be declared explicitly")
        self.assertNotEqual(
            match.group(1), "devmain",
            "the default goal must not be the target that opens a pull request",
        )

    def test_gh_is_overridable_for_testing(self) -> None:
        self.assertIsNotNone(
            re.search(r"^GH\s*\?=\s*gh\s*$", self.text, re.MULTILINE),
            "the gh binary must be a `?=` seam so it can be substituted in tests",
        )

    def test_devmain_recipe_does_not_suppress_failure(self) -> None:
        # No DOTALL: `.` must stop at the newline so the capture is the recipe's
        # own tab-indented lines and not the rest of the file.
        recipe = re.search(r"^devmain:.*\n((?:\t.*\n)+)", self.text, re.MULTILINE)
        self.assertIsNotNone(recipe, "devmain must have a recipe")
        body = recipe.group(1)
        self.assertNotIn("|| true", body, "devmain must not swallow a gh failure")
        self.assertNotIn("2>/dev/null", body, "devmain must not hide gh's error output")
        for line in body.splitlines():
            self.assertFalse(
                line.startswith("\t-"),
                "a `-` recipe prefix would make Make ignore a failing gh",
            )

    def test_no_owner_or_repository_is_hardcoded(self) -> None:
        # gh resolves the repository from the checkout (or the operator's GH_REPO).
        # A literal would break on a fork and went stale once already when this
        # repository was transferred.
        self.assertNotIn("OpenRAE/", self.text)
        self.assertNotIn("Brad-Edwards/", self.text)


if __name__ == "__main__":
    unittest.main()
