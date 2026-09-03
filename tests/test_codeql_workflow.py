"""Static workflow-contract guard for the CodeQL analysis workflow.

Issue #57 adds a GitHub-native CodeQL (Python) SAST workflow that runs on pull
requests into ``dev``/``main`` and on a weekly schedule, uploading results to
the Security tab. The live Security-tab upload can only be observed on a real
run, but the workflow *shape* that produces it is guarded here so a dropped
trigger, a broadened token permission, an unpinned action, or a reordered
init/analyze pair fails CI.

Scope is deliberately narrow — the CodeQL workflow's structural contract only.
It reuses the repo's existing unittest + PyYAML stack rather than adding a new
validation framework (mirrors tests/test_release_workflow_attestation.py).
"""

from __future__ import annotations

import pathlib
import re
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "codeql.yml"
_CONFIG = _ROOT / ".github" / "codeql" / "codeql-config.yml"

_CHECKOUT_ACTION = "actions/checkout@"
_INIT_ACTION = "github/codeql-action/init@"
_ANALYZE_ACTION = "github/codeql-action/analyze@"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _load() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _on_block(data: dict) -> dict:
    # PyYAML parses a bare ``on:`` key as the YAML 1.1 boolean ``True``, so the
    # triggers live under the ``True`` key, not ``"on"`` (see
    # tests/test_release_workflow_tag_signing.py).
    return data.get("on", data.get(True))


def _analyze_job(data: dict) -> dict:
    # Find the job that runs CodeQL rather than hard-coding its name.
    for job in data["jobs"].values():
        steps = job.get("steps", [])
        if any(str(s.get("uses", "")).startswith(_ANALYZE_ACTION) for s in steps):
            return job
    raise AssertionError("no job runs github/codeql-action/analyze")


class CodeqlWorkflowContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load()
        self.on = _on_block(self.data)
        self.job = _analyze_job(self.data)
        self.steps = self.job["steps"]

    def _uses(self) -> list[str]:
        return [str(s.get("uses", "")) for s in self.steps]

    def _index(self, prefix: str) -> int:
        for index, step in enumerate(self.steps):
            if str(step.get("uses", "")).startswith(prefix):
                return index
        return -1

    # --- triggers -------------------------------------------------------
    def test_pull_request_targets_dev_and_main(self) -> None:
        branches = self.on["pull_request"]["branches"]
        self.assertIn("main", branches, "CodeQL must run on PRs into main (#57)")
        self.assertIn("dev", branches, "CodeQL must run on PRs into dev (#57)")

    def test_has_weekly_schedule(self) -> None:
        schedule = self.on.get("schedule")
        self.assertTrue(schedule, "CodeQL must run on a weekly schedule (#57)")
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

    def test_trigger_surface_is_pr_and_schedule_only(self) -> None:
        # No push (redundant with PR + schedule) and never pull_request_target,
        # which is unsafe when checking out untrusted PR code.
        self.assertEqual(set(self.on), {"pull_request", "schedule"})

    # --- permissions ----------------------------------------------------
    def test_least_privilege_permissions(self) -> None:
        # #142 moved the single write scope off the top level and onto the job
        # that uses it: Scorecard's Token-Permissions check penalizes a top-level
        # write but not a job-level one sitting under a read-only top level.
        # The generic "top level is read-only / actions are SHA-pinned" rules are
        # asserted repo-wide in tests/test_workflow_permissions.py; what is
        # CodeQL-specific -- and therefore checked here -- is that `analyze` holds
        # exactly the SARIF-upload scope and nothing more.
        self.assertEqual(self.data.get("permissions"), "read-all",
                         "CodeQL workflow token must be read-only at the top level")
        perms = self.job.get("permissions")
        self.assertIsNotNone(perms, "the analyze job must set explicit permissions")
        self.assertEqual(perms.get("security-events"), "write",
                         "analyze needs security-events: write to upload SARIF")
        # A job-level block replaces the top-level one, so the read scope the
        # checkout needs has to be restated on the job.
        self.assertEqual(perms.get("contents"), "read")
        self.assertEqual(set(perms), {"contents", "security-events"},
                         f"permissions must stay least-privilege: {perms!r}")

    # --- analysis matrix ------------------------------------------------
    def test_python_build_mode_none_matrix(self) -> None:
        include = self.job["strategy"]["matrix"]["include"]
        entry = next((e for e in include if e.get("language") == "python"), None)
        self.assertIsNotNone(entry, "matrix must analyze the python language")
        self.assertEqual(entry.get("build-mode"), "none")

    def test_codeql_scans_the_complete_repository(self) -> None:
        init_step = next(
            step
            for step in self.steps
            if str(step.get("uses", "")).startswith(_INIT_ACTION)
        )
        self.assertEqual(
            init_step["with"]["config-file"],
            "./.github/codeql/codeql-config.yml",
        )
        config = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
        self.assertNotIn(
            "paths-ignore",
            config,
            "TechVault is a scenario pack, not a runtime layer to exclude from SAST",
        )

    # --- actions: pinned + ordered --------------------------------------
    def test_codeql_actions_present_and_sha_pinned(self) -> None:
        for prefix in (_CHECKOUT_ACTION, _INIT_ACTION, _ANALYZE_ACTION):
            uses = next((u for u in self._uses() if u.startswith(prefix)), None)
            self.assertIsNotNone(uses, f"missing step using {prefix}")
            ref = uses.split("@", 1)[1].split()[0]
            self.assertRegex(ref, _SHA_RE,
                             f"{prefix} must be pinned to a 40-hex commit SHA, not a tag: {uses!r}")

    def test_checkout_then_init_then_analyze_order(self) -> None:
        checkout = self._index(_CHECKOUT_ACTION)
        init = self._index(_INIT_ACTION)
        analyze = self._index(_ANALYZE_ACTION)
        for name, idx in (("checkout", checkout), ("init", init), ("analyze", analyze)):
            self.assertGreaterEqual(idx, 0, f"could not locate the {name} step")
        self.assertLess(checkout, init, "checkout must precede CodeQL init")
        self.assertLess(init, analyze, "CodeQL init must precede analyze")

    # --- concurrency ----------------------------------------------------
    def test_concurrency_cancels_in_progress(self) -> None:
        concurrency = self.data.get("concurrency") or self.job.get("concurrency")
        self.assertIsNotNone(concurrency, "CodeQL workflow must define concurrency")
        self.assertTrue(concurrency.get("cancel-in-progress"),
                        "superseded CodeQL runs should be cancelled")


if __name__ == "__main__":
    unittest.main()
