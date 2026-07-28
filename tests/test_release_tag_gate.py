"""Tests for the release-tag signing gate (tools/release_tag_gate.py).

The release workflow (``.github/workflows/release-please.yml``) and these tests
call the same pure functions, so the release-detection / validation / notes
policy cannot drift between the workflow YAML and local enforcement (mirrors the
``tools/check_pr_title.py`` seam, ADR 0006). The gate is what lets Release Please
run in PR-only mode while the workflow creates, signs, and verifies the tag
(ADR 0017).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

_GATE = Path(__file__).resolve().parents[1] / "tools" / "release_tag_gate.py"
_spec = importlib.util.spec_from_file_location("release_tag_gate", _GATE)
gate = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
# Register before exec so dataclass annotation resolution can find the module.
sys.modules[_spec.name] = gate
_spec.loader.exec_module(gate)

_NULL_SHA = "0" * 40
_SHA_A = "a" * 40
_SHA_B = "b" * 40

_PYPROJECT = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "raes-env-packs"
version = "{version}"
dependencies = ["PyYAML>=6"]
"""

_CHANGELOG = """\
# Changelog

<!-- towncrier release notes start -->

## [2.1.0](https://example.com/compare/v2.0.1...v2.1.0) (2026-08-01)


### Features

* sign release tags with keyless Sigstore ([#59](https://example.com/issues/59))


### Bug Fixes

* handle empty input ([#60](https://example.com/issues/60))

## [2.0.1](https://example.com/compare/v2.0.0...v2.0.1) (2026-07-17)


### Bug Fixes

* **deps:** bump raes ([#123](https://example.com/issues/123))
"""


def _pyproject(version: str) -> str:
    return _PYPROJECT.format(version=version)


def _manifest(version: str) -> str:
    return json.dumps({".": version})


class ParseProjectVersionTests(unittest.TestCase):
    def test_extracts_project_version(self) -> None:
        self.assertEqual(gate.parse_project_version(_pyproject("2.0.1")), "2.0.1")

    def test_missing_project_version_raises(self) -> None:
        text = "[project]\nname = \"x\"\n"
        with self.assertRaises(gate.GateError):
            gate.parse_project_version(text)

    def test_invalid_toml_raises(self) -> None:
        with self.assertRaises(gate.GateError):
            gate.parse_project_version("this is not = valid = toml [[[")


class SemverTests(unittest.TestCase):
    def test_accepts_stable_semver(self) -> None:
        for v in ("0.1.0", "2.0.1", "10.20.30"):
            with self.subTest(v=v):
                self.assertTrue(gate.is_stable_semver(v))

    def test_rejects_non_stable_semver(self) -> None:
        for v in ("2.0", "2", "2.0.1-rc1", "2.0.1+build", "v2.0.1", "", "abc", "1.2.3.4"):
            with self.subTest(v=v):
                self.assertFalse(gate.is_stable_semver(v))


class ManifestTests(unittest.TestCase):
    def test_valid_manifest(self) -> None:
        gate.validate_manifest(_manifest("2.0.1"), "2.0.1")  # no raise

    def test_extra_key_raises(self) -> None:
        text = json.dumps({".": "2.0.1", "pkg": "1.0.0"})
        with self.assertRaises(gate.GateError):
            gate.validate_manifest(text, "2.0.1")

    def test_missing_root_key_raises(self) -> None:
        text = json.dumps({"pkg": "2.0.1"})
        with self.assertRaises(gate.GateError):
            gate.validate_manifest(text, "2.0.1")

    def test_version_mismatch_raises(self) -> None:
        text = _manifest("2.0.0")
        with self.assertRaises(gate.GateError):
            gate.validate_manifest(text, "2.0.1")

    def test_invalid_json_raises(self) -> None:
        with self.assertRaises(gate.GateError):
            gate.validate_manifest("{not json", "2.0.1")


class ExpectedTagTests(unittest.TestCase):
    def test_v_prefixed(self) -> None:
        self.assertEqual(gate.expected_tag("2.1.0"), "v2.1.0")


class AuthorizationTests(unittest.TestCase):
    def test_release_pr_label_authorizes(self) -> None:
        self.assertTrue(gate.is_release_authorized(["autorelease: pending"]))
        self.assertTrue(
            gate.is_release_authorized(["other", "autorelease: pending"])
        )

    def test_missing_label_is_unauthorized(self) -> None:
        self.assertFalse(gate.is_release_authorized([]))
        self.assertFalse(gate.is_release_authorized(["enhancement", "bug"]))
        # A tagged (already-completed) label is not a fresh authorization.
        self.assertFalse(gate.is_release_authorized(["autorelease: tagged"]))


