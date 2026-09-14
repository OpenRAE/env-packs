"""Consumer-facing single-pack validation API (issue #94, ADR 0013)."""

from __future__ import annotations

import contextlib
import io
import json
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

    def test_errors_and_ok_are_derived_from_diagnostics(self) -> None:
        self.assertTrue(ValidationResult().ok)
        self.assertEqual(ValidationResult().errors, [])
        one = ValidationResult(
            (
                _validation.Diagnostic(
                    code="pack.missing",
                    path="pack.yaml",
                    field_path=None,
                    message="pack.missing: pack.yaml",
                ),
            )
        )
        self.assertFalse(one.ok)
        self.assertEqual(one.errors, ["pack.missing: pack.yaml"])

    def test_legacy_errors_construction_stays_supported(self) -> None:
        # Public back-compat (codex F1): the exported constructor still accepts
        # the historical error-string list, positionally and as errors=.
        self.assertTrue(ValidationResult(errors=[]).ok)
        keyword = ValidationResult(errors=["pack.missing: pack.yaml"])
        self.assertFalse(keyword.ok)
        self.assertEqual(keyword.errors, ["pack.missing: pack.yaml"])
        positional = ValidationResult(["provenance.type: docs/provenance-ledger.yaml:x"])
        self.assertEqual(
            positional.errors, ["provenance.type: docs/provenance-ledger.yaml:x"]
        )
        # A legacy string is parsed back into structured fields too.
        self.assertEqual(positional.diagnostics[0].code, "provenance.type")
        self.assertEqual(positional.diagnostics[0].path, "docs/provenance-ledger.yaml")

    def test_structured_location_components_are_bounded(self) -> None:
        # codex F2: path and field_path are bounded like the rendered message so
        # foreign pack input cannot exceed the diagnostic char budget.
        limits = PackValidationLimits(max_error_chars=16)
        collector = _validation._Errors(limits)
        collector.add("pack.type", path="a/" * 100, field_path="b" * 100)
        diagnostic = collector.result().diagnostics[0]
        self.assertLessEqual(len(diagnostic.path), 16)
        self.assertLessEqual(len(diagnostic.field_path), 16)
        self.assertLessEqual(len(diagnostic.message), 16)

    def test_result_exposes_structured_diagnostics(self) -> None:
        (self.root / "pack.yaml").unlink()
        result = self.validate()
        self.assertFalse(result.ok)
        missing = next(
            diagnostic
            for diagnostic in result.diagnostics
            if diagnostic.code == "pack.missing"
        )
        self.assertEqual(missing.path, "pack.yaml")
        self.assertIsNone(missing.field_path)
        self.assertEqual(missing.message, "pack.missing: pack.yaml")
        # errors stays the derived, sorted string view of the same records.
        self.assertEqual(
            result.errors, [diagnostic.message for diagnostic in result.diagnostics]
        )

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


_BOUND_SDL = "name: example-pack\nnodes:\n  target:\n    type: compute\n    os: linux\n"


def _scheme_snapshot(concepts: tuple[str, ...] = ("EX-1",)) -> dict[str, object]:
    return {
        "scheme_id": "example-scheme",
        "authority": "Example authority",
        "revision": "1",
        "source_locator": "https://example.invalid/scheme-1.json",
        "source_digest": "sha256:" + "a" * 64,
        "concepts": [{"concept_id": concept} for concept in concepts],
    }


def _binding_document(sdl_text: str, concept: str = "EX-1") -> dict[str, object]:
    from raes import parse_sdl
    from raes.external_concept_subjects import external_concept_subjects

    (subject,) = [
        item
        for item in external_concept_subjects(parse_sdl(sdl_text))
        if item.canonical_ref == "nodes.target"
    ]
    reference = [{"ref_kind": "other", "ref_id": "example"}]
    return {
        "schema_version": "external-concept-bindings/v1",
        "binding_set_id": "example-bindings",
        "binding_set_version": "1.0.0",
        "bindings": {
            "target-concept": {
                "binding_id": "target-concept",
                "subject": subject.model_dump(mode="json"),
                "scheme": {
                    key: _scheme_snapshot()[key]
                    for key in ("scheme_id", "authority", "revision", "source_locator", "source_digest")
                }
                | {"concept_id": concept},
                "assertion": {
                    "relationship_kind": "related-to",
                    "motivation": "Example classification.",
                    "motivation_basis_refs": reference,
                    "semantic_effect": "annotates",
                    "semantic_effect_basis_refs": reference,
                },
                "perspective": {
                    "asserting_party_kind": "author",
                    "asserting_party_ref": "authors.example",
                    "perspective": "author-classification",
                    "authority_basis_refs": reference,
                },
                "provenance": {
                    "asserted_at": "2026-09-13T00:00:00Z",
                    "source_refs": reference,
                },
                "confidence": {"posture": "high", "basis": "Authored."},
                "approximation": {"posture": "exact"},
                "limitations": ["Annotation only."],
                "review": {"status": "unreviewed"},
            }
        },
    }


