"""Consumer-facing single-pack validation API (issue #94, ADR 0013)."""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from raes_env_packs import PackValidationLimits, ValidationResult, validate_pack
from raes_env_packs import validation as _validation


_VALID_SDL = "\n".join(
    [
        "name: example-pack",
        "nodes:",
        "  target:",
        "    type: vm",
        "",
    ]
)


class PackValidationFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        template = (
            Path(__file__).parents[1]
            / "src" / "raes_env_packs" / "resources" / "template"
        )
        self.root = self.tmp / "example-pack"
        shutil.copytree(template, self.root)
        for rel in (
            "pack.yaml",
            "pack.compatibility.yaml",
            "docs/provenance-ledger.yaml",
        ):
            path = self.root / rel
            path.write_text(
                path.read_text(encoding="utf-8").replace("<name>", "example-pack"),
                encoding="utf-8",
            )
        (self.root / "sdl" / "example.sdl.yaml").write_text(
            _VALID_SDL, encoding="utf-8"
        )

    def validate(self, **kwargs: object) -> ValidationResult:
        return validate_pack(self.root, **kwargs)

    def _pack_yaml(self) -> dict[str, object]:
        return yaml.safe_load((self.root / "pack.yaml").read_text(encoding="utf-8"))

    def _write_pack_yaml(self, value: dict[str, object]) -> None:
        (self.root / "pack.yaml").write_text(
            yaml.safe_dump(value, sort_keys=False), encoding="utf-8"
        )


class PublicValidationTests(PackValidationFixture):
    def test_valid_pack_returns_silent_success(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = self.validate()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.errors, [])
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")

    def test_result_ok_is_derived_from_errors(self) -> None:
        self.assertTrue(ValidationResult([]).ok)
        self.assertFalse(ValidationResult(["pack.missing: pack.yaml"]).ok)

    def test_missing_pack_manifest_and_identity_fields_are_reported(self) -> None:
        (self.root / "pack.yaml").unlink()
        missing = self.validate()
        self.assertFalse(missing.ok)
        self.assertIn("pack.missing: pack.yaml", missing.errors)

        (self.root / "pack.yaml").write_text("name: example-pack\n", encoding="utf-8")
        incomplete = self.validate()
        self.assertIn("pack.identity.missing: pack.yaml:title", incomplete.errors)
        self.assertIn("pack.identity.missing: pack.yaml:version", incomplete.errors)

    def test_pack_name_must_match_directory(self) -> None:
        pack = self._pack_yaml()
        pack["name"] = "different-pack"
        self._write_pack_yaml(pack)
        result = self.validate()
        self.assertIn("pack.identity.name-mismatch: pack.yaml:name", result.errors)
        self.assertNotIn("different-pack", "\n".join(result.errors))


class ProvenanceValidationTests(PackValidationFixture):
    def test_provenance_pointer_is_required_and_contained(self) -> None:
        pack = self._pack_yaml()
        del pack["provenance_ledger"]
        self._write_pack_yaml(pack)
        self.assertIn(
            "provenance.pointer.missing: pack.yaml:provenance_ledger",
            self.validate().errors,
        )

        pack["provenance_ledger"] = "../outside.yaml"
        self._write_pack_yaml(pack)
        self.assertIn(
            "provenance.pointer.invalid: pack.yaml:provenance_ledger",
            self.validate().errors,
        )

    def test_provenance_pointer_names_the_canonical_ledger(self) -> None:
        shutil.copy(
            self.root / "docs" / "provenance-ledger.yaml",
            self.root / "docs" / "alternate.yaml",
        )
        pack = self._pack_yaml()
        pack["provenance_ledger"] = "docs/alternate.yaml"
        self._write_pack_yaml(pack)
        self.assertIn(
            "provenance.pointer.invalid: pack.yaml:provenance_ledger",
            self.validate().errors,
        )

    def test_provenance_schema_name_safety_and_review_gates_are_enforced(
        self,
    ) -> None:
        path = self.root / "docs" / "provenance-ledger.yaml"
        ledger = yaml.safe_load(path.read_text(encoding="utf-8"))
        ledger["pack"]["name"] = "secret-name"
        ledger["content_safety"]["no_real_malware"] = False
        ledger["review"]["gates"] = [
            gate for gate in ledger["review"]["gates"] if gate["gate_id"] != "licensing"
        ]
        path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

        result = self.validate()
        self.assertIn(
            "provenance.name-mismatch: docs/provenance-ledger.yaml:pack.name",
            result.errors,
        )
        self.assertIn(
            "provenance.safety.required: docs/provenance-ledger.yaml:"
            "content_safety.no_real_malware",
            result.errors,
        )
        self.assertIn(
            "provenance.review-gate.missing: docs/provenance-ledger.yaml:"
            "review.gates.licensing",
            result.errors,
        )
        self.assertNotIn("secret-name", "\n".join(result.errors))


