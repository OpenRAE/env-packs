"""Consumer pack-check CLI and diagnostic presentation (issue #187, ADR 0031)."""

from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import yaml

from raes_env_packs import check as _check
from raes_env_packs import new_pack as _new_pack
from raes_env_packs.validation import ValidationResult, validate_pack

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = _ROOT / "src" / "raes_env_packs" / "resources" / "template"
_DOC = _ROOT / "docs" / "public" / "checking.md"
_VALID_SDL = "name: example-pack\nnodes:\n  target:\n    type: vm\n"

# Codes the static authority can emit (validation.py), plus the two schema
# families. The catalog must resolve every one of these to an actionable
# diagnostic.
_SCHEMA_SUBCODES = (
    "required",
    "enum",
    "pattern",
    "type",
    "unknown",
    "min-items",
    "const",
    "ref",
)
_KNOWN_CODES = (
    "pack.missing",
    "pack.type",
    "pack.identity.missing",
    "pack.identity.name-mismatch",
    "yaml.invalid",
    "yaml.invalid-utf8",
    "yaml.duplicate-key",
    "filesystem.invalid-root",
    "filesystem.unsafe-member",
    "filesystem.changed",
    "resource.metadata-limit",
    "resource.sdl-limit",
    "resource.member-limit",
    "challenges.category.forbidden",
    "provenance.pointer.missing",
    "provenance.pointer.invalid",
    "provenance.missing",
    "provenance.type",
    "provenance.name-mismatch",
    "provenance.safety.required",
    "provenance.review-gate.missing",
    "compatibility.pointer.invalid",
    "compatibility.missing",
    "compatibility.type",
    "compatibility.boundary-overlap",
    "sdl.missing",
    "sdl.invalid",
    "sdl.invalid-utf8",
    "sdl.imports-denied",
) + tuple(f"provenance.schema.{sub}" for sub in _SCHEMA_SUBCODES) + tuple(
    f"compatibility.schema.{sub}" for sub in _SCHEMA_SUBCODES
)


def _valid_pack(parent: Path, name: str = "example-pack") -> Path:
    """A pack that passes ``validate_pack`` — the canonical quickstart shape."""

    root = parent / name
    shutil.copytree(_TEMPLATE, root)
    for rel in ("pack.yaml", "pack.compatibility.yaml", "docs/provenance-ledger.yaml"):
        path = root / rel
        path.write_text(
            path.read_text(encoding="utf-8").replace("<name>", name),
            encoding="utf-8",
        )
    (root / "sdl" / "example.sdl.yaml").write_text(_VALID_SDL, encoding="utf-8")
    return root


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = _check.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CheckFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = _valid_pack(self.tmp)


