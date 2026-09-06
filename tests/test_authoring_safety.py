"""Consumer admission regressions exercised through the shared libraries."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import yaml
from raes import SDLParseError
from raes_env_packs import kits, verify, wizard
from tests.test_kits import _write_synthetic_kit


class KitInspectionSafetyTests(TestCase):
    def test_operator_policy_is_rejected_before_content_reads(self):
        from raes_env_packs import _pack_fs, authoring

        for member in ("raes-trust.yaml", "nested/RAES-TRUST.YAML"):
            with self.subTest(member=member), TemporaryDirectory() as directory:
                root = _write_synthetic_kit(Path(directory) / "kit")
                # The same otherwise valid, import-free tree is admitted first.
                kits.load_kit_release(root)
                kits._capture_pack(root)
                authoring._admit_tree(root)
                policy = root / member
                policy.parent.mkdir(exist_ok=True)
                policy.write_text("registries: {}\n")
                for admit, error in ((kits.load_kit_release, kits.KitError),
                                     (kits._capture_pack, kits.KitError),
                                     (authoring._admit_tree, _pack_fs.PackFilesystemError)):
                    with self.subTest(admit=admit.__name__), \
                         mock.patch.object(_pack_fs, "open_member", wraps=_pack_fs.open_member) as read:
                        with self.assertRaisesRegex(error, "operator files are not admitted"):
                            admit(root)
                        read.assert_not_called()

    def test_static_kit_inspection_rejects_imports_without_resolving_them(self):
        with TemporaryDirectory() as directory:
            root = _write_synthetic_kit(Path(directory) / "kit")
            module = root / "module.sdl.yaml"
            doc = yaml.safe_load(module.read_text())
            doc["imports"] = [{"source": "oci:registry.invalid/module",
                               "namespace": "remote", "version": "1.0.0"}]
            module.write_text(yaml.safe_dump(doc))
            with mock.patch("raes.module_registry.urlopen",
                            side_effect=SDLParseError("blocked test transport")) as network:
                with self.assertRaisesRegex(kits.KitError, "kit module is not valid RAES SDL") as failure:
                    kits.load_kit_release(root)
            self.assertIsInstance(failure.exception.__cause__, SDLParseError)
            self.assertIn("SDL imports require file-backed parsing", str(failure.exception.__cause__))
            self.assertEqual(network.call_count, 0)

    def test_lock_resolution_cannot_load_a_pack_supplied_registry_policy(self):
        from raes.module_registry import resolution

        with TemporaryDirectory() as directory:
            root = Path(directory)
            sdl = root / "pack.sdl.yaml"
            sdl.write_text(yaml.safe_dump({"name": "pack", "nodes": {}, "imports": [{
                "source": "oci:registry.invalid/module", "namespace": "remote", "version": "1.0.0",
            }]}))
            (root / "raes-trust.yaml").write_text(yaml.safe_dump({
                "schema_version": "raes-trust/v1",
                "registries": {"registry.invalid": {"require_signatures": False}},
            }))
            with mock.patch("raes.module_registry.urlopen",
                            side_effect=SDLParseError("blocked test transport")) as network, \
                 mock.patch.object(resolution, "load_trust_policy", wraps=resolution.load_trust_policy) as policy:
                # Bypass inventory admission deliberately to isolate the resolver
                # policy defense. Public RAES would load this policy by default.
                with self.assertRaisesRegex(kits.KitError, "RAES could not resolve the exact module lock") as failure:
                    kits._lock_bytes(root, sdl.name)
                self.assertIsInstance(failure.exception.__cause__, SDLParseError)
                self.assertIn("not allowed by trust policy", str(failure.exception.__cause__))
                policy.assert_not_called()
                network.assert_not_called()
                # Positive control: the identical input reaches our intercepted
                # transport when the explicit deny-by-default policy is omitted.
                with self.assertRaisesRegex(SDLParseError, "blocked test transport"):
                    resolution.resolve_lock_records(sdl)
                policy.assert_called_once_with(root)
                network.assert_called_once()

    def test_preparation_rejects_direct_and_transitive_escape_before_outside_read(self):
        from raes import parser
        from raes_env_packs import catalog
        from raes_env_packs.authoring import AuthoringSession
        from tests.test_kits import KIT_ID, KIT_VERSION

        with TemporaryDirectory() as directory:
            root = Path(directory)
            packs = root / "packs"
            packs.mkdir()
            pack = Path(wizard.write_proposal(wizard.build_proposal(wizard.normalize_inputs({
                "version": wizard.WIZARD_INPUT_VERSION, "pack_id": "sample-pack",
            })), str(packs)))
            kit_root = root / "catalog"
            _write_synthetic_kit(kit_root / "kits" / KIT_ID / KIT_VERSION)
            outside = _write_synthetic_kit(root / "private-kit") / "module.sdl.yaml"
            sdl = pack / "sdl/sample-pack.sdl.yaml"
            original = yaml.safe_load(sdl.read_text())
            nested = pack / "sdl/modules/intermediate.sdl.yaml"
            nested.parent.mkdir()
            # Enough parent segments to reach the real existing outside fixture
            # from any transaction staging depth, rather than a nonexistent path.
            traversal = "../" * 32 + outside.as_posix().lstrip("/")
            for transitive in (False, True):
                for source in (traversal, outside.as_posix()):
                    with self.subTest(transitive=transitive, source_kind="absolute" if source.startswith("/") else "parent"):
                        external_import = {"source": "local:" + source, "namespace": "outside", "version": KIT_VERSION}
                        document = dict(original)
                        if transitive:
                            nested.write_text(yaml.safe_dump({
                                "name": "intermediate", "nodes": {},
                                "module": {"id": "infrastructure/intermediate", "version": KIT_VERSION,
                                           "parameters": [], "exports": {"nodes": []}},
                                "imports": [external_import],
                            }))
                            document["imports"] = [{"source": "local:modules/intermediate.sdl.yaml", "namespace": "inner", "version": KIT_VERSION}]
                        else:
                            document["imports"] = [external_import]
                        sdl.write_text(yaml.safe_dump(document))
                        reads = []
                        read_source = parser.read_sdl_source
                        open_path = Path.open
                        outside_opens = []
                        def observe_open(path, *args, **kwargs):
                            if path.resolve() == outside:
                                outside_opens.append(path)
                            return open_path(path, *args, **kwargs)
                        def observe_source(path, *args, **kwargs):
                            reads.append(Path(path).resolve())
                            return read_source(path, *args, **kwargs)
                        with AuthoringSession(packs={"sample": catalog.Source("examples", "revision-1", str(pack))},
                                kit_sources={"reference": kits.KitSource("reference", "revision-1", str(kit_root))},
                                write_root=packs, allow_prepare=True) as session:
                            planned = session.call("pack_compose", {"source": "sample", "operation": "add",
                                "kit_source": "reference", "kit": KIT_ID, "version": KIT_VERSION,
                                "namespace": "web", "target_sdl": "sdl/sample-pack.sdl.yaml"})
                            self.assertEqual(planned["status"], 0, planned)
                            before = sdl.read_bytes()
                            with mock.patch.object(parser, "read_sdl_source", side_effect=observe_source), \
                                 mock.patch.object(Path, "open", new=observe_open):
                                prepared = session.call("pack_prepare", {"proposal": planned["result"]["proposal"]})
                            self.assertNotIn(outside, reads)
                            self.assertEqual(outside_opens, [])
                            self.assertEqual(prepared["status"], 1, prepared)
                            self.assertTrue(any(path.name == "sample-pack.sdl.yaml" for path in reads))
                            if transitive:
                                self.assertTrue(any(path.name == "intermediate.sdl.yaml" for path in reads))
                            self.assertEqual(sdl.read_bytes(), before)
                            self.assertFalse(Path(planned["result"]["preparation_target"]).exists())


class ReleaseEvidenceSafetyTests(TestCase):
    def test_deep_json_evidence_is_rejected_without_recursion_failure(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release.yaml").write_text("evidence:\n  sbom:\n    path: sbom.json\n")
            for depth in (100, 2000):
                (root / "sbom.json").write_text('{"nested":' * depth + '{}' + '}' * depth)
                self.assertIsNone(verify.load_release_evidence(root)[1])

    def test_release_profile_symlink_is_not_followed(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            outside = base / "outside.yaml"
            outside.write_text("marker: private-value\n")
            release = base / "release"
            release.mkdir()
            (release / "release.yaml").symlink_to(outside)
            self.assertEqual(verify.load_release_evidence(release), (None, None, None))

    def test_duplicate_profile_keys_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "release.yaml").write_text("release: {}\nrelease: {name: duplicate}\n")
            self.assertEqual(verify.load_release_evidence(root), (None, None, None))

    def test_evidence_symlink_is_not_followed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "outside.json").write_text('{"marker": "private-value"}')
            (root / "linked.json").symlink_to(root / "outside.json")
            (root / "release.yaml").write_text("evidence:\n  sbom:\n    path: linked.json\n")
            self.assertIsNone(verify.load_release_evidence(root)[1])


class WizardPreviewTests(TestCase):
    def test_preview_exposes_every_proposed_byte_before_writing(self):
        proposal = wizard.build_proposal(wizard.normalize_inputs({
            "version": wizard.WIZARD_INPUT_VERSION, "pack_id": "preview-pack",
        }))
        with TemporaryDirectory() as directory:
            target = str(Path(directory) / proposal.pack_id)
            preview = wizard.review_document(proposal, target)
            self.assertEqual(preview["target"], target)
            self.assertEqual({c["path"]: c["after"]["text"] for c in preview["changes"]},
                             proposal.files)
            self.assertFalse(Path(target).exists())

    def test_kit_review_retains_the_exact_base_and_successor(self):
        from tests.test_kit_materialization import _write_content_identified_pack
        from tests.test_kits import KIT_ID, KIT_VERSION

        with TemporaryDirectory() as directory:
            base = Path(directory)
            pack = _write_content_identified_pack(base)
            release = kits.load_kit_release(_write_synthetic_kit(
                base / "catalog" / "kits" / KIT_ID / KIT_VERSION))
            source = kits.KitSource("reference", "revision-1", str(base / "catalog"))
            proposal = kits.propose_add(pack, release, source, namespace="web",
                                        target_sdl="sdl/example-pack.sdl.yaml", parameters={})
            review = kits.review_document(proposal)
            self.assertEqual(review["target"], str(pack))
            self.assertEqual({c["path"] for c in review["changes"]}, set(proposal.changes))
            old = (pack / "sdl/example-pack.sdl.yaml").read_text()
            self.assertEqual(next(c for c in review["changes"] if c["path"] == "sdl/example-pack.sdl.yaml")
                             ["before"]["text"], old)
            kits.apply_proposal(proposal)
            for change in review["changes"]:
                path = pack / change["path"]
                if change["after"] is None:
                    self.assertFalse(path.exists())
                else:
                    self.assertEqual(path.read_text(), change["after"]["text"])
