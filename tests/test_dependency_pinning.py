"""Contract for hash-locked CI dependencies and pinned workflow pip commands.

Issue #142 closes the OpenSSF Scorecard ``Pinned-Dependencies`` finding, which
flagged five ``pip install`` invocations across ``ci.yml`` and
``release-please.yml``. Version pins like ``pip-audit==2.10.1`` are *not* enough:
Scorecard wants a hash, because a version alone still trusts whatever artifact
the index serves for that version.

Three invariants are asserted here.

1. Every ``pip install`` in every workflow is in one of the shapes Scorecard
   accepts as pinned. ``_is_unpinned_pip_install`` below reimplements
   ``isUnpinnedPipInstall`` from Scorecard's ``checks/raw/shell_download_validate.go``
   so a reviewer can see the rule being enforced rather than trusting a remote
   scoring run that only happens post-merge on the default branch.
2. The ``requirements/*.txt`` locks are internally coherent: fully hashed,
   exactly pinned, agreeing with each other on any shared transitive package, and
   consistent with ``pyproject.toml``.
3. Static analysis and package syntax retain the declared Python compatibility
   floor, rather than assuming only the newer CI interpreter is supported.

On invariant 2's last point -- the locks are CI *toolchain* pins. They are not a
restatement of what the distributed package requires. ``pyproject.toml`` keeps
``PyYAML>=6`` as a compatibility floor for downstream consumers; a lock that
pinned the package's own metadata to one version would break that. So the test
asserts the lock **satisfies** pyproject's constraints, never that it equals
them.
"""

from __future__ import annotations

import ast
import pathlib
import re
import shlex
import tomllib
import unittest

import yaml
from packaging.requirements import Requirement
from packaging.version import Version

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW_DIR = _ROOT / ".github" / "workflows"
_REQ_DIR = _ROOT / "requirements"
_PYPROJECT = _ROOT / "pyproject.toml"

_PIN_RE = re.compile(r"^(?P<name>[A-Za-z0-9._-]+)==(?P<version>[^\s\\]+)")
_REMOTE_VCS_RE = re.compile(r"^(git|svn|hg|bzr)")
_FLAG_RE = re.compile(r"^(--?\w+)+$")


# --- Scorecard's pip rule, reimplemented -------------------------------------

def _is_flag(token: str) -> bool:
    return bool(_FLAG_RE.match(token))


def _is_pinned_editable_source(source: str) -> bool:
    # Local paths are pinned; a remote VCS source must carry a 40-hex commit.
    if not _REMOTE_VCS_RE.match(source):
        return True
    return bool(re.match(r"^git(\+(https?|ssh|git))?://.*@[a-fA-F0-9]{40}(#egg=.*)?$", source))


def _is_unpinned_pip_install(args: list[str]) -> bool:
    """Mirror of Scorecard's ``isUnpinnedPipInstall``. ``args`` excludes 'install'."""
    has_no_deps = False
    is_editable = False
    editable_pinned = True
    has_require_hashes = False
    has_additional_args = False
    has_wheel = False

    for token in args:
        if token.lower() == "--no-deps":
            has_no_deps = True
            continue
        if token in ("-e", "--editable"):
            is_editable = True
            continue
        if token.lower() == "--require-hashes":
            has_require_hashes = True
            break
        if _is_flag(token):
            continue
        if token.endswith(".whl"):
            has_wheel = True
            continue
        if is_editable:
            if not _is_pinned_editable_source(token):
                editable_pinned = False
            continue
        has_additional_args = True

    if is_editable:
        return not has_no_deps or not editable_pinned
    if has_require_hashes:
        return False
    if has_additional_args:
        return True
    if has_wheel:
        return False
    return True


def _join_continuations(script: str) -> list[str]:
    """Fold backslash-continued shell lines into single logical lines.

    Without this, a wrapped `pip install --require-hashes \\` + `-r lock.txt`
    is read as two fragments: the checker would see an argument-less install and
    wave it through, and the co-installation grouping would miss the lock
    entirely. That is a silent false pass, so it is handled up front.
    """
    logical: list[str] = []
    buffer = ""
    for raw in script.splitlines():
        stripped = raw.strip()
        if stripped.endswith("\\"):
            buffer += stripped[:-1].rstrip() + " "
            continue
        logical.append((buffer + stripped).strip())
        buffer = ""
    if buffer.strip():
        logical.append(buffer.strip())
    return logical