class ConceptBindingValidationTests(PackValidationFixture):
    """External concept bindings ship beside their SDL and admit through RAES."""

    def setUp(self) -> None:
        super().setUp()
        self.sdl = self.root / "sdl" / "example.sdl.yaml"
        self.sdl.write_text(_BOUND_SDL, encoding="utf-8")
        self.bindings = self.root / "sdl" / "example.bindings.json"
        self.schemes = self.root / "sdl" / "example.schemes.json"

    def _write(self, bindings: object, schemes: object | None) -> None:
        self.bindings.write_text(json.dumps(bindings), encoding="utf-8")
        if schemes is not None:
            self.schemes.write_text(json.dumps(schemes), encoding="utf-8")

    def _binding_errors(self) -> list[str]:
        return [error for error in self.validate().errors if error.startswith("sdl.bindings")]

    def test_resolved_bindings_are_admitted(self) -> None:
        self._write(_binding_document(_BOUND_SDL), [_scheme_snapshot()])
        self.assertEqual(self._binding_errors(), [])

    def test_bindings_go_stale_when_the_sdl_changes(self) -> None:
        self._write(_binding_document(_BOUND_SDL), [_scheme_snapshot()])
        self.sdl.write_text(
            _BOUND_SDL + "  other:\n    type: compute\n    os: linux\n",
            encoding="utf-8",
        )
        self.assertEqual(
            self._binding_errors(),
            ["sdl.bindings-unresolved: sdl/example.bindings.json"],
        )

    def test_a_concept_missing_from_the_pinned_scheme_is_unresolved(self) -> None:
        self._write(_binding_document(_BOUND_SDL, "EX-2"), [_scheme_snapshot()])
        self.assertEqual(
            self._binding_errors(),
            ["sdl.bindings-unresolved: sdl/example.bindings.json"],
        )

    def test_bindings_require_their_pinned_schemes(self) -> None:
        self._write(_binding_document(_BOUND_SDL), None)
        self.assertEqual(
            self._binding_errors(),
            ["sdl.bindings-schemes-missing: sdl/example.bindings.json"],
        )

    def test_malformed_documents_fail_closed(self) -> None:
        document = _binding_document(_BOUND_SDL)
        del document["bindings"]["target-concept"]["review"]
        for bindings, schemes, expected in (
            (document, [_scheme_snapshot()], "sdl.bindings-invalid: sdl/example.bindings.json"),
            (_binding_document(_BOUND_SDL), {"not": "a list"}, "sdl.bindings-invalid: sdl/example.schemes.json"),
        ):
            with self.subTest(expected=expected):
                self._write(bindings, schemes)
                self.assertEqual(self._binding_errors(), [expected])

    def test_bindings_without_their_sdl_are_orphans(self) -> None:
        orphan = self.root / "sdl" / "missing.bindings.json"
        orphan.write_text(json.dumps(_binding_document(_BOUND_SDL)), encoding="utf-8")
        self.assertEqual(
            self._binding_errors(),
            ["sdl.bindings-orphan: sdl/missing.bindings.json"],
        )

        orphan.unlink()
        self.schemes.write_text(json.dumps([_scheme_snapshot()]), encoding="utf-8")
        self.assertEqual(
            self._binding_errors(),
            ["sdl.bindings-orphan: sdl/example.schemes.json"],
        )


_CORPUS = (
    "sdl/example.sdl.yaml:nodes.siem.runtime.security_monitoring_managers[0]"
    ".content_sets[0]"
)