class DetectReleaseTests(unittest.TestCase):
    def test_unchanged_version_is_no_release(self) -> None:
        decision = gate.detect_release(
            _pyproject("2.0.1"), _pyproject("2.0.1"), _manifest("2.0.1")
        )
        self.assertFalse(decision.release)
        self.assertIsNone(decision.tag)

    def test_changed_version_is_release(self) -> None:
        decision = gate.detect_release(
            _pyproject("2.0.1"), _pyproject("2.1.0"), _manifest("2.1.0")
        )
        self.assertTrue(decision.release)
        self.assertEqual(decision.version, "2.1.0")
        self.assertEqual(decision.tag, "v2.1.0")

    def test_no_prior_revision_is_no_release(self) -> None:
        decision = gate.detect_release(None, _pyproject("2.1.0"), _manifest("2.1.0"))
        self.assertFalse(decision.release)

    def test_changed_to_non_semver_fails_closed(self) -> None:
        before, after, manifest = _pyproject("2.0.1"), _pyproject("2.1"), _manifest("2.1")
        with self.assertRaises(gate.GateError):
            gate.detect_release(before, after, manifest)

    def test_changed_with_manifest_mismatch_fails_closed(self) -> None:
        before, after, manifest = _pyproject("2.0.1"), _pyproject("2.1.0"), _manifest("9.9.9")
        with self.assertRaises(gate.GateError):
            gate.detect_release(before, after, manifest)


class ExtractReleaseNotesTests(unittest.TestCase):
    def test_extracts_requested_section(self) -> None:
        notes = gate.extract_release_notes(_CHANGELOG, "2.1.0")
        self.assertIn("sign release tags with keyless Sigstore", notes)
        self.assertIn("handle empty input", notes)
        # Must not bleed into the previous version's section.
        self.assertNotIn("bump raes", notes)
        # The version heading itself is not part of the body notes.
        self.assertNotIn("## [2.1.0]", notes)

    def test_exact_version_match_only(self) -> None:
        # "2.0.1" must not be satisfied by a "2.0.10" heading.
        changelog = "## [2.0.10](x) (d)\n\nnope\n"
        with self.assertRaises(gate.GateError):
            gate.extract_release_notes(changelog, "2.0.1")

    def test_missing_version_fails_closed(self) -> None:
        with self.assertRaises(gate.GateError):
            gate.extract_release_notes(_CHANGELOG, "9.9.9")


class CliCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_git_show = gate._git_show

        def fake_git_show(sha: str, path: str) -> str:
            table = {
                (_SHA_A, "pyproject.toml"): _pyproject("2.0.1"),
                (_SHA_B, "pyproject.toml"): _pyproject("2.1.0"),
                (_SHA_B, ".release-please-manifest.json"): _manifest("2.1.0"),
            }
            if (sha, path) not in table:
                raise gate.GateError(f"unexpected git show {sha}:{path}")
            return table[(sha, path)]

        gate._git_show = fake_git_show
        self.addCleanup(lambda: setattr(gate, "_git_show", self._orig_git_show))

    def _labels_file(self, labels: list[str]) -> str:
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as fh:
            fh.write("\n".join(labels))
            return fh.name

    def _run_check(self, before: str, after: str,
                   labels: list[str] | None = None) -> dict[str, str]:
        if labels is None:
            labels = ["autorelease: pending"]
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as fh:
            out_path = fh.name
        rc = gate.main(["check", "--before", before, "--after", after,
                        "--merged-pr-labels-file", self._labels_file(labels),
                        "--github-output", out_path])
        self.assertEqual(rc, 0)
        outputs: dict[str, str] = {}
        for line in Path(out_path).read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                outputs[key] = value
        return outputs

    def test_authorized_release_transition_emits_tag(self) -> None:
        outputs = self._run_check(_SHA_A, _SHA_B)
        self.assertEqual(outputs["release"], "true")
        self.assertEqual(outputs["tag"], "v2.1.0")
        self.assertEqual(outputs["version"], "2.1.0")

    def test_version_change_without_label_is_no_release(self) -> None:
        # The security binding: a version bump alone (no authenticated release-PR
        # label) must NOT authorize a release.
        outputs = self._run_check(_SHA_A, _SHA_B, labels=["enhancement"])
        self.assertEqual(outputs["release"], "false")
        self.assertNotIn("tag", outputs)

    def test_missing_labels_file_is_no_release(self) -> None:
        with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as fh:
            out_path = fh.name
        rc = gate.main(["check", "--before", _SHA_A, "--after", _SHA_B,
                        "--github-output", out_path])
        self.assertEqual(rc, 0)
        self.assertIn("release=false",
                      Path(out_path).read_text(encoding="utf-8"))

    def test_null_before_is_no_release(self) -> None:
        outputs = self._run_check(_NULL_SHA, _SHA_B)
        self.assertEqual(outputs["release"], "false")

    def test_non_sha_after_fails_closed(self) -> None:
        rc = gate.main(["check", "--before", _SHA_A, "--after", "notasha",
                        "--merged-pr-labels-file", self._labels_file(["autorelease: pending"]),
                        "--github-output", "/dev/null"])
        self.assertNotEqual(rc, 0)


class CliNotesTests(unittest.TestCase):
    def test_writes_notes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(_CHANGELOG, encoding="utf-8")
            out = Path(tmp) / "notes.md"
            rc = gate.main(["notes", "--version", "2.1.0",
                            "--changelog", str(changelog), "--output", str(out)])
            self.assertEqual(rc, 0)
            body = out.read_text(encoding="utf-8")
            self.assertIn("keyless Sigstore", body)
            self.assertNotIn("bump raes", body)

    def test_missing_version_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(_CHANGELOG, encoding="utf-8")
            out = Path(tmp) / "notes.md"
            rc = gate.main(["notes", "--version", "9.9.9",
                            "--changelog", str(changelog), "--output", str(out)])
            self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
