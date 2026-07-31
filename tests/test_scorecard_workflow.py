"""Static workflow-contract guard for the OpenSSF Scorecard workflow.

Issue #58 adds a dedicated ``ossf/scorecard-action`` workflow that publishes a
supply-chain posture score (weekly, plus on ``push`` to ``main`` so the badge
appears promptly) and a Scorecard badge in the README. The live published score
and badge rendering can only be observed on a real default-branch run, but the
workflow *shape* that produces them is guarded here so a dropped trigger, a
broadened token permission, an unpinned action, a disabled publish, or a
persisted credential fails CI.

Scope is deliberately narrow — the Scorecard workflow's structural contract and
the README badge endpoint only. It reuses the repo's existing unittest + PyYAML
stack rather than adding a new validation framework (mirrors
tests/test_codeql_workflow.py). Action SHAs are asserted to be 40-hex pins but
never hard-coded here; Dependabot owns their movement.
"""

from __future__ import annotations

import pathlib
import re
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "scorecard.yml"
_README = _ROOT / "README.md"

_CHECKOUT_ACTION = "actions/checkout@"
_SCORECARD_ACTION = "ossf/scorecard-action@"
_UPLOAD_ARTIFACT_ACTION = "actions/upload-artifact@"
_UPLOAD_SARIF_ACTION = "github/codeql-action/upload-sarif@"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Only these actions may appear in the publishing job. OpenSSF's publishing API
# applies strict workflow-shape validation and can reject an unapproved action.
_APPROVED_ACTIONS = (
    _CHECKOUT_ACTION,
    _SCORECARD_ACTION,
    _UPLOAD_ARTIFACT_ACTION,
    _UPLOAD_SARIF_ACTION,
)

# Public repo identity the OpenSSF badge/viewer endpoints are keyed on. These
# endpoints are keyed by slug and do not follow GitHub's redirect for a
# transferred repository, so this must track the repo's current path: after the
# move to OpenRAE/env-packs the old slug still serves a frozen pre-transfer
# score while new runs publish under the new one (#142).
_REPO_SLUG = "github.com/OpenRAE/env-packs"


def _load() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_block(data: dict) -> dict:
    # PyYAML parses a bare ``on:`` key as the YAML 1.1 boolean ``True``, so the
    # triggers live under the ``True`` key, not ``"on"`` (see
    # tests/test_codeql_workflow.py).
    return data.get("on", data.get(True))


def _scorecard_job(data: dict) -> dict:
    # Find the job that runs Scorecard rather than hard-coding its name.
    for job in data["jobs"].values():
        steps = job.get("steps", [])
        if any(str(s.get("uses", "")).startswith(_SCORECARD_ACTION) for s in steps):
            return job
    raise AssertionError("no job runs ossf/scorecard-action")


class ScorecardWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()
        self.on = _on_block(self.data)
        self.job = _scorecard_job(self.data)
        self.steps = self.job["steps"]

    def _uses(self) -> list[str]:
        return [str(s.get("uses", "")) for s in self.steps if s.get("uses")]

    def _step(self, prefix: str) -> dict:
        for step in self.steps:
            if str(step.get("uses", "")).startswith(prefix):
                return step
        raise AssertionError(f"missing step using {prefix}")

    def _index(self, prefix: str) -> int:
        for index, step in enumerate(self.steps):
            if str(step.get("uses", "")).startswith(prefix):
                return index
        return -1

    # --- triggers -------------------------------------------------------
    def test_trigger_surface_is_schedule_and_push_only(self) -> None:
        # Publishing runs from the default branch only. No pull_request /
        # pull_request_target (would run on untrusted forks) and no
        # workflow_dispatch — the surface is exactly schedule + push.
        self.assertEqual(set(self.on), {"schedule", "push"})

    def test_push_targets_main_only(self) -> None:
        branches = self.on["push"]["branches"]
        self.assertEqual(
            set(branches),
            {"main"},
            "Scorecard must publish only from the default branch (#58)",
        )

    def test_has_weekly_schedule(self) -> None:
        schedule = self.on.get("schedule")
        self.assertTrue(schedule, "Scorecard must run on a weekly schedule (#58)")
        crons = [entry["cron"] for entry in schedule]
        self.assertTrue(crons, "schedule must define at least one cron")
        for cron in crons:
            fields = cron.split()
            self.assertEqual(len(fields), 5, f"cron must have 5 fields: {cron!r}")
            minute, _hour, dom, _month, dow = fields
            # Weekly cadence: a specific day-of-week, any day-of-month.
            self.assertNotEqual(dow, "*", f"schedule must be weekly (specific weekday): {cron!r}")
            self.assertEqual(dom, "*", f"weekly schedule must not pin day-of-month: {cron!r}")
            # Off the top of the hour — GitHub delays top-of-hour scheduled runs.
            self.assertNotEqual(minute, "0", f"avoid top-of-hour scheduling: {cron!r}")

    # --- permissions ----------------------------------------------------
    def test_workflow_level_permissions_read_only(self) -> None:
        perms = self.data.get("permissions")
        self.assertIsNotNone(perms, "Scorecard workflow must set explicit permissions")
        if isinstance(perms, str):
            self.assertEqual(perms, "read-all", "workflow-level token must be read-only")
        else:
            for scope, level in perms.items():
                self.assertEqual(level, "read", f"workflow-level {scope} must be read, not {level!r}")

    def test_job_permissions_least_privilege(self) -> None:
        perms = self.job.get("permissions")
        self.assertIsNotNone(perms, "Scorecard job must set explicit permissions")
        self.assertEqual(perms.get("security-events"), "write",
                         "job needs security-events: write to upload SARIF")
        self.assertEqual(perms.get("id-token"), "write",
                         "job needs id-token: write to publish via OIDC")
        self.assertNotEqual(perms.get("contents"), "write",
                            "Scorecard must never hold contents: write")
        # Any scope beyond the two required writes must stay read-only.
        for scope, level in perms.items():
            if scope in ("security-events", "id-token"):
                continue
            self.assertEqual(level, "read", f"job {scope} must be read, not {level!r}")

    # --- publish + SARIF inputs -----------------------------------------
    def test_scorecard_publishes_results_as_sarif(self) -> None:
        with_block = self._step(_SCORECARD_ACTION).get("with", {})
        self.assertTrue(with_block.get("publish_results"),
                        "publish_results must be true so the API/badge populate")
        self.assertEqual(with_block.get("results_format"), "sarif")
        self.assertTrue(with_block.get("results_file"),
                        "results_file must name the SARIF output")

    # --- checkout hardening ---------------------------------------------
    def test_checkout_does_not_persist_credentials(self) -> None:
        with_block = self._step(_CHECKOUT_ACTION).get("with", {})
        # assertIs (not assertFalse): a missing key returns None, which is falsy
        # but means GitHub's default of *persisting* credentials — the insecure
        # case. Require the explicit boolean False, not merely a falsy value.
        self.assertIs(with_block.get("persist-credentials"), False,
                      "checkout must not persist credentials in the Scorecard job")

    # --- actions: approved set, pinned, ordered -------------------------
    def test_only_approved_actions_used(self) -> None:
        for uses in self._uses():
            self.assertTrue(
                any(uses.startswith(p) for p in _APPROVED_ACTIONS),
                f"unapproved action in Scorecard job: {uses!r}",
            )

    def test_required_actions_present_and_sha_pinned(self) -> None:
        for prefix in (_CHECKOUT_ACTION, _SCORECARD_ACTION, _UPLOAD_SARIF_ACTION):
            uses = next((u for u in self._uses() if u.startswith(prefix)), None)
            self.assertIsNotNone(uses, f"missing step using {prefix}")
        for uses in self._uses():
            ref = uses.split("@", 1)[1].split()[0]
            self.assertRegex(ref, _SHA_RE,
                             f"action must be pinned to a 40-hex commit SHA, not a tag: {uses!r}")

    def test_checkout_then_scorecard_then_upload_sarif_order(self) -> None:
        checkout = self._index(_CHECKOUT_ACTION)
        scorecard = self._index(_SCORECARD_ACTION)
        upload = self._index(_UPLOAD_SARIF_ACTION)
        for name, idx in (("checkout", checkout), ("scorecard", scorecard), ("upload-sarif", upload)):
            self.assertGreaterEqual(idx, 0, f"could not locate the {name} step")
        self.assertLess(checkout, scorecard, "checkout must precede scorecard analysis")
        self.assertLess(scorecard, upload, "scorecard analysis must precede SARIF upload")

    # --- concurrency ----------------------------------------------------
    def test_concurrency_cancels_in_progress(self) -> None:
        concurrency = self.data.get("concurrency") or self.job.get("concurrency")
        self.assertIsNotNone(concurrency, "Scorecard workflow must define concurrency")
        self.assertTrue(concurrency.get("cancel-in-progress"),
                        "superseded Scorecard runs should be cancelled")


class ScorecardBadgeTests(unittest.TestCase):
    def test_readme_has_official_scorecard_badge(self) -> None:
        text = _README.read_text(encoding="utf-8")
        self.assertIn(
            f"https://api.scorecard.dev/projects/{_REPO_SLUG}/badge",
            text,
            "README must render the official OpenSSF Scorecard badge (#58)",
        )
        self.assertIn(
            f"https://scorecard.dev/viewer/?uri={_REPO_SLUG}",
            text,
            "Scorecard badge must link to the viewer for this repo (#58)",
        )


if __name__ == "__main__":
    unittest.main()