class CliContractTests(CheckFixture):
    def test_valid_pack_exits_zero_and_is_silent_about_problems(self) -> None:
        code, out, err = _run(str(self.root))
        self.assertEqual(code, _check.EXIT_OK, out + err)
        self.assertIn("OK", out)
        self.assertEqual(err, "")

    def test_valid_pack_json_envelope(self) -> None:
        code, out, err = _run(str(self.root), "--json")
        self.assertEqual(code, _check.EXIT_OK)
        document = json.loads(out)  # stdout is only the JSON document
        self.assertEqual(document["version"], _check.ENVELOPE_VERSION)
        self.assertTrue(document["ok"])
        self.assertEqual(document["pack"], "example-pack")
        self.assertEqual(document["diagnostics"], [])
        self.assertEqual(document["summary"]["total"], 0)
        self.assertEqual(err, "")

    def test_broken_pack_exits_one_with_actionable_text(self) -> None:
        (self.root / "pack.yaml").unlink()
        code, out, err = _run(str(self.root))
        self.assertEqual(code, _check.EXIT_BLOCKING)
        self.assertIn("pack.missing", out)
        self.assertIn("fix:", out)

    def test_broken_pack_json_is_the_only_thing_on_stdout(self) -> None:
        (self.root / "pack.yaml").unlink()
        code, out, err = _run(str(self.root), "--json")
        self.assertEqual(code, _check.EXIT_BLOCKING)
        document = json.loads(out)  # would raise if stdout carried anything else
        self.assertFalse(document["ok"])
        codes = [item["code"] for item in document["diagnostics"]]
        self.assertIn("pack.missing", codes)

    def test_json_envelope_never_leaks_the_absolute_path(self) -> None:
        (self.root / "pack.yaml").unlink()
        _code, out, _err = _run(str(self.root), "--json")
        self.assertNotIn(str(self.root), out)
        self.assertNotIn(str(self.tmp), out)

    def test_missing_argument_is_a_usage_error(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            _check.main([])
        self.assertEqual(caught.exception.code, _check.EXIT_USAGE)

    def test_nonexistent_pack_root_is_a_usage_error(self) -> None:
        target = str(self.tmp / "nope")
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                _check.main([target])
        self.assertEqual(caught.exception.code, _check.EXIT_USAGE)

    def test_unexpected_defect_is_a_bounded_tool_failure(self) -> None:
        boom = RuntimeError("secret-detail-that-must-not-leak")
        with mock.patch.object(_check, "validate_pack", side_effect=boom):
            code, out, err = _run(str(self.root))
        self.assertEqual(code, _check.EXIT_TOOL_FAILURE)
        self.assertIn("internal error (RuntimeError)", err)
        self.assertNotIn("secret-detail", err)
        self.assertEqual(out, "")


class TerminalSafetyTests(CheckFixture):
    """codex F3: untrusted filesystem-derived names must not drive the terminal."""

    def test_terminal_safe_escapes_controls_and_separators(self) -> None:
        self.assertEqual(_check._terminal_safe("clean-name"), "clean-name")
        escaped = _check._terminal_safe("a\x1b[2Jb\nc d\tf")
        for danger in ("\x1b", "\n", " ", "\t"):
            self.assertNotIn(danger, escaped)
        self.assertIn("\\x1b", escaped)

    def test_human_output_escapes_untrusted_pack_and_member_names(self) -> None:
        # A crafted member path (ESC) and directory name (newline + fake verdict).
        diagnostic = _check.Diagnostic(
            code="sdl.invalid",
            path="sdl/in\x1bjection.sdl.yaml",
            field_path=None,
            message="sdl.invalid: sdl/in\x1bjection.sdl.yaml",
        )
        report = _check.build_report(
            ValidationResult((diagnostic,)),
            "pack\nOK — no blocking problems found.",
        )
        human = _check.render_human(report)
        self.assertNotIn("\x1b", human)
        # The injected text cannot become a standalone, spoofed verdict line.
        self.assertNotIn("OK — no blocking problems found.", human.splitlines())
        # JSON keeps the real bytes; json.dumps escapes them for machine consumers.
        document = json.loads(_check.render_json(report))
        self.assertEqual(document["diagnostics"][0]["file"], "sdl/in\x1bjection.sdl.yaml")
        self.assertEqual(document["pack"], "pack\nOK — no blocking problems found.")

    def test_usage_error_escapes_the_raw_argument(self) -> None:
        bad = str(self.tmp / "no\x1bpe")
        err = io.StringIO()
        with redirect_stderr(err):
            with self.assertRaises(SystemExit) as caught:
                _check.main([bad])
        self.assertEqual(caught.exception.code, _check.EXIT_USAGE)
        self.assertNotIn("\x1b", err.getvalue())


class ParityTests(CheckFixture):
    def test_human_and_json_express_the_same_result(self) -> None:
        # Break several domains at once so parity is non-trivial.
        (self.root / "sdl" / "example.sdl.yaml").unlink()
        ledger_path = self.root / "docs" / "provenance-ledger.yaml"
        ledger = _load(ledger_path)
        ledger["content_safety"]["no_real_malware"] = False
        _dump(ledger_path, ledger)

        report = _check.build_report(validate_pack(self.root), "example-pack")
        document = json.loads(_check.render_json(report))
        human = _check.render_human(report)

        report_codes = [item["code"] for item in report.diagnostics]
        json_codes = [item["code"] for item in document["diagnostics"]]
        self.assertEqual(json_codes, report_codes)  # same set and ordering
        self.assertEqual(document["ok"], report.ok)  # same verdict
        self.assertEqual(document["summary"]["total"], len(report.diagnostics))  # same count
        for code in report_codes:
            self.assertIn(code, human)  # every finding is in the human view too
        self.assertFalse(report.ok)
        self.assertGreater(len(report_codes), 1)


class PresentationCatalogTests(unittest.TestCase):
    def test_every_known_code_resolves_to_an_actionable_diagnostic(self) -> None:
        for code in _KNOWN_CODES:
            with self.subTest(code=code):
                presentation = _check.presentation_for(code)
                self.assertIn(presentation.domain, {"pack", "sdl", "compatibility", "trust"})
                self.assertIn(presentation.owner, {"env-packs", "raes"})
                self.assertTrue(presentation.explanation.strip())
                self.assertTrue(presentation.reason.strip())
                self.assertTrue(presentation.suggestion.strip())

    def test_domain_and_owner_follow_the_ownership_boundary(self) -> None:
        cases = {
            "pack.identity.name-mismatch": ("pack", "env-packs"),
            "yaml.invalid": ("pack", "env-packs"),
            "provenance.name-mismatch": ("trust", "env-packs"),
            "compatibility.boundary-overlap": ("compatibility", "env-packs"),
            "sdl.invalid": ("sdl", "raes"),
            "sdl.imports-denied": ("sdl", "raes"),
        }
        for code, (domain, owner) in cases.items():
            with self.subTest(code=code):
                presentation = _check.presentation_for(code)
                self.assertEqual((presentation.domain, presentation.owner), (domain, owner))

    def test_schema_subcode_enriches_the_suggestion(self) -> None:
        base = _check.presentation_for("provenance.schema")
        enriched = _check.presentation_for("provenance.schema.required")
        self.assertNotEqual(enriched.suggestion, base.suggestion)
        self.assertIn("required field is missing", enriched.suggestion)

    def test_unknown_code_fails_closed_to_a_generic_diagnostic(self) -> None:
        presentation = _check.presentation_for("brand.new.namespace.oops")
        self.assertTrue(presentation.explanation.strip())
        self.assertTrue(presentation.suggestion.strip())


def _mutations() -> list[tuple[str, str]]:
    """Return (label, expected code prefix) markers for the corpus builders."""

    return [
        ("missing pack.yaml", "pack.missing"),
        ("wrong pack name", "pack.identity.name-mismatch"),
        ("missing title", "pack.identity.missing"),
        ("broken pack yaml", "yaml.invalid"),
        ("missing provenance ledger", "provenance.missing"),
        ("provenance name mismatch", "provenance.name-mismatch"),
        ("safety flag false", "provenance.safety.required"),
        ("missing review gate", "provenance.review-gate.missing"),
        ("provenance schema break", "provenance.schema"),
        ("compatibility schema break", "compatibility.schema"),
        ("missing sdl", "sdl.missing"),
        ("invalid sdl", "sdl.invalid"),
    ]


def _apply_mutation(root: Path, label: str) -> None:
    pack_yaml = root / "pack.yaml"
    ledger_path = root / "docs" / "provenance-ledger.yaml"
    if label == "missing pack.yaml":
        pack_yaml.unlink()
    elif label == "wrong pack name":
        pack = _load(pack_yaml)
        pack["name"] = "some-other-name"
        _dump(pack_yaml, pack)
    elif label == "missing title":
        pack = _load(pack_yaml)
        pack.pop("title", None)
        _dump(pack_yaml, pack)
    elif label == "broken pack yaml":
        pack_yaml.write_text("name: [unterminated\n", encoding="utf-8")
    elif label == "missing provenance ledger":
        ledger_path.unlink()
    elif label == "provenance name mismatch":
        ledger = _load(ledger_path)
        ledger["pack"]["name"] = "wrong-name"
        _dump(ledger_path, ledger)
    elif label == "safety flag false":
        ledger = _load(ledger_path)
        ledger["content_safety"]["no_real_malware"] = False
        _dump(ledger_path, ledger)
    elif label == "missing review gate":
        ledger = _load(ledger_path)
        ledger["review"]["gates"] = [
            gate for gate in ledger["review"]["gates"]
            if gate.get("gate_id") != "licensing"
        ]
        _dump(ledger_path, ledger)
    elif label == "provenance schema break":
        ledger = _load(ledger_path)
        ledger["schema_version"] = "not-the-const"
        _dump(ledger_path, ledger)
    elif label == "compatibility schema break":
        manifest = _load(root / "pack.compatibility.yaml")
        manifest["schema_version"] = "not-the-const"
        _dump(root / "pack.compatibility.yaml", manifest)
    elif label == "missing sdl":
        (root / "sdl" / "example.sdl.yaml").unlink()
    elif label == "invalid sdl":
        (root / "sdl" / "example.sdl.yaml").write_text(
            "this: is: not: valid: sdl\n", encoding="utf-8"
        )
    else:  # pragma: no cover - guard against a typo'd label
        raise AssertionError(label)


class ActionableCorpusTests(unittest.TestCase):
    """AC: >=80% of representative first-time failures give an actionable fix."""

    def test_actionable_correction_ratio_meets_the_bar(self) -> None:
        corpus = _mutations()
        actionable = 0
        for label, expected_prefix in corpus:
            with self.subTest(failure=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = _valid_pack(Path(tmp))
                    _apply_mutation(root, label)
                    report = _check.build_report(validate_pack(root), "example-pack")
                    self.assertFalse(report.ok, f"{label} should be invalid")
                    matches = [
                        item for item in report.diagnostics
                        if str(item["code"]).startswith(expected_prefix)
                    ]
                    if matches and all(
                        str(item["suggestion"]).strip() and str(item["doc"]).strip()
                        for item in matches
                    ):
                        actionable += 1
        ratio = actionable / len(corpus)
        self.assertGreaterEqual(ratio, 0.80, f"only {actionable}/{len(corpus)} actionable")


class QuickstartPackTests(unittest.TestCase):
    """AC: works from a clean install, exercised by the canonical quickstart pack."""

    def _scaffold_quickstart(self, tmp: Path) -> Path:
        (tmp / "environments").mkdir()
        (tmp / ".git").mkdir()
        target = Path(
            _new_pack.scaffold_pack(
                str(tmp), "example-pack", "Example Pack", "one line", None, None
            )
        )
        # Fill the two things only the author knows, exactly as the quickstart does.
        (target / "sdl" / "example.sdl.yaml").write_text(_VALID_SDL, encoding="utf-8")
        ledger_path = target / "docs" / "provenance-ledger.yaml"
        ledger = _load(ledger_path)
        ledger["pack"] = {"name": "example-pack"}
        _dump(ledger_path, ledger)
        return target

    def test_scaffolded_quickstart_pack_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = self._scaffold_quickstart(Path(tmp))
            code, out, _err = _run(str(target))
            self.assertEqual(code, _check.EXIT_OK, out)

    def test_scaffolded_quickstart_pack_breaks_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = self._scaffold_quickstart(Path(tmp))
            (target / "sdl" / "example.sdl.yaml").unlink()
            code, _out, _err = _run(str(target), "--json")
            self.assertEqual(code, _check.EXIT_BLOCKING)


def _heading_slugs(text: str) -> set[str]:
    slugs = set()
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.*?)\s*$", line)
        if match:
            title = match.group(1).lower()
            title = re.sub(r"[^a-z0-9 -]", "", title)
            slugs.add(title.replace(" ", "-"))
    return slugs


class DocTargetTests(unittest.TestCase):
    def test_every_diagnostic_doc_anchor_exists_in_the_doc(self) -> None:
        self.assertTrue(_DOC.is_file(), f"missing {_DOC}")
        slugs = _heading_slugs(_DOC.read_text(encoding="utf-8"))
        for code in _KNOWN_CODES:
            with self.subTest(code=code):
                doc_target = _check._enriched(
                    _check.Diagnostic(code=code, message=code)
                )["doc"]
                anchor = str(doc_target).split("#", 1)[1]
                self.assertIn(anchor, slugs)


if __name__ == "__main__":
    unittest.main()
