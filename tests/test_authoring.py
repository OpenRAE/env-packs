"""The host-scoped authoring adapter uses real pack and RAES authorities."""
import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

from raes_env_packs import catalog, check, wizard
from raes_env_packs.validation import validate_pack


class AuthoringTests(TestCase):
    def setUp(self):
        from raes_env_packs.authoring import AuthoringSession

        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packs = self.root / "packs"
        self.packs.mkdir()
        proposal = wizard.build_proposal(wizard.normalize_inputs({
            "version": wizard.WIZARD_INPUT_VERSION, "pack_id": "sample-pack",
        }))
        self.pack = Path(wizard.write_proposal(proposal, str(self.packs)))
        self.source = catalog.Source("examples", "revision-1", str(self.pack))
        self.session = AuthoringSession(packs={"sample": self.source}, write_root=self.packs,
                                        allow_writes=True, allow_prepare=True)
        self.addCleanup(self.session.close)

    def call(self, name, **arguments):
        return self.session.call(name, arguments)

    def test_validate_matches_the_cli_document(self):
        result = self.call("pack_validate", source="sample")
        self.assertEqual(result["status"], 0)
        expected = json.loads(check.render_json(check.build_report(validate_pack(self.pack), "sample-pack")))
        self.assertEqual(result["result"], expected)

    def test_card_and_search_use_the_catalog_projection(self):
        expected, _ = catalog.build_catalog([self.source], as_of="2026-09-06")
        for name, extra in (("pack_inspect", {"source": "sample"}),
                            ("pack_compatibility_card", {"source": "sample"}),
                            ("pack_search", {"query": "sample"})):
            result = self.call(name, as_of="2026-09-06", **extra)
            self.assertEqual(result["status"], 0, result)
            self.assertEqual(result["result"]["catalog"], json.loads(catalog.render_json(expected)))

    def test_unregistered_source_and_unknown_fields_are_refused(self):
        for arguments in ({"source": "../outside"}, {"source": "sample", "approved": True}):
            self.assertEqual(self.session.call("pack_validate", arguments)["status"], 2)

    def test_preview_then_apply_writes_exactly_the_reviewed_content(self):
        result = self.call("pack_scaffold", inputs={"version": wizard.WIZARD_INPUT_VERSION,
                                                    "pack_id": "new-pack"})
        self.assertEqual(result["status"], 0, result)
        review = result["result"]
        self.assertFalse((self.packs / "new-pack").exists())
        self.assertEqual(review["target"], str(self.packs / "new-pack"))
        applied = self.call("pack_apply", proposal=review["proposal"])
        self.assertEqual(applied["status"], 0, applied)
        for change in review["changes"]:
            self.assertEqual((self.packs / "new-pack" / change["path"]).read_text(),
                             change["after"]["text"])
        self.assertEqual(self.call("pack_apply", proposal=review["proposal"]), applied)

    def test_approval_handle_does_not_cross_sessions_or_grant_host_permission(self):
        from raes_env_packs.authoring import AuthoringSession

        preview = self.call("pack_scaffold", inputs={"version": wizard.WIZARD_INPUT_VERSION,
                                                     "pack_id": "new-pack"})["result"]
        with AuthoringSession(write_root=self.packs) as other:
            self.assertEqual(other.call("pack_apply", {"proposal": preview["proposal"]})["status"], 2)
            own = other.call("pack_scaffold", {"inputs": {"version": wizard.WIZARD_INPUT_VERSION,
                                                          "pack_id": "other-pack"}})["result"]
            self.assertEqual(other.call("pack_apply", {"proposal": own["proposal"]})["status"], 2)
        self.assertFalse((self.packs / "new-pack").exists())
        self.assertFalse((self.packs / "other-pack").exists())

    def test_target_conflict_preserves_the_existing_tree(self):
        result = self.call("pack_scaffold", inputs={"version": wizard.WIZARD_INPUT_VERSION,
                                                    "pack_id": "new-pack"})
        target = self.packs / "new-pack"
        target.mkdir()
        (target / "author.txt").write_text("keep me")
        self.assertEqual(self.call("pack_apply", proposal=result["result"]["proposal"])["status"], 1)
        self.assertEqual((target / "author.txt").read_text(), "keep me")

    def test_session_and_output_limits_never_create_a_target(self):
        inputs = {"version": wizard.WIZARD_INPUT_VERSION, "pack_id": "limited-pack"}
        with mock.patch("raes_env_packs.authoring._MAX_OUTPUT", 1025):
            self.assertEqual(self.call("pack_scaffold", inputs=inputs)["status"], 2)
        self.assertEqual(len(self.session._pending), 0)
        with mock.patch("raes_env_packs.authoring._MAX_PROPOSALS", 1):
            self.assertEqual(self.call("pack_scaffold", inputs=inputs)["status"], 0)
            self.assertEqual(self.call("pack_scaffold", inputs=inputs)["status"], 2)
        self.assertFalse((self.packs / "limited-pack").exists())
        self.session.close()
        self.assertEqual(self.call("pack_examples")["status"], 2)

    def test_publication_plan_shares_effects_without_claiming_verification(self):
        from raes_env_packs import distribution
        from raes_env_packs.authoring import AuthoringSession

        root = self.root / "release"
        root.mkdir()
        (root / "release.yaml").write_text("release:\n  source_set:\n    set_digest: sha256:" + "a" * 64 + "\nevidence: {}\n")
        args = {"source": "release", "repository": "registry.invalid/example/pack", "reference": "1.0.0"}
        expected = distribution.plan_publish(str(root), selector=distribution.Selector(
            repository=args["repository"], reference=args["reference"]))
        before = (root / "release.yaml").read_bytes()
        with AuthoringSession(releases={"release": str(root)}) as session, \
             mock.patch("socket.socket.connect", side_effect=AssertionError("network")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("process")):
            result = session.call("pack_publication_plan", args)
            self.assertEqual(result["status"], 0, result)
            self.assertEqual(result["result"]["effects"], json.loads(expected.render_json())["effects"])
            self.assertFalse(result["result"]["publication_verified"])
            self.assertEqual(result["result"]["readiness"], "not-assessed")
            for repository in ("https://registry.invalid/pack", "user:pass@registry.invalid/pack", "registry.invalid/../pack"):
                self.assertEqual(session.call("pack_publication_plan", {**args, "repository": repository})["status"], 2)
        self.assertEqual((root / "release.yaml").read_bytes(), before)

    def test_malformed_release_identity_is_content_failure_not_tool_failure(self):
        from raes_env_packs.authoring import AuthoringSession

        root = self.root / "release"
        root.mkdir()
        with AuthoringSession(releases={"release": str(root)}) as session:
            for fragment in ("null", "[]", "{source_set: null}", "{source_set: {set_digest: 12}}"):
                (root / "release.yaml").write_text("release: " + fragment + "\nevidence: {}\n")
                result = session.call("pack_publication_plan", {"source": "release", "repository": "registry.invalid/pack", "reference": "1"})
                self.assertEqual(result["status"], 1, result)

    def test_recovery_metadata_is_bounded_even_on_exception_path(self):
        from raes_env_packs.kits import KitRecoveryError

        preview = self.call("pack_scaffold", inputs={"version": wizard.WIZARD_INPUT_VERSION, "pack_id": "recovery-pack"})["result"]
        for path in (self.packs / ".recovery-123", self.packs / ("x" * 5000)):
            with mock.patch("raes_env_packs.wizard.write_proposal", side_effect=KitRecoveryError(path)):
                result = self.call("pack_apply", proposal=preview["proposal"])
            self.assertEqual(result["status"], 3)
            if len(str(path)) < 4096:
                self.assertEqual(result["result"]["recovery_path"], str(path))

    def test_read_tools_cannot_execute_or_connect_or_read_secret_members(self):
        from raes_env_packs import _pack_fs

        (self.pack / "sdl" / "validate_custom.py").write_text("raise RuntimeError('executed')")
        original = _pack_fs.open_member
        def guard(fd, rel, **kwargs):
            self.assertNotIn(".env", rel)
            return original(fd, rel, **kwargs)
        with mock.patch("socket.socket.connect", side_effect=AssertionError("network")), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("process")), \
             mock.patch.object(_pack_fs, "open_member", side_effect=guard):
            self.assertEqual(self.call("pack_validate", source="sample")["status"], 0)
            (self.pack / ".env").write_text("private fixture")
            self.assertEqual(self.call("pack_validate", source="sample")["status"], 1)

    def test_sdl_services_delegate_to_real_raes(self):
        from raes.language_service import language_completions

        text = "name: sample\nnodes: {}\n"
        result = self.call("pack_sdl", operation="completion", content=text)
        self.assertEqual(result["result"]["items"], language_completions(text)["items"])
        for operation in ("parse", "diagnostics", "format", "compile", "plan"):
            result = self.call("pack_sdl", operation=operation, content=text)
            self.assertEqual(result["status"], 0, (operation, result))
            self.assertEqual(result["authority"], "raes")

    def test_malformed_input_never_leaks_values(self):
        for args in ({"source": ["SENSITIVE-SENTINEL"]},
                     {"source": "SENSITIVE-SENTINEL"},
                     {"source": "sample", "extra": "SENSITIVE-SENTINEL"}):
            result = self.session.call("pack_validate", args)
            self.assertNotIn("SENSITIVE-SENTINEL", json.dumps(result))
            self.assertEqual(result["status"], 2)

    def test_programming_failures_remain_tool_failures(self):
        for failure in (TypeError, ValueError, KeyError):
            with mock.patch("raes_env_packs.validation.validate_pack",
                            side_effect=failure("SENSITIVE-SENTINEL")):
                result = self.call("pack_validate", source="sample")
            self.assertEqual(result["status"], 3)
            self.assertNotIn("SENSITIVE-SENTINEL", json.dumps(result))

    def test_secret_arguments_and_large_or_unknown_version_inputs_are_refused(self):
        for args in ({"inputs": {"version": wizard.WIZARD_INPUT_VERSION, "pack_id": "secret-pack",
                                  "answers": {"description": "ghp_" + "a" * 36}}},
                     {"inputs": {"version": wizard.WIZARD_INPUT_VERSION, "pack_id": "x" * 70000}},
                     {"version": "raes-pack-authoring/v99", "inputs": {}}):
            self.assertEqual(self.session.call("pack_scaffold", args)["status"], 2)

    def test_nested_secret_parameter_is_refused_before_preparation(self):
        with mock.patch.object(self.session, "_compose", side_effect=AssertionError("must reject before dispatch")):
            result = self.call("pack_compose", source="sample", operation="add", parameters={"password": "private-value"})
        self.assertEqual(result["status"], 2)
        self.assertNotIn("private-value", json.dumps(result))

    def test_sdl_error_keeps_source_range_without_echoing_authored_value(self):
        result = self.call("pack_sdl", operation="diagnostics", content="name: [unterminated SENSITIVE-SENTINEL")
        self.assertEqual(result["status"], 1)
        self.assertNotIn("SENSITIVE-SENTINEL", json.dumps(result))
        self.assertTrue(result["result"]["diagnostics"])
        self.assertIn("range", result["result"]["diagnostics"][0])

    def test_symlink_target_cannot_redirect_a_scaffold(self):
        preview = self.call("pack_scaffold", inputs={"version": wizard.WIZARD_INPUT_VERSION,
                                                     "pack_id": "linked-pack"})["result"]
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (self.packs / "linked-pack").symlink_to(elsewhere, target_is_directory=True)
        self.assertNotEqual(self.call("pack_apply", proposal=preview["proposal"])["status"], 0)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_preparation_then_review_then_composition(self):
        from raes_env_packs import kits
        from tests.test_kits import KIT_ID, KIT_VERSION, _write_synthetic_kit
        from raes_env_packs.authoring import AuthoringSession

        kit_root = self.root / "catalog"
        _write_synthetic_kit(kit_root / "kits" / KIT_ID / KIT_VERSION)
        source = kits.KitSource("reference", "revision-1", str(kit_root))
        with AuthoringSession(packs={"sample": self.source}, kit_sources={"reference": source},
                              write_root=self.packs, allow_writes=True, allow_prepare=True) as session:
            before = {p.relative_to(self.pack).as_posix(): p.read_bytes()
                      for p in self.pack.rglob("*") if p.is_file()}
            planned = session.call("pack_compose", {"source": "sample", "operation": "add",
                "kit_source": "reference", "kit": KIT_ID, "version": KIT_VERSION,
                "namespace": "web", "target_sdl": "sdl/sample-pack.sdl.yaml"})
            self.assertEqual(planned["status"], 0, planned)
            for name, args in (("pack_kits", {"source": "reference"}),
                               ("pack_kit_inspect", {"source": "reference", "kit": KIT_ID, "version": KIT_VERSION})):
                self.assertEqual(session.call(name, args)["status"], 0)
            self.assertFalse(Path(planned["result"]["preparation_target"]).exists())
            with mock.patch("socket.socket.connect", side_effect=AssertionError("network")), \
                 mock.patch("subprocess.Popen", side_effect=AssertionError("process")):
                prepared = session.call("pack_prepare", {"proposal": planned["result"]["proposal"]})
            self.assertEqual(prepared["status"], 0, prepared)
            self.assertEqual(before, {p.relative_to(self.pack).as_posix(): p.read_bytes()
                                     for p in self.pack.rglob("*") if p.is_file()})
            applied = session.call("pack_apply", {"proposal": prepared["result"]["proposal"]})
            self.assertEqual(applied["status"], 0, applied)
            self.assertTrue((self.pack / "kit.materializations.json").is_file())
            self.assertTrue((self.pack / "sdl/raes.lock.json").is_file())
            for change in prepared["result"]["changes"]:
                if change["after"] is not None:
                    self.assertEqual((self.pack / change["path"]).read_text(), change["after"]["text"])
            # Consumer import denial retains its separate meaning after author composition.
            checked = session.call("pack_validate", {"source": "sample"})
            self.assertEqual(checked["status"], 1)
            self.assertIn("sdl.imports-denied", [d["code"] for d in checked["result"]["diagnostics"]])
            for operation, materialization in (("update", "web"), ("replace", "web"), ("remove", "api")):
                args = {"source": "sample", "operation": operation, "materialization": materialization}
                if operation != "remove":
                    args.update(kit_source="reference", kit=KIT_ID, version=KIT_VERSION,
                                parameters={"hostname": "changed.example"})
                if operation == "replace":
                    args.update(namespace="api", target_sdl="sdl/sample-pack.sdl.yaml")
                plan = session.call("pack_compose", args)
                self.assertEqual(plan["status"], 0, plan)
                prepared = session.call("pack_prepare", {"proposal": plan["result"]["proposal"]})
                self.assertEqual(prepared["status"], 0, prepared)
                self.assertEqual(session.call("pack_prepare", {"proposal": plan["result"]["proposal"]}), prepared)
                applied = session.call("pack_apply", {"proposal": prepared["result"]["proposal"]})
                self.assertEqual(applied["status"], 0, (operation, applied))
                for change in prepared["result"]["changes"]:
                    path = self.pack / change["path"]
                    if change["after"] is None:
                        self.assertFalse(path.exists())
                    else:
                        self.assertEqual(path.read_text(), change["after"]["text"])
            self.assertEqual(session.call("pack_validate", {"source": "sample"})["status"], 0)
