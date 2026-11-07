"""Exercise the CI prose shell commands against real Git path selection."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_STEPS = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text())["jobs"]["docs"]["steps"]
_SCRIPTS = {step["name"]: step["run"] for step in _STEPS if "run" in step}


class DocumentationToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        fake = self.bin / "mise"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "with open(os.environ['PROSE_LOG'], 'a') as out:\n"
            "    out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "key = 'PROSE_' + sys.argv[3].upper() + '_STATUS'\n"
            "sys.exit(int(os.environ.get(key, os.environ.get('PROSE_STATUS', '0'))))\n"
        )
        fake.chmod(0o755)
        self.git("init", "-q")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "initial", "--allow-empty")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        RUNNER_TEMP=str(self.root), BASE=self.base,
                        PROSE_LOG=str(self.root / "calls.jsonl"))

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True,
                              text=True, capture_output=True)

    def commit(self, paths):
        for name in paths:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Read the guide.\n")
        self.git("add", "--", *paths)
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "content")

    def run_step(self, name, status=0, **codes):
        return subprocess.run(["bash", "-c", _SCRIPTS[name]], cwd=self.root,
                              env=dict(self.env, PROSE_STATUS=str(status), **codes),
                              text=True, capture_output=True)

    def calls(self):
        log = self.root / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def test_changed_paths_include_hidden_assets_spaces_and_flag_names(self):
        wanted = ["docs/public/page.md", ".gc/notes.md", "packs/demo/assets/read me.md",
                  "--analyzer=unexpected.md"]
        omitted = ["CHANGELOG.md", "CODE_OF_CONDUCT.md", "tests/fixtures/evidence.md", "code.py"]
        self.commit(wanted + omitted)
        result = self.run_step("Check changed Markdown prose")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls()), 2)
        for args in self.calls():
            # Paths must follow an option terminator and remain individual argv entries.
            self.assertEqual(set(args[args.index("--", 3) + 1:]), set(wanted))
        self.assertIn("0", self.calls()[1])
        self.assertIn("--no-baseline", self.calls()[1])

    def test_empty_and_deleted_changes_do_not_invoke_tools(self):
        self.assertEqual(self.run_step("Check changed Markdown prose").returncode, 0)
        self.commit(["removed.md"])
        self.env["BASE"] = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("rm", "removed.md")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "remove")
        self.assertEqual(self.run_step("Check changed Markdown prose").returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_changed_gate_propagates_findings_and_errors(self):
        self.commit(["page.md"])
        for status in (1, 2):
            with self.subTest(status=status):
                self.assertEqual(self.run_step("Check changed Markdown prose", status).returncode, status)

    def test_corpus_reports_findings_but_rejects_tool_errors(self):
        self.commit([".gc/notes.md", "packs/demo/assets/read me.md", "CHANGELOG.md"])
        # Vale findings are advisory, but configuration and execution errors fail.
        self.assertEqual(self.run_step("Report the full Markdown corpus", 2).returncode, 2)
        self.assertEqual(len(self.calls()), 1)
        (self.root / "calls.jsonl").unlink()
        self.assertEqual(self.run_step("Report the full Markdown corpus").returncode, 0)
        self.assertEqual(len(self.calls()), 2)
        self.assertIn("-1", self.calls()[1])
        self.assertEqual(self.run_step("Report the full Markdown corpus", PROSE_VALE_STATUS="1").returncode, 0)
        for args in self.calls():
            self.assertEqual(set(args[args.index("--", 3) + 1:]),
                             {".gc/notes.md", "packs/demo/assets/read me.md"})

    def test_first_push_checks_all_paths(self):
        self.commit(["page.md"])
        self.env["BASE"] = "0" * 40
        self.assertEqual(self.run_step("Check changed Markdown prose").returncode, 0)
        self.assertEqual(self.calls()[0][-1], "page.md")
