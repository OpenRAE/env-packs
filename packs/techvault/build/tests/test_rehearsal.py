import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = PACK_ROOT / "build"
REHEARSAL_PATH = BUILD_ROOT / "rehearsal.py"


def _load_rehearsal():
    spec = importlib.util.spec_from_file_location("techvault_rehearsal", REHEARSAL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeStore:
    def __init__(self, root):
        self.root = Path(root)
        self.writes = []

    def create_run(self, run_id):
        self.get_run_path(run_id).mkdir(parents=True, exist_ok=True)
        return self.get_run_path(run_id)

    def get_run_path(self, run_id):
        return self.root / run_id

    def write_json(self, run_id, relative_path, obj):
        self.writes.append((run_id, relative_path, obj))
        target = self.get_run_path(run_id) / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}", encoding="utf-8")


class FakeRunner:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def run(self, args, *, cwd, env=None, input_text=None, timeout=None):
        self.calls.append(
            {
                "args": list(args),
                "cwd": cwd,
                "env": dict(env or {}),
                "input_text": input_text,
                "timeout": timeout,
            }
        )
        key = self._key(args)
        response = self.responses.get(key, (0, "", ""))
        return subprocess.CompletedProcess(args, response[0], response[1], response[2])

    @staticmethod
    def _key(args):
        if args[:1] == ["bash"]:
            return Path(args[1]).name
        if args[:2] == ["ssh", "-i"]:
            return "ssh"
        if args[:2] == ["docker", "compose"] and args[-3:] == ["port", "kali-ssh-proxy", "2023"]:
            return "compose_port"
        if args[:3] == ["docker", "ps", "-a"]:
            return "docker_ps"
        if args[:3] == ["docker", "network", "ls"]:
            return "docker_network_ls"
        if args[:3] == ["docker", "volume", "ls"] and "--filter" in args:
            return "docker_volume_ls_labeled"
        if args[:3] == ["docker", "volume", "ls"]:
            return "docker_volume_ls_all"
        return tuple(args)


