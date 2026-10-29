"""Contract for the parallel CI topology in ``.github/workflows/ci.yml`` (issue #163).

ADR 0029 keeps ``verify`` as the single protected-branch status context and turns
it into a *fail-closed aggregate* of the mandatory verification jobs, run
concurrently, with SonarCloud consuming the unit-test job's same-run coverage
artifact instead of re-running the suite. Those are properties of the workflow
*graph*, not of any one command, so they are guarded here the way
``tests/test_codeql_workflow.py`` and ``tests/test_scorecard_workflow.py`` guard
their workflows.

Deliberately NOT restated here: action SHA pinning, least-privilege permissions,
no-auto-merge, and hash-locked pip shapes. Those are whole-repository invariants
owned by ``tests/test_workflow_permissions.py`` and
``tests/test_dependency_pinning.py`` (ADR 0029: the topology test does not
duplicate the generic security rules). This module owns only the topology:
aggregate membership, job independence, the Sonar coverage dependency, secret
eligibility, single-run coverage, gate completeness, and the no-shard decision.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CI = _ROOT / ".github" / "workflows" / "ci.yml"

# The job whose green status branch protection requires. Renaming it silently
# would decouple the merge gate from the work (ADR 0029).
_REQUIRED_CONTEXT = "verify"
# SonarCloud is a secret-backed check unavailable to fork/Dependabot PRs, so it
# is never part of the universally-required aggregate.
_NON_MANDATORY = {"sonar"}


def _load() -> dict:
    return yaml.safe_load(_CI.read_text(encoding="utf-8"))


def _jobs() -> dict:
    return _load().get("jobs") or {}


def _needs(job: dict) -> set[str]:
    raw = job.get("needs")
    if raw is None:
        return set()
    if isinstance(raw, str):
        return {raw}
    return set(raw)


def _steps(job: dict) -> list[dict]:
    return [s for s in (job.get("steps") or []) if isinstance(s, dict)]


def _runs(job: dict) -> str:
    """Every ``run:`` body of a job, concatenated."""
    return "\n".join(str(s["run"]) for s in _steps(job) if s.get("run"))


def _mandatory_job_names(jobs: dict) -> set[str]:
    """The jobs the required aggregate must gate: everything but itself and Sonar."""
    return set(jobs) - {_REQUIRED_CONTEXT} - _NON_MANDATORY


def _guard_step(verify: dict) -> dict:
    """The verify job's gate step: the one mapping job results into `env` and
    running the fail-closed script."""
    for step in _steps(verify):
        if step.get("run") and (step.get("env") or {}):
            return step
    raise AssertionError(
        "the verify job has no gate step carrying `needs.<job>.result` env vars "
        "and a run script"
    )


def _job_env_map(step: dict) -> dict[str, str]:
    """Map each job to the env var that carries its `needs.<job>.result`."""
    mapping: dict[str, str] = {}
    for env_key, value in (step.get("env") or {}).items():
        m = re.search(r"needs\.([A-Za-z0-9_-]+)\.result", str(value))
        if m:
            mapping[m.group(1)] = env_key
    return mapping


class AggregateGateTests(unittest.TestCase):
    """`verify` is the stable required context and a fail-closed aggregate."""

    def setUp(self) -> None:
        self.jobs = _jobs()

    def test_required_context_still_exists(self) -> None:
        self.assertIn(
            _REQUIRED_CONTEXT, self.jobs,
            "ci.yml must keep a job named `verify`; it is the required "
            "branch-protection status context (ADR 0029)",
        )

    def test_the_split_actually_happened(self) -> None:
        # Guards against the test passing vacuously on the old single-job file:
        # the mandatory work must be spread across these independent jobs.
        for name in ("compile", "tests", "audit", "content"):
            with self.subTest(job=name):
                self.assertIn(
                    name, self.jobs,
                    f"expected an independent `{name}` job after the split (ADR 0029)",
                )

    def test_verify_gates_exactly_the_mandatory_set(self) -> None:
        # The extensibility seam: a new mandatory job must be wired into the
        # aggregate, or this fails. Sonar must NOT be in it.
        verify = self.jobs[_REQUIRED_CONTEXT]
        self.assertEqual(
            _needs(verify), _mandatory_job_names(self.jobs),
            "`verify` must `needs:` every mandatory job and only those; add a new "
            "check to the aggregate when you add a new mandatory job (ADR 0029)",
        )
        self.assertNotIn(
            "sonar", _needs(verify),
            "Sonar is secret-backed and skipped for fork/Dependabot PRs; it "
            "cannot be part of the universally-required aggregate (ADR 0029)",
        )

    def test_verify_runs_even_when_a_dependency_fails(self) -> None:
        cond = str(self.jobs[_REQUIRED_CONTEXT].get("if", ""))
        self.assertIn(
            "always()", cond,
            "`verify` must use `if: always()` so a failed/cancelled dependency "
            "cannot let the gate skip straight to success (ADR 0029)",
        )

    def test_verify_env_references_every_mandatory_result(self) -> None:
        # Every mandatory job's result must be surfaced to the gate step, so none
        # can be silently dropped before the check even runs.
        step = _guard_step(self.jobs[_REQUIRED_CONTEXT])
        self.assertEqual(
            set(_job_env_map(step)), _mandatory_job_names(self.jobs),
            "the `verify` gate step must map `needs.<job>.result` for every "
            "mandatory job (ADR 0029)",
        )

    @unittest.skipUnless(shutil.which("bash"), "bash is required to exercise the gate")
    def test_verify_gate_script_blocks_on_each_mandatory_failure(self) -> None:
        # Execute the actual fail-closed loop rather than pattern-matching its
        # text. A substring/regex check for `success`/`exit 1` passes even if the
        # loop is narrowed to a subset of the results — e.g. dropping `$AUDIT`
        # while leaving its env line — which would silently stop the gate from
        # blocking that job's failure (issue #163 test-quality review). Driving
        # the real control flow with a per-job matrix catches that regression.
        step = _guard_step(self.jobs[_REQUIRED_CONTEXT])
        script = str(step["run"])
        env_of = _job_env_map(step)  # {job: ENV_VAR}
        jobs = sorted(env_of)
        self.assertTrue(jobs, "the gate step maps no job results")

        def gate_exit(result_by_job: dict[str, str]) -> int:
            child_env = {"PATH": os.environ.get("PATH", "")}
            for job, env_key in env_of.items():
                child_env[env_key] = result_by_job[job]
            return subprocess.run(
                ["bash", "-c", script],
                env=child_env, capture_output=True, text=True,
            ).returncode

        # Every mandatory job succeeded -> the gate passes.
        self.assertEqual(
            gate_exit({j: "success" for j in jobs}), 0,
            "the gate must pass when every mandatory job succeeded",
        )
        # Each mandatory job, failing on its own, must block the merge. Only
        # "success" is a pass; failed/cancelled/skipped/empty are not (ADR 0029).
        # If the loop were narrowed to skip a job, that job's row here fails.
        for failed in jobs:
            for bad in ("failure", "cancelled", "skipped", ""):
                results = {j: "success" for j in jobs}
                results[failed] = bad
                with self.subTest(job=failed, result=bad or "<empty>"):
                    self.assertNotEqual(
                        gate_exit(results), 0,
                        f"the gate must block merge when `{failed}` is "
                        f"'{bad or 'empty'}' (only 'success' is a pass, ADR 0029)",
                    )


class JobIndependenceTests(unittest.TestCase):
    """Mandatory checks run concurrently; none waits on an unrelated stage."""

    def setUp(self) -> None:
        self.jobs = _jobs()

    def test_mandatory_jobs_have_no_cross_dependencies(self) -> None:
        for name in _mandatory_job_names(self.jobs):
            with self.subTest(job=name):
                self.assertEqual(
                    _needs(self.jobs[name]), set(),
                    f"`{name}` is a mandatory check and must start immediately; it "
                    "must not `needs:` another job (issue #163)",
                )

    def test_sonar_depends_only_on_the_coverage_producer(self) -> None:
        sonar = self.jobs["sonar"]
        self.assertEqual(
            _needs(sonar), {"tests"},
            "SonarCloud must depend only on the unit-test coverage producer, not "
            "on `verify`, `audit`, or `content` (ADR 0029)",
        )


class CoverageAuthorityTests(unittest.TestCase):
    """Coverage is produced once by `tests` and handed to Sonar as an artifact."""

    def setUp(self) -> None:
        self.jobs = _jobs()

    def test_the_unit_suite_is_discovered_exactly_once(self) -> None:
        # No sharding: exactly one mandatory job runs the whole-suite discovery,
        # so every test runs exactly once per full run (AC: deterministic, once).
        discoverers = [
            name for name in _mandatory_job_names(self.jobs)
            if "unittest discover -s tests" in _runs(self.jobs[name])
        ]
        self.assertEqual(
            discoverers, ["tests"],
            "exactly one job (`tests`) must run `unittest discover -s tests`; the "
            "suite is not sharded (ADR 0029)",
        )

    def test_tests_job_is_the_coverage_authority(self) -> None:
        body = _runs(self.jobs["tests"])
        self.assertIn("coverage run", body, "`tests` must run the suite under coverage")
        self.assertIn("coverage xml", body, "`tests` must emit coverage.xml")
        uploads = "\n".join(
            str(s.get("uses", "")) for s in _steps(self.jobs["tests"])
        )
        self.assertIn(
            "actions/upload-artifact", uploads,
            "`tests` must upload the coverage artifact for Sonar to consume",
        )

    def test_sonar_consumes_the_artifact_and_does_not_rerun_the_suite(self) -> None:
        sonar = self.jobs["sonar"]
        uses = "\n".join(str(s.get("uses", "")) for s in _steps(sonar))
        self.assertIn(
            "actions/download-artifact", uses,
            "Sonar must download the same-run coverage artifact (ADR 0029)",
        )
        self.assertNotIn(
            "unittest discover", _runs(sonar),
            "Sonar must not re-run the unit suite; it consumes the artifact "
            "(ADR 0029: coverage is produced once)",
        )
        self.assertNotIn("coverage run", _runs(sonar))


class GateCompletenessTests(unittest.TestCase):
    """Splitting the job must not drop any verification the merge gate had."""

    def setUp(self) -> None:
        self.jobs = _jobs()
        self.mandatory_body = "\n".join(
            _runs(self.jobs[name]) for name in _mandatory_job_names(self.jobs)
        )

    def test_every_verification_command_survives_the_split(self) -> None:
        for needle in (
            "unittest discover -s tests",   # unit tests
            "pip-audit",                    # dependency vulnerability audit
            "raes-pack-validate",           # environment-pack-content gate
            "raes-pack-release",            # pack-release gate
            "check --all",
            "compileall src tests",         # static/compile early feedback
        ):
            with self.subTest(command=needle):
                self.assertIn(
                    needle, self.mandatory_body,
                    f"the mandatory jobs must still run `{needle}`; the parallel "
                    "split may not narrow required verification (AC #1, ADR 0029)",
                )

    def test_pip_audit_population_is_not_narrowed(self) -> None:
        # The audit must see the same installed population it saw inside `verify`:
        # runtime + build + the audit tool. Installing fewer locks would silently
        # shrink what pip-audit inspects (ADR 0029).
        audit_body = _runs(self.jobs["audit"])
        for lock in ("requirements/runtime.txt", "requirements/build.txt",
                     "requirements/pip-audit.txt"):
            with self.subTest(lock=lock):
                self.assertIn(
                    lock, audit_body,
                    f"the `audit` job must install {lock} so pip-audit's audited "
                    "population is not narrowed when split out of `verify`",
                )


class SecretEligibilityTests(unittest.TestCase):
    """SONAR_TOKEN handling and fork/Dependabot skip are preserved."""

    def setUp(self) -> None:
        self.jobs = _jobs()

    def test_sonar_still_skips_fork_and_dependabot_prs(self) -> None:
        cond = str(self.jobs["sonar"].get("if", "")).lower()
        self.assertIn("dependabot", cond)
        self.assertIn("github.repository", cond)
        self.assertIn("pull_request", cond)

    def test_sonar_token_is_passed_by_environment_not_argv(self) -> None:
        # The token must reach the scanner through step `env:`, never a shell
        # command line where it could land in process argv or logs.
        env_carries_token = any(
            "SONAR_TOKEN" in (step.get("env") or {})
            for step in _steps(self.jobs["sonar"])
        )
        self.assertTrue(
            env_carries_token,
            "SONAR_TOKEN must be provided via a step `env:` mapping (ADR 0029)",
        )
        for name, job in self.jobs.items():
            with self.subTest(job=name):
                self.assertNotIn(
                    "SONAR_TOKEN", _runs(job),
                    f"{name} must not reference SONAR_TOKEN in a run script; keep "
                    "it out of argv and logs (ADR 0029)",
                )


class CachingTests(unittest.TestCase):
    """Dependency caching is reproducible: keyed on the hash-locked requirements."""

    def setUp(self) -> None:
        self.jobs = _jobs()

    def test_installing_jobs_cache_pip_keyed_on_locks(self) -> None:
        for name in ("tests", "audit", "content"):
            job = self.jobs[name]
            setups = [
                s for s in _steps(job)
                if "actions/setup-python" in str(s.get("uses", ""))
            ]
            with self.subTest(job=name):
                self.assertTrue(setups, f"`{name}` must set up Python")
                with_block = setups[0].get("with") or {}
                self.assertEqual(
                    str(with_block.get("cache")), "pip",
                    f"`{name}` must enable pip caching to cut repeated setup time",
                )
                dep_path = str(with_block.get("cache-dependency-path", ""))
                self.assertIn(
                    "requirements", dep_path,
                    f"`{name}` must key the cache on the hash-locked "
                    "requirements/*.txt so restores stay reproducible (ADR 0029)",
                )


if __name__ == "__main__":
    unittest.main()