def _pip_installs(script: str) -> list[list[str]]:
    """Yield the argument list of every `pip install` in a shell script."""
    found: list[list[str]] = []
    for line in _join_continuations(script):
        if not line or line.startswith("#") or "pip" not in line:
            continue
        # `dist/*.whl` is a glob, not valid shlex input on its own, but it
        # tokenizes fine; only genuinely unparseable lines are skipped.
        try:
            tokens = shlex.split(line, comments=True)
        except ValueError:
            continue
        for i, tok in enumerate(tokens):
            base = tok.rsplit("/", 1)[-1]
            if base in ("pip", "pip3") and tokens[i + 1: i + 2] == ["install"]:
                found.append(tokens[i + 2:])
                break
    return found


def _workflow_scripts() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for path in sorted(_WORKFLOW_DIR.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job_name, job in (data.get("jobs") or {}).items():
            for step in (job.get("steps") or []):
                if isinstance(step, dict) and step.get("run"):
                    out.append((path.name, job_name, str(step["run"])))
    return out


# --- lock-file helpers -------------------------------------------------------

def _locks_per_job() -> dict[tuple[str, str], set[str]]:
    """Map each workflow job to the repo-relative locks its steps install.

    One job is one Python environment, so this is the set that has to agree.
    """
    grouped: dict[tuple[str, str], set[str]] = {}
    for workflow, job, script in _workflow_scripts():
        for args in _pip_installs(script):
            for i, tok in enumerate(args):
                if tok in ("-r", "--requirement") and i + 1 < len(args):
                    grouped.setdefault((workflow, job), set()).add(args[i + 1])
    return grouped


def _lock_files() -> list[pathlib.Path]:
    files = sorted(_REQ_DIR.glob("*.txt"))
    if not files:
        raise AssertionError(f"no lock files found in {_REQ_DIR}")
    return files


def _parse_lock(path: pathlib.Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _PIN_RE.match(stripped)
        if match:
            pins[match.group("name").lower().replace("_", "-")] = match.group("version")
    return pins


class PythonAnalysisCompatibilityTests(unittest.TestCase):
    def test_analysis_and_source_syntax_include_the_declared_python_floor(self) -> None:
        project = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]
        declared = re.fullmatch(r">=(\d+)\.(\d+)", project["requires-python"])
        self.assertIsNotNone(declared, "update the floor check when the supported range changes")
        floor = tuple(map(int, declared.groups()))
        properties = (_ROOT / "sonar-project.properties").read_text(encoding="utf-8")
        configured = re.search(r"^sonar\.python\.version=(.+)$", properties, re.MULTILINE)
        self.assertIsNotNone(configured)
        versions = [tuple(map(int, item.strip().split("."))) for item in configured[1].split(",")]
        self.assertIn(floor, versions, "analysis must not recommend syntax unavailable to supported users")
        for path in sorted((_ROOT / "src" / "raes_env_packs").rglob("*.py")):
            with self.subTest(source=path.relative_to(_ROOT).as_posix()):
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=floor)


class PipPinningRuleTests(unittest.TestCase):
    """Exercise the rule itself against crafted input, not just today's repo.

    The checks below run the reimplemented Scorecard rule over a table of
    commands that are known-pinned and known-unpinned. Without this, every
    assertion in this module would still pass if `_is_unpinned_pip_install` were
    replaced by `return False` -- the helper would be asserting nothing, and the
    workflow tests would be green by construction.

    That is not hypothetical: `_join_continuations` was added because the
    line-by-line reader silently truncated a wrapped `pip install ... \\` and
    waved through a command it had never actually seen.
    """

    PINNED = [
        (["--require-hashes", "-r", "requirements/runtime.txt"], "hash-locked file"),
        (["--require-hashes", "-r", "a.txt", "-r", "b.txt"], "two hash-locked files"),
        (["--no-deps", "-e", "."], "editable local install with --no-deps"),
        (["--no-deps", "--no-build-isolation", "-e", "."], "plus isolation disabled"),
        (["dist/foo.whl"], "a wheel on its own"),
        (["--no-deps", "dist/foo.whl"], "a wheel with --no-deps"),
        (["--no-deps", "-e", f"git+https://x/y.git@{'a' * 40}"], "VCS pinned to a commit"),
    ]

    UNPINNED = [
        ([], "bare `pip install`"),
        (["coverage"], "a bare package name"),
        (["pip-audit==2.10.1"], "a version pin without a hash"),
        (["build==1.5.0"], "a version pin without a hash"),
        (["-e", "."], "editable install WITHOUT --no-deps"),
        (["-e", ".", "coverage"], "editable install plus an unpinned package"),
        (["-r", "requirements/runtime.txt"], "a requirements file WITHOUT --require-hashes"),
        (["dist/foo.whl", "cyclonedx-bom==7.3.0"], "a wheel plus an unpinned package"),
        (["--no-deps", "-e", "git+https://x/y.git@main"], "VCS pinned only to a branch"),
    ]

    def test_pinned_shapes_are_accepted(self) -> None:
        for args, why in self.PINNED:
            with self.subTest(command=" ".join(args) or "<none>", shape=why):
                self.assertFalse(
                    _is_unpinned_pip_install(args),
                    f"{why} should count as pinned",
                )

    def test_unpinned_shapes_are_rejected(self) -> None:
        for args, why in self.UNPINNED:
            with self.subTest(command=" ".join(args) or "<none>", shape=why):
                self.assertTrue(
                    _is_unpinned_pip_install(args),
                    f"{why} should count as unpinned",
                )

    def test_editable_source_pinning(self) -> None:
        self.assertTrue(_is_pinned_editable_source("."))
        self.assertTrue(_is_pinned_editable_source("./subdir"))
        self.assertTrue(_is_pinned_editable_source(f"git+https://x/y.git@{'f' * 40}"))
        self.assertFalse(_is_pinned_editable_source("git+https://x/y.git@main"))
        self.assertFalse(_is_pinned_editable_source("git+https://x/y.git@v1.0"))


