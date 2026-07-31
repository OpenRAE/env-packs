"""Progressive scaffold wizard (issue #189, ADR 0034).

These tests drive the wizard as its two front ends do — the non-interactive
replay/build path used by Hub and MCP, and the interactive question flow a
non-developer uses — and prove the pack it writes passes the same static check
(`validate_pack`) users run later. They cover every acceptance criterion in the
issue: a valid minimal pack, consequence-bearing questions with safe defaults
and an explicit not-sure state, RAES-owned SDL choices/errors, selective
generation, domain neutrality, deterministic no-silent-overwrite replay, the
machine-readable mode, and one non-developer task per primary persona.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from raes_env_packs import validate_pack
from raes_env_packs import wizard


REQUIRED_MINIMAL = (
    "docs/attack-path.md",
    "docs/concepts.md",
    "docs/provenance-ledger.yaml",
    "pack.yaml",
    "sdl/example-pack.sdl.yaml",
)


def _inputs(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "version": wizard.WIZARD_INPUT_VERSION,
        "pack_id": "example-pack",
        "route": "minimal",
        "answers": {},
    }
    base.update(over)
    return base


class PackIdTests(unittest.TestCase):
    def test_valid_ids_accepted(self) -> None:
        for pack_id in ("a", "example-pack", "range-01"):
            wizard.validate_pack_id(pack_id)

    def test_invalid_ids_rejected(self) -> None:
        for bad in ("Bad_Id", "../evil", "-leading", "UPPER", "a/b", ""):
            with self.assertRaises(SystemExit):
                wizard.validate_pack_id(bad)

    def test_title_from_pack_id(self) -> None:
        self.assertEqual(wizard.title_from_pack_id("blind-example"), "Blind Example")


class ProposalTests(unittest.TestCase):
    def test_minimal_manifest_is_exactly_the_required_tier(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        self.assertEqual(proposal.manifest(), REQUIRED_MINIMAL)

    def test_minimal_pack_yaml_has_no_optional_pointers(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        pack = yaml.safe_load(proposal.files["pack.yaml"])
        self.assertNotIn("compatibility_manifest", pack)
        self.assertEqual(pack["contents"],
                         {"flag_layer": False, "reference_triangle": False,
                          "profile_bundles": False})
        self.assertEqual(pack["provenance_ledger"], "docs/provenance-ledger.yaml")

    def test_build_is_deterministic(self) -> None:
        one = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        two = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        self.assertEqual(one.files, two.files)

    def test_unknown_version_fails_closed(self) -> None:
        with self.assertRaises(wizard.WizardError):
            wizard.normalize_inputs(_inputs(version="raes-pack-wizard-input/v99"))

    def test_unknown_route_fails_closed(self) -> None:
        with self.assertRaises(wizard.WizardError):
            wizard.normalize_inputs(_inputs(route="does-not-exist"))

    def test_unknown_capability_fails_closed(self) -> None:
        with self.assertRaises(wizard.WizardError):
            wizard.normalize_inputs(_inputs(capabilities=["not-a-layer"]))

    def test_unknown_answer_key_fails_closed(self) -> None:
        with self.assertRaises(wizard.WizardError):
            wizard.normalize_inputs(_inputs(answers={"nonsense": "x"}))

    def test_bad_pack_id_raises_bounded_wizard_error(self) -> None:
        # The DTO boundary must fail with the one bounded contract, not SystemExit.
        for bad in ("Bad_Id", "../evil", 123, None):
            with self.assertRaises(wizard.WizardError):
                wizard.normalize_inputs(_inputs(pack_id=bad))

    def test_unhashable_route_and_capability_fail_closed(self) -> None:
        with self.assertRaises(wizard.WizardError):
            wizard.normalize_inputs(_inputs(route=["not", "a", "route"]))
        with self.assertRaises(wizard.WizardError):
            wizard.normalize_inputs(_inputs(capabilities=[["unhashable"]]))

    def test_top_level_title_is_rejected_not_silently_ignored(self) -> None:
        with self.assertRaises(wizard.WizardError):
            wizard.normalize_inputs(_inputs(title="Top Level"))

    def test_title_and_description_flow_through_answers(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(
            _inputs(answers={"title": "My Title", "description": "My desc"})))
        pack = yaml.safe_load(proposal.files["pack.yaml"])
        self.assertEqual(pack["title"], "My Title")
        self.assertEqual(pack["description"], "My desc")


class SelectiveGenerationTests(unittest.TestCase):
    def test_security_route_ships_flag_layer_minimal_does_not(self) -> None:
        minimal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        secure = wizard.build_proposal(
            wizard.normalize_inputs(_inputs(route="security-exercise")))
        self.assertNotIn("flags/placement.yaml", minimal.manifest())
        self.assertIn("flags/placement.yaml", secure.manifest())
        self.assertIn("challenges/challenges.yaml", secure.manifest())
        pack = yaml.safe_load(secure.files["pack.yaml"])
        self.assertTrue(pack["contents"]["flag_layer"])

    def test_publication_route_ships_compatibility_manifest(self) -> None:
        pub = wizard.build_proposal(
            wizard.normalize_inputs(_inputs(route="publication-ready")))
        self.assertIn("pack.compatibility.yaml", pub.manifest())
        pack = yaml.safe_load(pub.files["pack.yaml"])
        self.assertEqual(pack["compatibility_manifest"], "pack.compatibility.yaml")

    def test_explicit_capability_adds_only_that_layer(self) -> None:
        proposal = wizard.build_proposal(
            wizard.normalize_inputs(_inputs(capabilities=["compatibility"])))
        self.assertIn("pack.compatibility.yaml", proposal.manifest())
        self.assertNotIn("flags/placement.yaml", proposal.manifest())


class SdlDelegationTests(unittest.TestCase):
    def test_generated_sdl_parses_through_raes(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        from raes import parse_sdl
        parse_sdl(proposal.files["sdl/example-pack.sdl.yaml"])

    def test_sdl_carries_only_identity_no_invented_topology(self) -> None:
        # The wizard owns identity, not scenario semantics: it must not invent
        # nodes, node types, or topology (ADR 0009/0034). The start state is the
        # scenario name only; node authoring is RAES's, done later.
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        sdl = yaml.safe_load(proposal.files["sdl/example-pack.sdl.yaml"])
        self.assertEqual(sdl, {"name": "example-pack"})


class QuestionContractTests(unittest.TestCase):
    def test_every_question_has_consequence_and_default_or_not_sure(self) -> None:
        seen = 0
        for route_id in wizard.ROUTES:
            for question in wizard.route_questions(route_id):
                seen += 1
                self.assertTrue(question.consequence,
                                f"{route_id}:{question.key} lacks a consequence")
                self.assertTrue(question.default is not None or question.allow_not_sure,
                                f"{route_id}:{question.key} has neither default nor not-sure")
        self.assertGreater(seen, 0)


class NotSureTests(unittest.TestCase):
    def test_not_sure_stays_unresolved_and_never_becomes_a_claim(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(
            _inputs(route="publication-ready",
                    answers={"publication_cleared": wizard.NOT_SURE})))
        self.assertIn("publication_cleared", dict(proposal.unresolved))
        # The provenance review gate must remain pending, never silently approved.
        ledger = yaml.safe_load(proposal.files["docs/provenance-ledger.yaml"])
        self.assertEqual(ledger["review"]["status"], "pending")

    def test_not_sure_on_required_answer_blocks_write(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(
            _inputs(route="publication-ready",
                    answers={"publication_cleared": wizard.NOT_SURE})))
        self.assertTrue(proposal.blocking_unresolved())
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "environments"
            env.mkdir()
            with self.assertRaises(wizard.WizardError):
                wizard.write_proposal(proposal, str(env))

    def test_publication_cleared_no_blocks_write(self) -> None:
        # Answering the affirmative clearance gate "no" is a resolved answer but
        # must NOT satisfy the gate — a not-cleared pack cannot be published.
        proposal = wizard.build_proposal(wizard.normalize_inputs(
            _inputs(route="publication-ready",
                    answers={"publication_cleared": "no"})))
        self.assertIn("publication_cleared",
                      dict(proposal.blocking_unresolved()))
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "environments"
            env.mkdir()
            with self.assertRaises(wizard.WizardError):
                wizard.write_proposal(proposal, str(env))


class DomainNeutralityTests(unittest.TestCase):
    # Offensive/live-fire *posture* — not safety-attestation vocabulary such as
    # the provenance ledger's `no_real_malware` / `offensive_tooling_boundary`,
    # which every valid pack carries.
    OFFENSIVE = ("live-fire", "live fire", "offensive by default",
                 "offensive-by-default", "offensive default")

    def test_non_security_routes_carry_no_offensive_assumption(self) -> None:
        for route_id in ("minimal", "runnable-local", "ai-agent-eval",
                         "dr-recovery", "product-integration"):
            proposal = wizard.build_proposal(
                wizard.normalize_inputs(_inputs(route=route_id)))
            blob = "\n".join(proposal.files.values()).lower()
            for token in self.OFFENSIVE:
                self.assertNotIn(token, blob,
                                 f"route {route_id} leaked '{token}'")


class WriteTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.env = self.tmp / "environments"
        self.env.mkdir()

    def test_write_creates_valid_pack_at_absent_target(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        created = wizard.write_proposal(proposal, str(self.env))
        self.assertEqual(Path(created), self.env / "example-pack")
        result = validate_pack(created)
        self.assertTrue(result.ok, result.errors)

    def test_write_refuses_to_overwrite_existing_target(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        target = self.env / "example-pack"
        target.mkdir()
        (target / "user-file.txt").write_text("do not clobber", encoding="utf-8")
        with self.assertRaises(wizard.WizardError):
            wizard.write_proposal(proposal, str(self.env))
        # User content untouched; no partial pack written.
        self.assertEqual((target / "user-file.txt").read_text(encoding="utf-8"),
                         "do not clobber")
        self.assertFalse((target / "pack.yaml").exists())

    def test_failed_write_leaves_no_staging_residue(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        (self.env / "example-pack").mkdir()
        with self.assertRaises(wizard.WizardError):
            wizard.write_proposal(proposal, str(self.env))
        siblings = {p.name for p in self.env.iterdir()}
        self.assertEqual(siblings, {"example-pack"})


class PreviewTests(unittest.TestCase):
    def test_preview_is_side_effect_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "environments"
            env.mkdir()
            proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
            text = wizard.render_human_preview(proposal)
            self.assertIn("pack.yaml", text)
            self.assertIn("sdl/example-pack.sdl.yaml", text)
            self.assertEqual(list(env.iterdir()), [])  # nothing created

    def test_machine_document_is_versioned_and_stable(self) -> None:
        proposal = wizard.build_proposal(wizard.normalize_inputs(_inputs()))
        doc = wizard.machine_document(proposal)
        self.assertEqual(doc["version"], wizard.WIZARD_OUTPUT_VERSION)
        self.assertEqual(doc["pack"], "example-pack")
        self.assertEqual(tuple(doc["files"]), REQUIRED_MINIMAL)


class InteractiveFlowTests(unittest.TestCase):
    def _scripted(self, answers: dict[str, str]):
        def ask(question: wizard.Question) -> str | None:
            raw = answers.get(question.key, "")
            if raw == wizard.NOT_SURE:
                return wizard.NOT_SURE
            return raw or question.default
        return ask

    def test_interactive_reaches_valid_minimal_pack(self) -> None:
        ask = self._scripted({})  # accept every default
        answers = wizard.ask_questions(wizard.route_questions("minimal"), ask)
        proposal = wizard.build_proposal(wizard.normalize_inputs(
            _inputs(answers=answers)))
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "environments"
            env.mkdir()
            created = wizard.write_proposal(proposal, str(env))
            self.assertTrue(validate_pack(created).ok)


class PersonaTaskTests(unittest.TestCase):
    """One non-developer task per primary persona (hub ADR 0003)."""

    PERSONAS = {
        "ai-researcher": ("ai-agent-eval", {}),
        "security-researcher": ("security-exercise", {}),
        "dr-resilience-practitioner": ("dr-recovery", {}),
        "product-test-engineer": ("product-integration", {}),
        "ai-engineer": ("runnable-local", {}),
    }

    def test_each_primary_persona_reaches_a_valid_pack(self) -> None:
        for persona, (route, answers) in self.PERSONAS.items():
            with self.subTest(persona=persona):
                pack_id = f"{persona}-pack"
                proposal = wizard.build_proposal(wizard.normalize_inputs({
                    "version": wizard.WIZARD_INPUT_VERSION,
                    "pack_id": pack_id,
                    "route": route,
                    "answers": answers,
                }))
                with tempfile.TemporaryDirectory() as tmp:
                    env = Path(tmp) / "environments"
                    env.mkdir()
                    created = wizard.write_proposal(proposal, str(env))
                    result = validate_pack(created)
                    self.assertTrue(result.ok, f"{persona}: {result.errors}")


class RepoRootTests(unittest.TestCase):
    def test_repo_root_accepts_gitfile_worktree_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "environments"), exist_ok=True)
            # A linked worktree carries `.git` as a gitfile, not a directory.
            with open(os.path.join(tmp, ".git"), "w", encoding="utf-8") as fh:
                fh.write("gitdir: /tmp/example.git/worktrees/example\n")
            self.assertEqual(wizard.repo_root(tmp), os.path.abspath(tmp))

    def test_repo_root_without_marker_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(wizard.WizardError):
                wizard.repo_root(tmp)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / ".git").mkdir()
        (self.tmp / "environments").mkdir()

    def test_preview_flag_writes_nothing(self) -> None:
        out = io.StringIO()
        rc = wizard.main(
            ["example-pack", "--repo", str(self.tmp), "--preview"], stdout=out)
        self.assertEqual(rc, 0)
        self.assertFalse((self.tmp / "environments" / "example-pack").exists())

    def test_non_interactive_create_and_validate(self) -> None:
        rc = wizard.main(
            ["example-pack", "--repo", str(self.tmp), "--route", "minimal", "--yes"],
            stdout=io.StringIO())
        self.assertEqual(rc, 0)
        created = self.tmp / "environments" / "example-pack"
        self.assertTrue(validate_pack(created).ok)

    def test_replay_json_roundtrip(self) -> None:
        payload = json.dumps(_inputs(pack_id="replay-pack"))
        out = io.StringIO()
        rc = wizard.main(
            ["--repo", str(self.tmp), "--replay", "-", "--json"],
            stdin=io.StringIO(payload), stdout=out)
        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        self.assertEqual(doc["version"], wizard.WIZARD_OUTPUT_VERSION)
        self.assertEqual(doc["pack"], "replay-pack")

    def test_existing_target_reports_conflict_nonzero(self) -> None:
        (self.tmp / "environments" / "example-pack").mkdir()
        rc = wizard.main(
            ["example-pack", "--repo", str(self.tmp), "--yes"],
            stdout=io.StringIO(), stderr=io.StringIO())
        self.assertNotEqual(rc, 0)


class _Tty(io.StringIO):
    """A StringIO that claims to be a terminal, to drive the interactive path."""

    def isatty(self) -> bool:  # noqa: D401
        return True


class InteractiveCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / ".git").mkdir()
        (self.tmp / "environments").mkdir()

    def test_interactive_prompts_reach_a_valid_pack(self) -> None:
        # Blank lines accept every default; the pack must still validate.
        stdin = _Tty("\n\n\n")
        rc = wizard.main(
            ["example-pack", "--repo", str(self.tmp)],
            stdin=stdin, stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(rc, 0)
        self.assertTrue(validate_pack(self.tmp / "environments" / "example-pack").ok)

    def test_terminal_ask_handles_not_sure(self) -> None:
        ask = wizard._terminal_ask(io.StringIO("?\n"), io.StringIO())
        self.assertEqual(ask(wizard._PUBLICATION_CLEARED), wizard.NOT_SURE)

    def test_json_create_emits_document_with_created_path(self) -> None:
        out = io.StringIO()
        rc = wizard.main(
            ["example-pack", "--repo", str(self.tmp), "--yes", "--json"],
            stdout=out, stderr=io.StringIO())
        self.assertEqual(rc, 0)
        doc = json.loads(out.getvalue())
        self.assertEqual(doc["created"], "environments/example-pack")

    def test_preview_json_is_versioned(self) -> None:
        out = io.StringIO()
        rc = wizard.main(
            ["example-pack", "--repo", str(self.tmp), "--preview", "--json"],
            stdout=out, stderr=io.StringIO())
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue())["version"],
                         wizard.WIZARD_OUTPUT_VERSION)

    def test_replay_from_file(self) -> None:
        payload = self.tmp / "input.json"
        payload.write_text(json.dumps(_inputs(pack_id="file-pack")),
                           encoding="utf-8")
        rc = wizard.main(
            ["--repo", str(self.tmp), "--replay", str(payload)],
            stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(rc, 0)
        self.assertTrue(
            validate_pack(self.tmp / "environments" / "file-pack").ok)

    def test_replay_invalid_json_is_usage_error(self) -> None:
        rc = wizard.main(
            ["--repo", str(self.tmp), "--replay", "-"],
            stdin=io.StringIO("{not json"), stdout=io.StringIO(),
            stderr=io.StringIO())
        self.assertEqual(rc, wizard.EXIT_USAGE)

    def test_missing_pack_id_is_usage_error(self) -> None:
        rc = wizard.main(
            ["--repo", str(self.tmp)],
            stdin=io.StringIO(""), stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(rc, wizard.EXIT_USAGE)

    def test_answer_flag_makes_publication_route_usable(self) -> None:
        rc = wizard.main(
            ["pub-pack", "--repo", str(self.tmp), "--route", "publication-ready",
             "--answer", "publication_cleared=yes", "--yes"],
            stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(rc, 0)
        self.assertTrue(
            validate_pack(self.tmp / "environments" / "pub-pack").ok)

    def test_publication_route_without_clearance_blocks(self) -> None:
        rc = wizard.main(
            ["pub-pack", "--repo", str(self.tmp), "--route", "publication-ready",
             "--yes"],
            stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(rc, wizard.EXIT_BLOCKING)
        self.assertFalse((self.tmp / "environments" / "pub-pack").exists())

    def test_answer_flag_bad_format_is_usage_error(self) -> None:
        rc = wizard.main(
            ["pub-pack", "--repo", str(self.tmp), "--answer", "noequalssign",
             "--yes"],
            stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(rc, wizard.EXIT_USAGE)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