class ContentSetInventoryTests(PackValidationFixture):
    """A corpus's file_count and file_refs must match the files that ship (#343)."""

    def _write_sdl(
        self,
        content_set: dict[str, object],
        content: dict[str, object] | None = None,
    ) -> None:
        document = {
            "name": "example-pack",
            "nodes": {
                "siem": {
                    "type": "vm",
                    "runtime": {
                        "security_monitoring_managers": [
                            {
                                "security_monitoring_manager_id": "siem",
                                "implementation": "wazuh",
                                "content_sets": [
                                    {"content_id": "rules", **content_set}
                                ],
                            }
                        ]
                    },
                },
                "other": {"type": "vm"},
            },
        }
        if content is not None:
            document["content"] = content
        (self.root / "sdl" / "example.sdl.yaml").write_text(
            yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
        )

    @staticmethod
    def _file_row(path: str, target: str = "siem") -> dict[str, object]:
        return {"type": "file", "target": target, "path": path, "text": "<group/>"}

    def _set_inventory(self, entries: list[dict[str, object]]) -> None:
        path = self.root / "sdl" / "example.sdl.yaml"
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document["nodes"]["siem"]["runtime"]["filesystem_inventory"] = entries
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

    def _corpus_errors(self) -> list[str]:
        return [e for e in self.validate().errors if e.startswith("content-set.")]

    def test_count_matching_supplied_refs_passes(self) -> None:
        self._write_sdl(
            {"file_count": 2, "file_refs": ["/rules/a.xml", "/rules/b.xml"]},
            {
                "a": self._file_row("/rules/a.xml"),
                "b": self._file_row("/rules/b.xml"),
            },
        )
        result = self.validate()
        self.assertTrue(result.ok, result.errors)

    def test_definition_count_declared_as_file_count_is_rejected(self) -> None:
        # The #343 defect: one XML file holding 11 rules declared as 11 files.
        self._write_sdl(
            {"file_count": 11, "file_refs": ["/rules/webapp_rules.xml"]},
            {"webapp": self._file_row("/rules/webapp_rules.xml")},
        )
        self.assertEqual(
            self._corpus_errors(),
            [f"content-set.file-count-mismatch: {_CORPUS}.file_count"],
        )

    def test_file_count_without_file_refs_is_rejected(self) -> None:
        self._write_sdl(
            {"file_count": 1, "name": "webapp_rules.xml"},
            {"webapp": self._file_row("/rules/webapp_rules.xml")},
        )
        self.assertEqual(
            self._corpus_errors(),
            [f"content-set.file-refs.missing: {_CORPUS}.file_refs"],
        )

    def test_duplicate_refs_count_once(self) -> None:
        self._write_sdl(
            {"file_count": 2, "file_refs": ["/rules/a.xml", "/rules/a.xml"]},
            {"a": self._file_row("/rules/a.xml")},
        )
        self.assertEqual(
            self._corpus_errors(),
            [f"content-set.file-count-mismatch: {_CORPUS}.file_count"],
        )

    def test_ref_nothing_supplies_is_rejected(self) -> None:
        self._write_sdl(
            {"file_count": 2, "file_refs": ["/rules/a.xml", "/rules/missing.xml"]},
            {"a": self._file_row("/rules/a.xml")},
        )
        self.assertEqual(
            self._corpus_errors(),
            [f"content-set.file-ref.unsupplied: {_CORPUS}.file_refs[1]"],
        )

    def test_file_placed_on_another_node_does_not_supply_the_ref(self) -> None:
        self._write_sdl(
            {"file_count": 1, "file_refs": ["/rules/a.xml"]},
            {"a": self._file_row("/rules/a.xml", target="other")},
        )
        self.assertEqual(
            self._corpus_errors(),
            [f"content-set.file-ref.unsupplied: {_CORPUS}.file_refs[0]"],
        )

    def test_ref_beneath_a_directory_row_is_supplied(self) -> None:
        self._write_sdl(
            {"file_count": 1, "file_refs": ["/rules/bundle/a.xml"]},
            {
                "bundle": {
                    "type": "directory",
                    "target": "siem",
                    "destination": "/rules/bundle",
                }
            },
        )
        self.assertEqual(self._corpus_errors(), [])

    def test_directory_root_does_not_supply_a_sibling_prefix(self) -> None:
        self._write_sdl(
            {"file_count": 1, "file_refs": ["/rules/bundle-extra/a.xml"]},
            {
                "bundle": {
                    "type": "directory",
                    "target": "siem",
                    "destination": "/rules/bundle",
                }
            },
        )
        self.assertEqual(
            self._corpus_errors(),
            [f"content-set.file-ref.unsupplied: {_CORPUS}.file_refs[0]"],
        )

    def test_present_inventory_file_supplies_the_ref(self) -> None:
        self._write_sdl({"file_count": 1, "file_refs": ["/rules/a.xml"]})
        self._set_inventory([{"path": "/rules/a.xml", "entry_type": "file"}])
        self.assertEqual(self._corpus_errors(), [])

    def test_image_build_destination_supplies_the_ref(self) -> None:
        self._write_sdl({"file_count": 1, "file_refs": ["/rules/a.xml"]})
        path = self.root / "sdl" / "example.sdl.yaml"
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        document["nodes"]["siem"]["source"] = {
            "name": "siem-image",
            "build": {
                "copied_sources": [
                    {"source_path": "rules/a.xml", "destination_path": "/rules/a.xml"}
                ]
            },
        }
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        self.assertEqual(self._corpus_errors(), [])

    def test_absent_or_directory_inventory_entry_does_not_supply_the_ref(self) -> None:
        for entry in (
            {"path": "/rules/a.xml", "entry_type": "file", "presence": "expected_absent"},
            {"path": "/rules/a.xml", "entry_type": "directory"},
        ):
            with self.subTest(entry=entry):
                self._write_sdl({"file_count": 1, "file_refs": ["/rules/a.xml"]})
                self._set_inventory([entry])
                self.assertEqual(
                    self._corpus_errors(),
                    [f"content-set.file-ref.unsupplied: {_CORPUS}.file_refs[0]"],
                )

    def test_unresolved_variable_ref_counts_but_is_not_resolved(self) -> None:
        self._write_sdl({"file_count": 1, "file_refs": ["${corpus_path}"]})
        self.assertEqual(self._corpus_errors(), [])

    def test_corpus_without_a_file_count_or_refs_is_not_checked(self) -> None:
        self._write_sdl({"name": "stock ruleset"})
        self.assertEqual(self._corpus_errors(), [])


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