class ShellParsingTests(unittest.TestCase):
    """The parser must see whole commands, including wrapped ones."""

    def test_backslash_continuations_are_folded(self) -> None:
        script = "python -m pip install --require-hashes \\\n  -r a.txt -r b.txt\n"
        self.assertEqual(
            _join_continuations(script),
            ["python -m pip install --require-hashes -r a.txt -r b.txt"],
        )

    def test_multiple_continuations_fold_into_one_line(self) -> None:
        script = "pip install \\\n  --require-hashes \\\n  -r a.txt\n"
        self.assertEqual(_join_continuations(script), ["pip install --require-hashes -r a.txt"])

    def test_a_wrapped_install_is_read_in_full(self) -> None:
        # The regression that motivated the folding: read line-by-line, this is
        # an argument-less `pip install` that would be waved through as pinned.
        script = "python -m pip install --require-hashes \\\n  -r requirements/runtime.txt\n"
        installs = _pip_installs(script)
        self.assertEqual(installs, [["--require-hashes", "-r", "requirements/runtime.txt"]])
        self.assertFalse(_is_unpinned_pip_install(installs[0]))

    def test_unwrapped_installs_still_parse(self) -> None:
        script = "python -m pip install --no-deps -e .\npip3 install foo\n"
        self.assertEqual(_pip_installs(script), [["--no-deps", "-e", "."], ["foo"]])

    def test_non_install_pip_commands_are_ignored(self) -> None:
        self.assertEqual(_pip_installs("python -m pip --version\npip list\n"), [])


class WorkflowPipPinningTests(unittest.TestCase):
    """No workflow may install Python packages in an unpinned shape (#142)."""

    def test_every_pip_install_is_pinned(self) -> None:
        seen = 0
        for workflow, job, script in _workflow_scripts():
            for args in _pip_installs(script):
                seen += 1
                with self.subTest(workflow=workflow, job=job, args=" ".join(args)):
                    self.assertFalse(
                        _is_unpinned_pip_install(args),
                        f"{workflow}:{job} runs an unpinned `pip install "
                        f"{' '.join(args)}`. Accepted shapes: `--require-hashes -r "
                        "<lock>`, `--no-deps -e <local path>`, or a bare `*.whl` "
                        "(#142)",
                    )
        self.assertGreater(seen, 0, "expected to find pip installs in the workflows")

    def test_every_referenced_lock_file_exists(self) -> None:
        for workflow, job, script in _workflow_scripts():
            for args in _pip_installs(script):
                for i, tok in enumerate(args):
                    if tok in ("-r", "--requirement"):
                        target = _ROOT / args[i + 1]
                        with self.subTest(workflow=workflow, job=job, req=args[i + 1]):
                            self.assertTrue(
                                target.is_file(),
                                f"{workflow}:{job} installs from {args[i + 1]}, "
                                "which does not exist",
                            )


