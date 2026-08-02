"""End-to-end / CLI coverage for the tool modules.

These drive the command-line entry points, the GitHub client (with subprocess
mocked), the issue-template renderers, and the pack-walking gates against a pack
scaffolded from the packaged template, so the shipped tooling is exercised as a
consumer would run it — not just the pure helpers.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "raes_env_packs"


def _load(modname: str, filename: str):
    spec = importlib.util.spec_from_file_location(modname, str(PKG / filename))
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ISK = _load("isk_cov", "issue_skeleton.py")
CI = _load("ci_cov", "content_ci.py")
REL = _load("rel_cov", "release.py")

# The wizard uses package-relative imports, so it is consumed through the
# installed package rather than the file-path _load() shim.
from raes_env_packs import wizard as WIZ  # noqa: E402


def _plan():
    return ISK.PackPlan(pack_id="cov-pack", title="Cov Pack", focus="focus text",
                        sources=("upstream-x",), labels=("area:cov",),
                        milestone_number=1, milestone_title="Wave 1")


class _StubProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class IssueSkeletonRenderTests(unittest.TestCase):
    def test_helpers(self):
        self.assertEqual(ISK.title_from_pack_id("a-b-c"), "A B C")
        self.assertTrue(ISK.clean("  x  ").endswith("\n"))
        self.assertIn("- a", ISK.bullets(("a", "b")))
        self.assertIn("cov-pack", ISK.pack_block(_plan()))
        self.assertTrue(ISK.child_issue_note())
        self.assertEqual(ISK.milestone_title(_plan()), "Wave 1")

    def test_validate_pack_id_rejects_bad(self):
        with self.assertRaises(SystemExit):
            ISK.validate_pack_id("Bad_Id")

    def test_build_operations_renders_every_template(self):
        ops = ISK.build_operations(_plan(), [], available_labels={"area:cov"},
                                   milestone_exists=True)
        self.assertTrue(ops)
        self.assertTrue(all(op.title for op in ops))
        # Exercise print_operations over the full set.
        with redirect_stdout(io.StringIO()):
            ISK.print_operations(ops)

    def test_build_operations_matching_and_refresh(self):
        plan = _plan()
        ops = ISK.build_operations(plan, [], milestone_exists=True)
        existing = [{"number": i, "title": op.title, "labels": list(op.labels),
                     "milestone": {"number": 1}}
                    for i, op in enumerate(ops) if op.action == "create_issue"]
        refreshed = ISK.build_operations(plan, existing, refresh_existing=True,
                                         milestone_exists=True)
        expected = [
            ("update_issue", operation.title, index)
            for index, operation in enumerate(ops)
            if operation.action == "create_issue"
        ]
        self.assertEqual(
            [
                (operation.action, operation.title, operation.issue_number)
                for operation in refreshed
            ],
            expected,
        )

    def test_resolve_milestone_number(self):
        num, exists = ISK.resolve_milestone_number(
            _plan(), [{"title": "Wave 1", "number": 1}])
        self.assertEqual((num, exists), (1, True))

    def test_parse_and_plan_from_args(self):
        args = ISK.parse_args(["--pack-id", "cov-pack", "--milestone-title", "Wave 1",
                               "--source", "s", "--label", "l"])
        plan = ISK.plan_from_args(args)
        self.assertEqual(plan.pack_id, "cov-pack")
        with self.assertRaises(SystemExit):
            ISK.plan_from_args(ISK.parse_args([]))


class GhClientTests(unittest.TestCase):
    def setUp(self):
        self.client = ISK.GhClient("owner/repo")

    def test_run_parses_json(self):
        with mock.patch.object(ISK.subprocess, "run",
                               return_value=_StubProc(stdout='{"number": 2}')):
            self.assertEqual(ISK.GhClient.run(["api", "x"]), {"number": 2})

    def test_run_empty_returns_none(self):
        with mock.patch.object(ISK.subprocess, "run", return_value=_StubProc(stdout="")):
            self.assertIsNone(ISK.GhClient.run(["api", "x"]))

    def test_run_failure_raises(self):
        with mock.patch.object(ISK.subprocess, "run",
                               return_value=_StubProc(returncode=1, stderr="boom")):
            with self.assertRaises(SystemExit):
                ISK.GhClient.run(["api", "x"])

    def test_list_and_create(self):
        with mock.patch.object(ISK.subprocess, "run",
                               return_value=_StubProc(stdout='[{"name": "l"}]')):
            self.assertEqual(self.client.list_labels(), {"l"})
        with mock.patch.object(ISK.subprocess, "run",
                               return_value=_StubProc(stdout='[{"number": 1}]')):
            self.assertEqual(self.client.list_issues(), [{"number": 1}])
            self.assertEqual(self.client.list_milestones(), [{"number": 1}])
        with mock.patch.object(ISK.subprocess, "run",
                               return_value=_StubProc(stdout='{"number": 3}')):
            self.assertEqual(self.client.create_milestone("m"), 3)
        op = ISK.Operation(action="create_issue", title="t", body="b",
                           labels=("l",), issue_number=5)
        with mock.patch.object(ISK.subprocess, "run", return_value=_StubProc(stdout="")):
            self.client.create_issue(op, 1)
            self.client.update_issue(op, 1)

    def test_resolve_canonical_repo(self):
        with mock.patch.object(
                ISK.subprocess, "run",
                return_value=_StubProc(stdout='{"nameWithOwner": "Owner/Repo"}')):
            self.assertEqual(self.client.resolve_canonical_repo(), "Owner/Repo")

    def test_resolve_canonical_repo_missing_field_raises(self):
        with mock.patch.object(ISK.subprocess, "run",
                               return_value=_StubProc(stdout="{}")):
            with self.assertRaises(SystemExit):
                self.client.resolve_canonical_repo()


class _StubClient:
    def __init__(self, repo="example-org/example-packs"):
        self.created = []
        self.repo = repo

    def resolve_canonical_repo(self):
        return self.repo

    def list_milestones(self):
        return [{"title": "Wave 1", "number": 1}]

    def list_issues(self):
        return []

    def list_labels(self):
        return {"area:cov"}

    def create_milestone(self, title):
        return 1

    def create_issue(self, operation, milestone_number):
        self.created.append(("create", operation.title))

    def update_issue(self, operation, milestone_number):
        self.created.append(("update", operation.title))


class PrepareApplyTests(unittest.TestCase):
    def test_prepare_and_apply(self):
        args = ISK.parse_args(["--pack-id", "cov-pack", "--milestone-number", "1"])
        ops, milestone = ISK.prepare_operations(args, _StubClient())
        self.assertTrue(ops)
        client = _StubClient()
        with redirect_stdout(io.StringIO()):
            ISK.apply_operations(client, ops, milestone)
        self.assertTrue(client.created)

    def test_require_milestone_number_raises(self):
        with self.assertRaises(SystemExit):
            ISK.require_milestone_number(None, "create")

    def test_main_dry_run_and_apply(self):
        client = _StubClient()
        base = ["--pack-id", "cov-pack", "--milestone-number", "1",
                "--repo", "some-org/community-packs"]
        with mock.patch.object(ISK, "GhClient", return_value=client):
            with redirect_stdout(io.StringIO()):
                ISK.main(base)
            self.assertEqual(client.created, [])
            with redirect_stdout(io.StringIO()):
                ISK.main(base + ["--apply"])
        self.assertEqual(len(client.created), len(ISK.ISSUE_TEMPLATES))
        self.assertTrue(
            all(action == "create" for action, _title in client.created),
            client.created,
        )


def _scaffold(tmp: str) -> str:
    """Scaffold a pack with the wizard into tmp/environments and return it.

    Uses the ``product-integration`` route so the pack ships the compatibility
    manifest the release gate needs, mirroring what the old whole-template
    scaffold produced. The wizard's own behaviour is covered in test_wizard.py.
    """
    environments = os.path.join(tmp, "environments")
    os.makedirs(environments, exist_ok=True)
    inputs = WIZ.normalize_inputs({
        "version": WIZ.WIZARD_INPUT_VERSION,
        "pack_id": "cov-pack",
        "route": "product-integration",
        "answers": {"title": "Cov Pack", "description": "one line"},
    })
    proposal = WIZ.build_proposal(inputs)
    return WIZ.write_proposal(proposal, environments)


def _add_pack_gates(pack: str) -> None:
    """Add a validator (pass + fail) and a passing test suite to a scaffolded pack."""
    provenance = Path(pack) / "docs" / "provenance-ledger.yaml"
    provenance.write_text(
        provenance.read_text(encoding="utf-8").replace("<name>", "cov-pack"),
        encoding="utf-8",
    )
    sdl = os.path.join(pack, "sdl")
    os.makedirs(os.path.join(sdl, "tests"), exist_ok=True)
    with open(os.path.join(sdl, "example.sdl.yaml"), "w", encoding="utf-8") as fh:
        fh.write("name: cov-pack\nnodes:\n  target:\n    type: vm\n")
    with open(os.path.join(sdl, "validate_ok.py"), "w", encoding="utf-8") as fh:
        fh.write("import sys\nif __name__ == '__main__':\n    sys.exit(0)\n")
    with open(os.path.join(sdl, "validate_bad.py"), "w", encoding="utf-8") as fh:
        fh.write("import sys\nif __name__ == '__main__':\n    sys.exit(1)\n")
    with open(os.path.join(sdl, "tests", "test_ok.py"), "w", encoding="utf-8") as fh:
        fh.write("import unittest\n\n\nclass T(unittest.TestCase):\n"
                 "    def test_ok(self):\n        self.assertTrue(True)\n")


class ContentCiWalkTests(unittest.TestCase):
    def test_full_walk_over_scaffolded_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = _scaffold(tmp)
            _add_pack_gates(pack)
            orig = CI.PACKS_ROOT, CI._REPO
            CI.PACKS_ROOT, CI._REPO = os.path.join(tmp, "environments"), tmp
            try:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    rc = CI.main(["--pack", pack])
                self.assertEqual(rc, 1)
                self.assertIn("validate_bad.py", stdout.getvalue())
            finally:
                CI.PACKS_ROOT, CI._REPO = orig


def _complete_scaffold(pack: str) -> None:
    """Fill in the parts a freshly scaffolded pack leaves for the author.

    The template is a starting point, not a releasable pack: it ships no SDL
    start-state document and a placeholder provenance pack name. A release now
    requires the shared author-static contract to pass first (ADR 0028), so the
    author's own fill-in step has to happen before a publication profile exists.
    """
    sdl = Path(pack) / "sdl" / "example.sdl.yaml"
    sdl.parent.mkdir(parents=True, exist_ok=True)
    sdl.write_text("name: cov-pack\nnodes:\n  target:\n    type: vm\n", encoding="utf-8")
    ledger_path = Path(pack) / "docs" / "provenance-ledger.yaml"
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    ledger["pack"] = {"name": "cov-pack"}
    ledger_path.write_text(yaml.safe_dump(ledger), encoding="utf-8")


class ReleaseTests(unittest.TestCase):
    def test_pack_flows(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            pack = _scaffold(tmp)
            _complete_scaffold(pack)
            self.assertEqual(REL.lint_pack(pack), [])
            self.assertEqual(REL.smoke_pack(pack), [])
            meta, failures = REL.build_release(pack, out)
            self.assertEqual(failures, [])
            self.assertEqual(meta["release"]["pack"]["name"], "cov-pack")
            self.assertEqual(
                REL.release_metadata(pack)["release"]["pack"]["name"],
                "cov-pack",
            )
            version, digest = REL.load_contract_version()
            self.assertEqual(version, "7")
            self.assertRegex(digest, r"\Asha256:[0-9a-f]{64}\Z")

    def test_main_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = _scaffold(tmp)
            with redirect_stdout(io.StringIO()):
                rc = REL.main(["metadata", "--pack", pack])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