class TechVaultRehearsalTest(unittest.TestCase):
    def setUp(self):
        self.rehearsal = _load_rehearsal()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.report = Path(self.tmp.name) / "report.md"
        self.store = FakeStore(Path(self.tmp.name) / "runs")
        self.old_run_store = self.rehearsal._run_store
        self.rehearsal._run_store = lambda: self.store
        self.addCleanup(self._restore_run_store)

    def _restore_run_store(self):
        self.rehearsal._run_store = self.old_run_store

    def _options(self, *, isolated=True, run_id="tv392-test-run", marker="tv392-test-marker"):
        return self.rehearsal.RehearsalOptions(
            run_id=run_id,
            project="techvault_golden",
            env_file=BUILD_ROOT / "operator-defaults.env",
            report_path=self.report,
            isolated_docker_host=isolated,
            telemetry_window_seconds=10,
            marker=marker,
        )

    def _successful_responses(self):
        initial = "".join(f"REHEARSAL_CHECK {name} ok\n" for name in self.rehearsal.INITIAL_PARTICIPANT_CHECKS)
        telemetry = "".join(f"REHEARSAL_CHECK {name} ok\n" for name in self.rehearsal.NEGATIVE_TELEMETRY_CHECKS)
        reset = "".join(f"REHEARSAL_CHECK {name} ok\n" for name in self.rehearsal.RESET_PARTICIPANT_CHECKS)
        return {
            "launch.sh": (0, "", ""),
            "health-check.sh": (0, "", ""),
            "compose_port": (0, "127.0.0.1:2023\n", ""),
            "ssh": (0, initial, ""),
            "reset.sh": (0, "", ""),
            "cleanup.sh": (0, "", ""),
            "docker_ps": (0, "", ""),
            "docker_network_ls": (0, "", ""),
            "docker_volume_ls_labeled": (0, "", ""),
            "docker_volume_ls_all": (0, "", ""),
        }, telemetry, reset

    def test_missing_isolated_host_attestation_blocks_before_docker(self):
        runner = FakeRunner()

        report = self.rehearsal.run_rehearsal(self._options(isolated=False), runner)

        self.assertFalse(report.passed)
        self.assertEqual("LiveGateReport", type(report).__name__)
        self.assertTrue(type(report).__module__.endswith("techvault_live_gate"))
        self.assertEqual([], runner.calls)
        self.assertIn("Status: `BLOCKED`", self.report.read_text(encoding="utf-8"))

    def test_report_path_must_stay_under_docs_and_not_be_symlink(self):
        tmp_root = Path(self.tmp.name) / "pack"
        docs_root = tmp_root / "docs"
        docs_root.mkdir(parents=True)
        old_pack_root = self.rehearsal.PACK_ROOT
        self.rehearsal.PACK_ROOT = tmp_root
        self.addCleanup(lambda: setattr(self.rehearsal, "PACK_ROOT", old_pack_root))

        valid = self.rehearsal._resolve_report_path("docs/report.md")
        self.assertEqual(docs_root / "report.md", valid)

        outside = Path(self.tmp.name) / "outside.md"
        outside.parent.mkdir(exist_ok=True)
        with self.assertRaises(ValueError):
            self.rehearsal._resolve_report_path(outside)

        target = docs_root / "target.md"
        target.write_text("existing target\n", encoding="utf-8")
        existing_symlink = docs_root / "existing-link.md"
        existing_symlink.symlink_to(target)
        with self.assertRaises(ValueError):
            self.rehearsal._resolve_report_path(existing_symlink)

        dangling_symlink = docs_root / "dangling-link.md"
        dangling_symlink.symlink_to(Path(self.tmp.name) / "missing-target.md")
        with self.assertRaises(ValueError):
            self.rehearsal._resolve_report_path(dangling_symlink)

    def test_participant_actions_use_ssh_stdin_not_operator_argv(self):
        responses, telemetry_stdout, reset_stdout = self._successful_responses()
        call_count = {"ssh": 0}

        class Runner(FakeRunner):
            def run(inner_self, args, **kwargs):
                if inner_self._key(args) == "ssh":
                    call_count["ssh"] += 1
                    if call_count["ssh"] == 2:
                        inner_self.responses["ssh"] = (0, telemetry_stdout, "")
                    if call_count["ssh"] == 3:
                        inner_self.responses["ssh"] = (0, reset_stdout, "")
                return super().run(args, **kwargs)

        runner = Runner(responses)
        old_collect = self.rehearsal._collect_telemetry
        self.rehearsal._collect_telemetry = lambda ctx, _start: self.rehearsal._record_check(ctx, "telemetry_evidence_path", True)
        self.addCleanup(lambda: setattr(self.rehearsal, "_collect_telemetry", old_collect))

        report = self.rehearsal.run_rehearsal(self._options(marker="tv392-boundary-marker"), runner)

        self.assertTrue(report.passed)
        ssh_calls = [call for call in runner.calls if call["args"][0] == "ssh"]
        self.assertEqual(3, len(ssh_calls))
        for call in ssh_calls:
            self.assertNotIn("tv392-boundary-marker", " ".join(call["args"]))
            self.assertEqual("tv392-test-run", call["env"]["APTL_RUN_ID"])
        self.assertIn("tv392-boundary-marker", ssh_calls[0]["input_text"])
        self.assertIsNone(ssh_calls[1]["input_text"])
        self.assertIn("telemetry_negative_ssh_generated", " ".join(ssh_calls[1]["args"]))
        self.assertIn("tv392-boundary-marker", ssh_calls[2]["input_text"])

    def test_initial_participant_script_keeps_stdin_after_smbclient(self):
        script = self.rehearsal._initial_participant_script("tv392-script-marker")
        self.assertIn('smbclient //172.20.2.12/Public -N -c "get welcome.txt $TMP.public.txt" </dev/null', script)
        self.assertIn('smbclient //172.20.2.12/Shared -N -c "ls ${MARKER}.txt" </dev/null', script)
        self.assertNotIn("172.20.2.22", script)

    def test_negative_telemetry_command_uses_real_victim_ip_without_marker(self):
        command = self.rehearsal._negative_telemetry_command()
        self.assertIn('IDENTITY="aptl-live-gate-invalid-${APTL_RUN_ID:-manual}"', command)
        self.assertIn('"${IDENTITY}@172.20.2.20"', command)
        self.assertIn("nmap -Pn -T4 -p 22,80,443,445 172.20.2.20 </dev/null", command)
        self.assertIn("REHEARSAL_CHECK %s ok", command)
        self.assertNotIn("172.20.2.22", command)
        self.assertNotIn("MARKER", command)

    def test_reset_participant_script_keeps_stdin_after_smbclient(self):
        script = self.rehearsal._reset_participant_script("tv392-script-marker")
        self.assertIn('smbclient //172.20.2.12/Shared -N -c "ls" </dev/null', script)
        self.assertIn('smbclient //172.20.2.12/Public -N -c "get welcome.txt $TMP.public.txt" </dev/null', script)

    def test_cleanup_runs_when_participant_journey_fails(self):
        responses, _telemetry_stdout, _reset_stdout = self._successful_responses()
        responses["ssh"] = (20, "REHEARSAL_CHECK portal_reachable ok\n", "")
        runner = FakeRunner(responses)

        report = self.rehearsal.run_rehearsal(self._options(), runner)

        self.assertFalse(report.passed)
        called_scripts = [Path(call["args"][1]).name for call in runner.calls if call["args"][0] == "bash"]
        self.assertIn("cleanup.sh", called_scripts)
        self.assertNotIn("reset.sh", called_scripts)

    def test_cleanup_runs_when_launch_fails_after_partial_setup(self):
        responses, _telemetry_stdout, _reset_stdout = self._successful_responses()
        responses["launch.sh"] = (1, "", "")
        runner = FakeRunner(responses)

        report = self.rehearsal.run_rehearsal(self._options(), runner)

        self.assertFalse(report.passed)
        called_scripts = [Path(call["args"][1]).name for call in runner.calls if call["args"][0] == "bash"]
        self.assertIn("launch.sh", called_scripts)
        self.assertIn("cleanup.sh", called_scripts)
        failures = {check.name for check in report.failures()}
        self.assertIn("setup_launch", failures)
        self.assertNotIn("cleanup_no_residual_resources", failures)
        self.assertIn("Status: `FAIL`", self.report.read_text(encoding="utf-8"))

    def test_launch_timeout_writes_report_and_runs_cleanup(self):
        responses, _telemetry_stdout, _reset_stdout = self._successful_responses()

        class Runner(FakeRunner):
            def run(inner_self, args, **kwargs):
                inner_self.calls.append(
                    {
                        "args": list(args),
                        "cwd": kwargs["cwd"],
                        "env": dict(kwargs.get("env") or {}),
                        "input_text": kwargs.get("input_text"),
                        "timeout": kwargs.get("timeout"),
                    }
                )
                if inner_self._key(args) == "launch.sh":
                    raise subprocess.TimeoutExpired(args, kwargs.get("timeout"))
                return super().run(args, **kwargs)

        runner = Runner(responses)

        report = self.rehearsal.run_rehearsal(self._options(), runner)

        self.assertFalse(report.passed)
        failures = {check.name for check in report.failures()}
        self.assertIn("setup_launch", failures)
        self.assertTrue(self.report.exists())
        called_scripts = [Path(call["args"][1]).name for call in runner.calls if call["args"][0] == "bash"]
        self.assertIn("cleanup.sh", called_scripts)

    def test_participant_subprocess_failure_fails_even_with_complete_check_lines(self):
        responses, telemetry_stdout, reset_stdout = self._successful_responses()
        initial = "".join(f"REHEARSAL_CHECK {name} ok\n" for name in self.rehearsal.INITIAL_PARTICIPANT_CHECKS)
        responses["ssh"] = (255, initial, "")
        call_count = {"ssh": 0}

        class Runner(FakeRunner):
            def run(inner_self, args, **kwargs):
                if inner_self._key(args) == "ssh":
                    call_count["ssh"] += 1
                    if call_count["ssh"] == 2:
                        inner_self.responses["ssh"] = (0, telemetry_stdout, "")
                    if call_count["ssh"] == 3:
                        inner_self.responses["ssh"] = (0, reset_stdout, "")
                return super().run(args, **kwargs)

        runner = Runner(responses)
        old_collect = self.rehearsal._collect_telemetry
        self.rehearsal._collect_telemetry = lambda ctx, _start: self.rehearsal._record_check(ctx, "telemetry_evidence_path", True)
        self.addCleanup(lambda: setattr(self.rehearsal, "_collect_telemetry", old_collect))

        report = self.rehearsal.run_rehearsal(self._options(), runner)

        self.assertFalse(report.passed)
        initial_evidence = self.store.writes[-1][2]["evidence"]["participant"]["initial"]
        self.assertEqual(255, initial_evidence["returncode"])
        failures = {check.name for check in report.failures()}
        self.assertIn("portal_reachable", failures)

    def test_telemetry_evidence_rejects_suricata_events_without_wazuh_correlation(self):
        ctx = self.rehearsal.RehearsalContext(
            options=self._options(),
            runner=FakeRunner(),
            store=self.store,
        )
        old_collect = self.rehearsal._collect_until_evidence
        old_load_env = self.rehearsal._load_env
        self.rehearsal._collect_until_evidence = lambda *_args, **_kwargs: (
            [
                {
                    "event_type": "flow",
                    "src_ip": self.rehearsal.KALI_INTERNAL_IP,
                    "dest_ip": self.rehearsal.VICTIM_IP,
                    "dest_port": 22,
                }
            ],
            [],
        )
        self.rehearsal._load_env = lambda _path: {
            "INDEXER_USERNAME": "admin",
            "INDEXER_PASSWORD": "TechVaultIndexerPass2026!",
        }
        self.addCleanup(lambda: setattr(self.rehearsal, "_collect_until_evidence", old_collect))
        self.addCleanup(lambda: setattr(self.rehearsal, "_load_env", old_load_env))

        self.rehearsal._collect_telemetry(ctx, "2026-07-21T00:00:00+00:00")

        checks = {check.name: check.passed for check in ctx.checks}
        self.assertFalse(checks["telemetry_evidence_path"])
        self.assertEqual({"flow": 1}, ctx.evidence["telemetry"]["suricata_correlated_event_types"])
        self.assertEqual(1, ctx.evidence["telemetry"]["suricata_correlated_event_count"])
        self.assertEqual(0, ctx.evidence["telemetry"]["wazuh_correlated_alert_count"])

    def test_telemetry_evidence_rejects_ambient_suricata_events(self):
        ctx = self.rehearsal.RehearsalContext(
            options=self._options(),
            runner=FakeRunner(),
            store=self.store,
        )
        old_collect = self.rehearsal._collect_until_evidence
        old_load_env = self.rehearsal._load_env
        self.rehearsal._collect_until_evidence = lambda *_args, **_kwargs: (
            [
                {
                    "event_type": "flow",
                    "src_ip": "172.20.1.20",
                    "dest_ip": self.rehearsal.VICTIM_IP,
                    "dest_port": 22,
                }
            ],
            [{"rule": {"description": "ambient unrelated alert"}}],
        )
        self.rehearsal._load_env = lambda _path: {
            "INDEXER_USERNAME": "admin",
            "INDEXER_PASSWORD": "TechVaultIndexerPass2026!",
        }
        self.addCleanup(lambda: setattr(self.rehearsal, "_collect_until_evidence", old_collect))
        self.addCleanup(lambda: setattr(self.rehearsal, "_load_env", old_load_env))

        self.rehearsal._collect_telemetry(ctx, "2026-07-21T00:00:00+00:00")

        checks = {check.name: check.passed for check in ctx.checks}
        self.assertFalse(checks["telemetry_evidence_path"])
        self.assertEqual(0, ctx.evidence["telemetry"]["suricata_correlated_event_count"])
        self.assertEqual(0, ctx.evidence["telemetry"]["wazuh_correlated_alert_count"])

    def test_telemetry_evidence_passes_with_run_specific_wazuh_manager_alert(self):
        ctx = self.rehearsal.RehearsalContext(
            options=self._options(run_id="tv392-auth-log-run"),
            runner=FakeRunner(
                {
                    (
                        "docker",
                        "exec",
                        "aptl-wazuh-manager",
                        "sh",
                        "-lc",
                        "grep -h -F -- aptl-live-gate-invalid-tv392-auth-log-run "
                        "/var/ossec/logs/alerts/alerts.json /var/ossec/logs/alerts/alerts.log "
                        "2>/dev/null | tail -n 20",
                    ): (
                        0,
                        '{"rule":{"id":"5710"},"full_log":"Invalid user '
                        "aptl-live-gate-invalid-tv392-auth-log-run from 172.20.2.35\n",
                        "",
                    )
                }
            ),
            store=self.store,
        )
        old_collect = self.rehearsal._collect_until_evidence
        old_load_env = self.rehearsal._load_env
        self.rehearsal._collect_until_evidence = lambda *_args, **_kwargs: ([], [])
        self.rehearsal._load_env = lambda _path: {
            "INDEXER_USERNAME": "admin",
            "INDEXER_PASSWORD": "TechVaultIndexerPass2026!",
        }
        self.addCleanup(lambda: setattr(self.rehearsal, "_collect_until_evidence", old_collect))
        self.addCleanup(lambda: setattr(self.rehearsal, "_load_env", old_load_env))

        self.rehearsal._collect_telemetry(ctx, "2026-07-21T00:00:00+00:00")

        checks = {check.name: check.passed for check in ctx.checks}
        self.assertTrue(checks["telemetry_evidence_path"])
        self.assertEqual(1, ctx.evidence["telemetry"]["wazuh_manager_alert"]["match_count"])
        self.assertIn("sha256", ctx.evidence["telemetry"]["wazuh_manager_alert"])

    def test_telemetry_evidence_rejects_victim_auth_log_without_wazuh_alert(self):
        ctx = self.rehearsal.RehearsalContext(
            options=self._options(run_id="tv392-victim-only-run"),
            runner=FakeRunner(
                {
                    (
                        "docker",
                        "exec",
                        "aptl-victim",
                        "sh",
                        "-lc",
                        "grep -h -F -- aptl-live-gate-invalid-tv392-victim-only-run "
                        "/var/log/secure /var/log/auth.log 2>/dev/null | tail -n 20",
                    ): (
                        0,
                        "Jul 21 sshd[42]: Invalid user "
                        "aptl-live-gate-invalid-tv392-victim-only-run from 172.20.2.35\n",
                        "",
                    )
                }
            ),
            store=self.store,
        )
        old_collect = self.rehearsal._collect_until_evidence
        old_load_env = self.rehearsal._load_env
        self.rehearsal._collect_until_evidence = lambda *_args, **_kwargs: ([], [])
        self.rehearsal._load_env = lambda _path: {
            "INDEXER_USERNAME": "admin",
            "INDEXER_PASSWORD": "TechVaultIndexerPass2026!",
        }
        self.addCleanup(lambda: setattr(self.rehearsal, "_collect_until_evidence", old_collect))
        self.addCleanup(lambda: setattr(self.rehearsal, "_load_env", old_load_env))

        self.rehearsal._collect_telemetry(ctx, "2026-07-21T00:00:00+00:00")

        checks = {check.name: check.passed for check in ctx.checks}
        self.assertFalse(checks["telemetry_evidence_path"])
        self.assertEqual(1, ctx.evidence["telemetry"]["victim_auth_log"]["match_count"])
        self.assertEqual(0, ctx.evidence["telemetry"]["wazuh_manager_alert"]["match_count"])

    def test_cleanup_residuals_are_failures(self):
        responses, telemetry_stdout, reset_stdout = self._successful_responses()
        responses["docker_volume_ls_all"] = (0, "techvault_golden_leftover\n", "")
        call_count = {"ssh": 0}

        class Runner(FakeRunner):
            def run(inner_self, args, **kwargs):
                if inner_self._key(args) == "ssh":
                    call_count["ssh"] += 1
                    if call_count["ssh"] == 2:
                        inner_self.responses["ssh"] = (0, telemetry_stdout, "")
                    if call_count["ssh"] == 3:
                        inner_self.responses["ssh"] = (0, reset_stdout, "")
                return super().run(args, **kwargs)

        runner = Runner(responses)
        old_collect = self.rehearsal._collect_telemetry
        self.rehearsal._collect_telemetry = lambda ctx, _start: self.rehearsal._record_check(ctx, "telemetry_evidence_path", True)
        self.addCleanup(lambda: setattr(self.rehearsal, "_collect_telemetry", old_collect))

        report = self.rehearsal.run_rehearsal(self._options(), runner)

        self.assertFalse(report.passed)
        failures = {check.name for check in report.failures()}
        self.assertIn("cleanup_no_residual_resources", failures)


if __name__ == "__main__":
    unittest.main()