class CompatibilityValidationTests(PackValidationFixture):
    def test_unreferenced_compatibility_manifest_is_optional(self) -> None:
        pack = self._pack_yaml()
        del pack["compatibility_manifest"]
        self._write_pack_yaml(pack)
        (self.root / "pack.compatibility.yaml").unlink()
        self.assertTrue(self.validate().ok)

    def test_referenced_compatibility_manifest_must_be_schema_valid(self) -> None:
        (self.root / "pack.compatibility.yaml").write_text(
            "schema_version: 1\npack: {}\n", encoding="utf-8"
        )
        errors = self.validate().errors
        self.assertTrue(
            any(error.startswith("compatibility.schema.required:") for error in errors),
            errors,
        )

    def test_participant_restricted_boundary_overlap_is_rejected_without_leaking(
        self,
    ) -> None:
        manifest = yaml.safe_load(
            (self.root / "pack.compatibility.yaml").read_text(encoding="utf-8")
        )
        # Participant root "docs" is an ancestor of the restricted operator path
        # docs/golden-readiness-checklist.md shipped in the template manifest.
        manifest["artifact_boundaries"]["participant_visible"] = [
            {"path": "docs", "export": "public", "description": "x"},
        ]
        (self.root / "pack.compatibility.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
        result = self.validate()
        self.assertFalse(result.ok)
        blob = "\n".join(result.errors)
        self.assertIn(
            "compatibility.boundary-overlap: pack.compatibility.yaml:"
            "artifact_boundaries.participant_visible[0].path",
            blob,
        )
        # The restricted descendant path value must never enter the result.
        self.assertNotIn("golden-readiness-checklist", blob)


class BoundaryOverlapUnitTests(unittest.TestCase):
    """Pure participant-vs-restricted overlap invariant (issue #112)."""

    def _fields(self, boundaries: object) -> list[str]:
        return _validation._boundary_overlaps(boundaries)

    def test_equal_path_across_participant_and_oracle_is_flagged(self) -> None:
        self.assertEqual(
            self._fields(
                {
                    "participant_visible": [{"path": "docs/shared.md", "export": "public"}],
                    "oracle_only": [{"path": "docs/shared.md", "export": "private"}],
                }
            ),
            ["artifact_boundaries.participant_visible[0].path"],
        )

    def test_participant_ancestor_of_restricted_is_flagged(self) -> None:
        self.assertEqual(
            len(
                self._fields(
                    {
                        "participant_visible": [{"path": "docs", "export": "public"}],
                        "oracle_only": [{"path": "docs/oracle.md", "export": "private"}],
                    }
                )
            ),
            1,
        )

    def test_participant_descendant_of_restricted_is_flagged(self) -> None:
        self.assertEqual(
            len(
                self._fields(
                    {
                        "participant_visible": [{"path": "docs/guide.md", "export": "public"}],
                        "operator_only": [{"path": "docs/", "export": "operator"}],
                    }
                )
            ),
            1,
        )

    def test_trailing_slash_is_path_equivalent(self) -> None:
        self.assertEqual(
            len(
                self._fields(
                    {
                        "participant_visible": [{"path": "docs", "export": "public"}],
                        "oracle_only": [{"path": "docs/", "export": "private"}],
                    }
                )
            ),
            1,
        )

    def test_backslash_is_treated_as_a_path_separator(self) -> None:
        # A Windows-style separator must not smuggle a restricted descendant
        # past the guard: docs\\secret.yaml is under the participant root docs,
        # and Windows filesystem APIs would stage it into the participant tree.
        self.assertEqual(
            len(
                self._fields(
                    {
                        "participant_visible": [{"path": "docs", "export": "public"}],
                        "oracle_only": [{"path": "docs\\secret.yaml", "export": "private"}],
                    }
                )
            ),
            1,
        )
        # Same when the backslash is on the participant declaration.
        self.assertEqual(
            self._fields(
                {
                    "participant_visible": [{"path": "docs\\guide.md", "export": "public"}],
                    "operator_only": [{"path": "docs", "export": "operator"}],
                }
            ),
            ["artifact_boundaries.participant_visible[0].path"],
        )

    def test_sibling_prefix_is_not_a_false_positive(self) -> None:
        self.assertEqual(
            self._fields(
                {
                    "participant_visible": [{"path": "docs", "export": "public"}],
                    "oracle_only": [{"path": "docs2", "export": "private"}],
                }
            ),
            [],
        )

    def test_operator_only_group_is_restricted_regardless_of_export(self) -> None:
        self.assertEqual(
            len(
                self._fields(
                    {
                        "participant_visible": [{"path": "shared/brief.md", "export": "public"}],
                        "operator_only": [{"path": "shared/brief.md", "export": "commercial"}],
                    }
                )
            ),
            1,
        )

    def test_restricted_export_in_any_group_is_restricted(self) -> None:
        self.assertEqual(
            len(
                self._fields(
                    {
                        "participant_visible": [{"path": "notes.md", "export": "public"}],
                        "commercial": [{"path": "notes.md", "export": "operator"}],
                    }
                )
            ),
            1,
        )

    def test_disjoint_boundaries_are_clean(self) -> None:
        self.assertEqual(
            self._fields(
                {
                    "participant_visible": [{"path": "public/brief.md", "export": "public"}],
                    "operator_only": [{"path": "operator/runbook.md", "export": "operator"}],
                    "oracle_only": [{"path": "restricted/answers.yaml", "export": "private"}],
                    "commercial": [{"path": "profiles/", "export": "commercial"}],
                }
            ),
            [],
        )

    def test_restricted_versus_restricted_is_out_of_scope(self) -> None:
        # participant-vs-restricted only; operator/commercial-vs-oracle is not
        # broadened into universal cross-tier disjointness (ADR 0013).
        self.assertEqual(
            self._fields(
                {
                    "participant_visible": [{"path": "public/brief.md", "export": "public"}],
                    "commercial": [{"path": "docs/", "export": "commercial"}],
                    "oracle_only": [{"path": "docs/answers.yaml", "export": "private"}],
                }
            ),
            [],
        )

    def test_malformed_rows_do_not_raise(self) -> None:
        self.assertEqual(
            self._fields(
                {
                    "participant_visible": [
                        "not-a-dict",
                        {"path": 123},
                        {"no_path": True},
                        {"path": "docs/x.md", "export": "public"},
                    ],
                    "oracle_only": [{"path": "docs/x.md", "export": "private"}, {"bad": 1}],
                }
            ),
            ["artifact_boundaries.participant_visible[3].path"],
        )

    def test_non_dict_boundaries_return_empty(self) -> None:
        self.assertEqual(self._fields(None), [])
        self.assertEqual(self._fields([]), [])
        self.assertEqual(self._fields({}), [])


class SdlValidationTests(PackValidationFixture):
    def test_every_direct_sdl_document_is_parsed_through_raes(self) -> None:
        (self.root / "sdl" / "broken.sdl.yaml").write_text(
            "name: example-pack\nnodes:\n  target: {}\n", encoding="utf-8"
        )
        result = self.validate()
        self.assertIn("sdl.invalid: sdl/broken.sdl.yaml", result.errors)

    def test_missing_direct_sdl_document_fails_closed(self) -> None:
        (self.root / "sdl" / "example.sdl.yaml").unlink()
        self.assertIn("sdl.missing: sdl", self.validate().errors)

    def test_imports_fail_closed_without_network_or_cache(self) -> None:
        path = self.root / "sdl" / "example.sdl.yaml"
        path.write_text(
            "name: example-pack\nimports:\n  - oci://registry.invalid/module:latest\nnodes: {}\n",
            encoding="utf-8",
        )
        with mock.patch("urllib.request.urlopen") as urlopen, mock.patch(
            "socket.create_connection", side_effect=AssertionError("network reached")
        ):
            result = self.validate()
        self.assertIn("sdl.imports-denied: sdl/example.sdl.yaml", result.errors)
        urlopen.assert_not_called()
        self.assertFalse((self.root / "sdl" / ".raes").exists())


class ValidationBoundaryTests(PackValidationFixture):
    def test_duplicate_yaml_keys_are_rejected_without_echoing_values(self) -> None:
        # A stand-in for confidential pack content. It is named for what it is
        # rather than called `secret`: CodeQL's py/clear-text-storage-sensitive-data
        # heuristic keys on the *variable name*, and that name made it report this
        # fixture as stored sensitive data. That was a false positive -- the value
        # is a literal sentinel written to a per-test temp directory, and the
        # assertion below is precisely that it never reaches the output -- so the
        # fix is an accurate name, not a suppression (#142).
        never_echoed = "participant-value-that-must-not-appear"
        (self.root / "pack.yaml").write_text(
            f"name: example-pack\nname: {never_echoed}\ntitle: x\nversion: 1\n",
            encoding="utf-8",
        )
        result = self.validate()
        self.assertIn("yaml.duplicate-key: pack.yaml", result.errors)
        self.assertNotIn(never_echoed, "\n".join(result.errors))

    def test_symlink_hardlink_and_special_file_members_fail_closed(self) -> None:
        outside = self.tmp / "outside"
        outside.write_text("outside", encoding="utf-8")
        os.symlink(outside, self.root / "linked")
        self.assertIn("filesystem.unsafe-member", "\n".join(self.validate().errors))
        (self.root / "linked").unlink()

        os.link(self.root / "README.md", self.root / "linked")
        self.assertIn("filesystem.unsafe-member", "\n".join(self.validate().errors))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation is not supported")
    def test_fifo_member_fails_closed(self) -> None:
        os.mkfifo(self.root / "pipe")
        self.assertEqual(self.validate().errors, ["filesystem.unsafe-member"])

    def test_metadata_and_member_limit_errors_are_classified(self) -> None:
        metadata = self.validate(limits=PackValidationLimits(max_metadata_bytes=8))
        self.assertTrue(any(error.startswith("resource.metadata-limit:")
                            for error in metadata.errors), metadata.errors)

        members = self.validate(limits=PackValidationLimits(max_members=2))
        self.assertEqual(members.errors, ["resource.member-limit"])

    def test_yaml_depth_and_alias_expansion_are_bounded(self) -> None:
        nested = "value"
        for _ in range(8):
            nested = f"[{nested}]"
        (self.root / "pack.yaml").write_text(
            f"name: example-pack\ntitle: {nested}\nversion: x\n",
            encoding="utf-8",
        )
        depth = self.validate(limits=PackValidationLimits(max_yaml_depth=4))
        self.assertIn("yaml.invalid: pack.yaml", depth.errors)

        (self.root / "pack.yaml").write_text(
            "name: example-pack\ntitle: &title Example\nversion: *title\n",
            encoding="utf-8",
        )
        aliases = self.validate(
            limits=PackValidationLimits(max_yaml_aliases=1, max_yaml_nodes=5)
        )
        self.assertIn("yaml.invalid: pack.yaml", aliases.errors)

    def test_metadata_member_and_error_limits_are_bounded(self) -> None:
        limits = PackValidationLimits(
            max_metadata_bytes=8, max_members=2, max_errors=2
        )
        result = self.validate(limits=limits)
        self.assertFalse(result.ok)
        self.assertLessEqual(len(result.errors), 2)
        self.assertTrue(
            all(len(error) <= limits.max_error_chars for error in result.errors)
        )

    def test_invalid_root_is_a_result_not_an_exception(self) -> None:
        result = validate_pack(self.tmp / "missing")
        self.assertEqual(result.errors, ["filesystem.invalid-root"])

    def test_consumer_api_does_not_invoke_git_or_subprocess(self) -> None:
        with (
            mock.patch("subprocess.run", side_effect=AssertionError("subprocess reached")),
            mock.patch("subprocess.check_output", side_effect=AssertionError("git reached")),
            mock.patch("subprocess.Popen", side_effect=AssertionError("subprocess reached")),
            mock.patch("os.system", side_effect=AssertionError("shell reached")),
        ):
            self.assertTrue(self.validate().ok)


if __name__ == "__main__":
    unittest.main()