class LockFileIntegrityTests(unittest.TestCase):
    """The committed locks must be fully hashed and mutually consistent."""

    def test_audit_lock_excludes_pip_affected_by_pysec_2026_3721(self) -> None:
        pins = _parse_lock(_REQ_DIR / "pip-audit.txt")
        self.assertGreaterEqual(Version(pins["pip"]), Version("26.2"))

    def test_every_requirement_is_exactly_pinned_and_hashed(self) -> None:
        for path in _lock_files():
            text = path.read_text(encoding="utf-8")
            pins = _parse_lock(path)
            with self.subTest(lock=path.name):
                self.assertTrue(pins, f"{path.name} pins no packages")
                # `--require-hashes` fails the install outright if any entry
                # lacks a hash, so assert one hash per pinned distribution.
                self.assertGreaterEqual(
                    text.count("--hash=sha256:"),
                    len(pins),
                    f"{path.name} has fewer sha256 hashes than pinned packages; "
                    "regenerate with `uv pip compile --generate-hashes`",
                )
            for name, version in pins.items():
                with self.subTest(lock=path.name, package=name):
                    # A bare version is not a pin unless it is an `==` pin, which
                    # _PIN_RE already required; guard against ranges sneaking in.
                    self.assertNotIn(",", version, f"{name} must be a single == pin")

    def test_legacy_release_lock_matches_the_2_0_2_runtime(self) -> None:
        pins = _parse_lock(_REQ_DIR / "recovery-v2.0.2.txt")
        self.assertEqual(pins.get("a" + "ces-sdl"), "0.23.1")
        self.assertEqual(pins.get("cyclonedx-bom"), "7.3.0")
        self.assertIn("pyyaml", pins)

    def test_co_installed_locks_agree_on_shared_packages(self) -> None:
        # A workflow job is one Python environment: every lock installed by any
        # step of that job lands in the same site-packages. If two of them
        # disagree on a shared transitive package, the second install silently
        # moves the first one's dependency -- or `--require-hashes` fails the run
        # outright.
        #
        # Only *co-installed* locks are compared, and the grouping is derived
        # from the workflows rather than hard-coded, so adding a step to a job
        # extends the check automatically. Locks that never share an environment
        # are free to disagree: requirements/docs.txt is built by Read the Docs
        # alone and legitimately pins an older markdown-it-py than the runtime
        # closure, because myst-parser requires it.
        for (workflow, job), locks in sorted(_locks_per_job().items()):
            if len(locks) < 2:
                continue
            parsed = {name: _parse_lock(_ROOT / name) for name in sorted(locks)}
            for name, pins in parsed.items():
                for other, other_pins in parsed.items():
                    if name >= other:
                        continue
                    for pkg in sorted(set(pins) & set(other_pins)):
                        with self.subTest(job=f"{workflow}:{job}", package=pkg):
                            self.assertEqual(
                                pins[pkg], other_pins[pkg],
                                f"{workflow}:{job} installs both {name} and "
                                f"{other} into one environment, but they pin "
                                f"{pkg} to {pins[pkg]} and {other_pins[pkg]}. "
                                "Regenerate them together.",
                            )


class LockMatchesProjectMetadataTests(unittest.TestCase):
    """The runtime lock must satisfy -- not replace -- pyproject's constraints."""

    def setUp(self) -> None:
        self.declared = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
        self.runtime = _parse_lock(_REQ_DIR / "runtime.txt")

    def test_runtime_lock_satisfies_declared_dependencies(self) -> None:
        for spec in self.declared["project"]["dependencies"]:
            req = Requirement(spec)
            key = req.name.lower().replace("_", "-")
            with self.subTest(dependency=spec):
                self.assertIn(
                    key, self.runtime,
                    f"{req.name} is declared in pyproject.toml but absent from "
                    "requirements/runtime.txt; regenerate the lock",
                )
                self.assertTrue(
                    req.specifier.contains(Version(self.runtime[key]), prereleases=True),
                    f"requirements/runtime.txt pins {req.name}=="
                    f"{self.runtime[key]}, which does not satisfy the declared "
                    f"constraint {spec!r}",
                )

    def test_declared_floor_is_not_rewritten_as_a_lock(self) -> None:
        # Guardrail from the #142 architecture preflight: this package is a
        # library. Its published metadata must keep compatibility ranges so
        # consumers can resolve; the CI lock is a separate artifact.
        specs = self.declared["project"]["dependencies"]
        self.assertTrue(
            any("==" not in s for s in specs),
            "pyproject.toml dependencies collapsed to all-exact pins. The CI "
            "lock lives in requirements/, not in the distributed metadata "
            "(#142 preflight guardrail).",
        )


if __name__ == "__main__":
    unittest.main()
