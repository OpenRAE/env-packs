"""Static workflow-contract guard for the ggshield secret scan (ADR 0047).

The GitGuardian App posts its check on pull request commits only, so it does
not report on a dev merge group. ``.github/workflows/gitguardian.yml`` produces
the GitGuardian context on pull requests and on merge groups with ggshield.
This module guards that the job runs on both events, scans the commit range of
each event, fails closed, and does not skip or downgrade a finding.

Action SHA pinning, least-privilege permissions, and hash-locked pip commands
are whole-repository rules in ``tests/test_workflow_permissions.py`` and
``tests/test_dependency_pinning.py``. This module does not restate them.
"""

from __future__ import annotations

import pathlib
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "gitguardian.yml"
_LOCK_INPUT = _ROOT / "requirements" / "ggshield.in"
_JOB = "ggshield"
_CONTEXT = "GitGuardian secret scan"

# ggshield options that turn a finding into a pass or hide it.
_DOWNGRADE_MARKERS = ("--exit-zero", "--ignore-known-secrets", "--ignored-detectors")


def _load() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_block(data: dict) -> dict:
    # PyYAML parses a bare ``on:`` key as the YAML 1.1 boolean ``True``.
    return data.get("on", data.get(True)) or {}


def _scan_step(job: dict) -> dict:
    for step in job.get("steps") or []:
        if "ggshield secret scan" in str(step.get("run", "")):
            return step
    raise AssertionError("no step runs `ggshield secret scan`")


class GitGuardianWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()
        self.on = _on_block(self.data)
        self.job = self.data["jobs"][_JOB]
        self.scan = _scan_step(self.job)

    def test_the_context_name_is_stable(self) -> None:
        # Branch protection requires this context by name. A rename makes the
        # required context stop reporting.
        self.assertEqual(self.job.get("name"), _CONTEXT)

    def test_runs_on_pull_requests_into_dev_and_main(self) -> None:
        self.assertEqual(
            set(self.on["pull_request"]["branches"]), {"dev", "main"},
        )

    def test_runs_on_dev_merge_groups(self) -> None:
        merge_group = self.on.get("merge_group")
        self.assertIsInstance(
            merge_group, dict,
            "the GitGuardian context must report on each dev merge group, or "
            "the merge queue never merges (ADR 0047)",
        )
        self.assertEqual(merge_group.get("types"), ["checks_requested"])
        self.assertEqual(merge_group.get("branches"), ["dev"])

    def test_the_job_has_no_condition(self) -> None:
        # A condition could skip the scan, and a skipped job does not report
        # the required context on the event.
        self.assertNotIn("if", self.job)
        self.assertNotIn("if", self.scan)
        self.assertNotIn("continue-on-error", self.job)
        self.assertNotIn("continue-on-error", self.scan)

    def test_scans_the_commit_range_of_each_event(self) -> None:
        env = self.scan.get("env") or {}
        self.assertIn("github.event.pull_request.base.sha", str(env.get("BASE")))
        self.assertIn("github.event.merge_group.base_sha", str(env.get("BASE")))
        self.assertIn("github.event.pull_request.head.sha", str(env.get("HEAD")))
        self.assertIn("github.event.merge_group.head_sha", str(env.get("HEAD")))
        self.assertIn(
            'ggshield secret scan commit-range "$BASE..$HEAD"', self.scan["run"],
        )

    def test_the_checkout_has_the_full_history(self) -> None:
        checkout = self.job["steps"][0]
        self.assertTrue(str(checkout.get("uses", "")).startswith("actions/checkout@"))
        self.assertEqual((checkout.get("with") or {}).get("fetch-depth"), 0)

    def test_the_api_key_comes_from_the_environment(self) -> None:
        env = self.scan.get("env") or {}
        self.assertEqual(
            env.get("GITGUARDIAN_API_KEY"), "${{ secrets.GITGUARDIAN_API_KEY }}",
        )
        self.assertNotIn("secrets.", self.scan["run"])

    def test_a_missing_api_key_fails_the_job(self) -> None:
        run = self.scan["run"]
        self.assertIn("set -euo pipefail", run)
        self.assertIn('if [ -z "$GITGUARDIAN_API_KEY" ]', run)
        self.assertIn("exit 1", run)

    def test_no_option_downgrades_a_finding(self) -> None:
        for marker in _DOWNGRADE_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, self.scan["run"])

    def test_ggshield_is_pinned_exactly(self) -> None:
        lines = [
            line.split("#")[0].strip()
            for line in _LOCK_INPUT.read_text(encoding="utf-8").splitlines()
        ]
        self.assertIn("ggshield", " ".join(lines))
        self.assertTrue(
            any(line.startswith("ggshield==") for line in lines),
            "requirements/ggshield.in must pin ggshield with `==`",
        )


if __name__ == "__main__":
    unittest.main()
