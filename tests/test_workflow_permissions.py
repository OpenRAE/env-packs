"""Repo-wide GITHUB_TOKEN permission and action-pinning contract for every workflow.

Issue #142 closes the OpenSSF Scorecard ``Token-Permissions`` and
``Pinned-Dependencies`` findings. Both are whole-repository properties: Scorecard
scores the *worst* workflow, so a single new file that forgets a top-level
``permissions`` block or uses a floating action tag reopens the finding.

This module therefore asserts the invariants once, over every file discovered in
``.github/workflows/``, instead of restating them in each workflow's specialized
test (the architecture preflight for #142 calls for exactly one repo-wide
contract here). ``tests/test_scorecard_workflow.py`` and
``tests/test_codeql_workflow.py`` keep their workflow-specific assertions --
triggers, step ordering, publish inputs -- and no longer need to own the generic
rules.

Why top-level read-only specifically: Scorecard's scorer
(``checks/evaluation/permissions.go``) only applies ``reduceBy()`` in the
top-level branch. A job-level write costs nothing *provided* the same file's top
level is read-only; it is penalized only when the top level is write-all or
undeclared. So least privilege here means "declare read-only at the top, put
every write on the job that needs it" -- not "never write".
"""

from __future__ import annotations

import pathlib
import re
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW_DIR = _ROOT / ".github" / "workflows"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Read-only spellings GitHub accepts at the top level. ``{}`` (no permissions at
# all) is also read-only in effect, but Scorecard reports an explicit empty block
# differently from a declared read scope, so it is not accepted here.
_READ_ONLY_SCALARS = frozenset({"read-all"})

# Local actions (``./.github/actions/...``) and reusable workflows in this repo
# are not third-party supply chain, so they are exempt from SHA pinning.
_LOCAL_PREFIXES = ("./", ".github/")


def _workflows() -> list[pathlib.Path]:
    paths = sorted(
        p for p in _WORKFLOW_DIR.iterdir() if p.suffix in (".yml", ".yaml") and p.is_file()
    )
    if not paths:
        raise AssertionError(f"no workflows found under {_WORKFLOW_DIR}")
    return paths


def _load(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _is_read_only(perms: object) -> bool:
    """True when a ``permissions`` value grants no write scope."""
    if isinstance(perms, str):
        return perms in _READ_ONLY_SCALARS
    if isinstance(perms, dict):
        return all(str(level) in ("read", "none") for level in perms.values())
    return False


def _steps(job: object) -> list[dict]:
    if not isinstance(job, dict):
        return []
    return [s for s in job.get("steps", []) or [] if isinstance(s, dict)]


class PermissionRuleTests(unittest.TestCase):
    """Exercise the read-only rule against crafted values, not just this repo.

    Every other assertion in this module reads the repository's current -- now
    compliant -- workflows. Without these cases, `_is_read_only` could be
    replaced by `return True` and the whole file would still pass, asserting
    nothing.
    """

    def test_read_only_values_are_accepted(self) -> None:
        for value in ("read-all", {"contents": "read"},
                      {"contents": "read", "id-token": "none"}, {}):
            with self.subTest(permissions=value):
                self.assertTrue(_is_read_only(value))

    def test_write_and_undeclared_values_are_rejected(self) -> None:
        for value in (
            None,                                          # undeclared
            "write-all",                                   # blanket write
            {"contents": "write"},                         # a single write scope
            {"contents": "read", "security-events": "write"},  # read plus a write
            "some-nonsense",                               # unrecognized scalar
        ):
            with self.subTest(permissions=value):
                self.assertFalse(_is_read_only(value))


class TopLevelPermissionsTests(unittest.TestCase):
    """Every workflow declares a read-only token at the top level (#142)."""

    def test_every_workflow_declares_top_level_permissions(self) -> None:
        for path in _workflows():
            with self.subTest(workflow=path.name):
                data = _load(path)
                self.assertIn(
                    "permissions",
                    data,
                    f"{path.name} must declare a top-level `permissions` block; an "
                    "undeclared top level inherits the repository default and is "
                    "scored as excessive by Scorecard Token-Permissions (#142)",
                )

    def test_top_level_permissions_are_read_only(self) -> None:
        for path in _workflows():
            with self.subTest(workflow=path.name):
                perms = _load(path).get("permissions")
                self.assertTrue(
                    _is_read_only(perms),
                    f"{path.name} top-level permissions must be read-only "
                    f"(`read-all`, or every scope set to read/none), got {perms!r}. "
                    "Move any write scope onto the job that needs it (#142).",
                )


class JobLevelPermissionsTests(unittest.TestCase):
    """Writes are allowed, but only where they are actually needed."""

    def test_jobs_that_declare_permissions_use_a_mapping(self) -> None:
        # A job-level `write-all` is as bad as a top-level one: it hands every
        # scope to the job rather than the ones it uses.
        for path in _workflows():
            data = _load(path)
            for name, job in (data.get("jobs") or {}).items():
                perms = job.get("permissions") if isinstance(job, dict) else None
                if perms is None:
                    continue
                with self.subTest(workflow=path.name, job=name):
                    self.assertIsInstance(
                        perms,
                        dict,
                        f"{path.name}:{name} must enumerate individual scopes, "
                        f"not use the blanket {perms!r} (#142)",
                    )

    def test_no_job_grants_write_without_a_read_only_top_level(self) -> None:
        # This is the exact combination Scorecard penalizes: a job-level write
        # sitting under an undeclared or write-all top level.
        for path in _workflows():
            data = _load(path)
            top = data.get("permissions")
            for name, job in (data.get("jobs") or {}).items():
                perms = job.get("permissions") if isinstance(job, dict) else None
                if not isinstance(perms, dict):
                    continue
                writes = {s for s, lvl in perms.items() if str(lvl) == "write"}
                if not writes:
                    continue
                with self.subTest(workflow=path.name, job=name):
                    self.assertTrue(
                        _is_read_only(top),
                        f"{path.name}:{name} holds write scopes {sorted(writes)} "
                        "while the workflow's top-level permissions are not "
                        f"read-only ({top!r}) (#142)",
                    )


class ActionPinningTests(unittest.TestCase):
    """Third-party actions stay pinned to immutable commit SHAs (ADR 0004)."""

    def test_every_third_party_action_is_sha_pinned(self) -> None:
        for path in _workflows():
            data = _load(path)
            for name, job in (data.get("jobs") or {}).items():
                for step in _steps(job):
                    uses = str(step.get("uses", "")).strip()
                    if not uses or uses.startswith(_LOCAL_PREFIXES):
                        continue
                    with self.subTest(workflow=path.name, job=name, uses=uses):
                        self.assertIn(
                            "@",
                            uses,
                            f"{path.name}:{name} uses {uses!r} with no ref",
                        )
                        ref = uses.split("@", 1)[1].split()[0]
                        self.assertRegex(
                            ref,
                            _SHA_RE,
                            f"{path.name}:{name} must pin {uses!r} to a 40-hex "
                            "commit SHA, not a floating tag; Dependabot moves the "
                            "pin (ADR 0004)",
                        )


if __name__ == "__main__":
    unittest.main()
