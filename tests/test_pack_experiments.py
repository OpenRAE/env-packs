"""Pack experiment artifact sets (issue #504, ADR 0042)."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import quote

import yaml
from raes import SDLError, admit_scenario_family, parse_sdl
from raes.canonical import canonical_sdl_digest
from raes.participant_control_context import SDLControlContextConfigurationValidator
from raes.scenario import ExpandedScenario
from raes_contracts.canonical import canonical_json_bytes, canonical_json_digest
from raes_contracts.contracts import (
    AdmittedApparatusBindingModel,
    AdmittedParticipantManifestReferenceModel,
    BackendManifestV2Model,
    ExperimentBackendReferenceModel,
    ExperimentManifestReferenceModel,
    ExperimentProcessorReferenceModel,
    ParticipantImplementationManifestModel,
    ProcessorManifestV2Model,
    TrialExecutionAuthorityModel,
)
from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel
from raes_processor.trial_compiler import compile_admitted_trial_plan
from raes_processor.trial_realization import instantiate_admitted_trial_entry

from raes_env_packs import (
    PackExperiment,
    PackExperimentError,
    derive_pack_content_manifest,
    load_pack_experiments,
    validate_pack,
    validate_pack_content_manifest,
)
from raes_env_packs import check as _check
from raes_env_packs import release as _release
from raes_env_packs import validation as _validation
from raes_env_packs.distribution import export_pack_archive, stage_pack_archive

_ROOT = Path(__file__).resolve().parents[1]
_TEMPLATE = _ROOT / "src" / "raes_env_packs" / "resources" / "template"
_SCHEMAS = _ROOT / "src" / "raes_env_packs" / "resources" / "schemas"
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "experiment-artifact-set"
_NAME = "experiment-fixture"
_SPEC = "experiments/crossed-design.exp.yaml"
_TASK = "experiments/evaluation.task.json"
_CAPTURE = "experiments/alert-capture.capture.json"
_SDL = f"sdl/{_NAME}.sdl.yaml"
_MARKER = "PRIVATE-AUTHORED-MARKER"


def build_fixture_pack(parent: Path, name: str = _NAME) -> Path:
    """Assemble the complete synthetic fixture pack in a scratch directory."""

    root = parent / name
    shutil.copytree(_TEMPLATE, root)
    for rel in ("pack.yaml", "pack.compatibility.yaml", "docs/provenance-ledger.yaml"):
        path = root / rel
        path.write_text(
            path.read_text(encoding="utf-8").replace("<name>", name), encoding="utf-8"
        )
    shutil.copytree(_FIXTURE / "pack", root, dirs_exist_ok=True)
    return root


def apparatus_context(
    experiment: PackExperiment, *, participant_manifest: Path | None = None
) -> dict[str, object]:
    """Build the caller-supplied apparatus context from the fixture manifests."""

    def load(name: str) -> object:
        return json.loads((_FIXTURE / "apparatus" / name).read_text(encoding="utf-8"))

    backend = BackendManifestV2Model.model_validate(load("backend-manifest.json"))
    processor = ProcessorManifestV2Model.model_validate(load("processor-manifest.json"))
    participant = ParticipantImplementationManifestModel.model_validate(
        load("participant-manifest.json")
        if participant_manifest is None
        else json.loads(participant_manifest.read_text(encoding="utf-8"))
    )
    envelope = BackendRealizationEnvelopeModel.model_validate(load("realization-envelope.json"))
    authority = TrialExecutionAuthorityModel.model_validate(load("execution-authority.json"))
    tail = (participant.identity.name, participant.identity.version, participant.schema_version)
    addresses = [f"agents.{name}" for name in sorted(experiment.family.agents)]
    owner = participant.configuration_registry.owner
    apparatus = AdmittedApparatusBindingModel(
        manifest_refs=[
            ExperimentManifestReferenceModel(
                ref_kind="manifest",
                ref_id=backend.identity.name,
                ref_version="backend-manifest/v2",
                ref_digest=canonical_json_digest(backend.model_dump(mode="json")),
                subject_ref=ExperimentBackendReferenceModel(
                    ref_kind="backend",
                    ref_id=backend.identity.name,
                    ref_version=backend.identity.version,
                ),
            ),
            ExperimentManifestReferenceModel(
                ref_kind="manifest",
                ref_id=processor.identity.name,
                ref_version="processor-manifest/v2",
                ref_digest=canonical_json_digest(processor.model_dump(mode="json")),
                subject_ref=ExperimentProcessorReferenceModel(
                    ref_kind="processor",
                    ref_id=processor.identity.name,
                    ref_version=processor.identity.version,
                ),
            ),
        ],
        realization_envelope=envelope.identity,
        capability_refs=sorted(experiment.experiment.apparatus_intent.required_capabilities),
        participant_manifest_refs=[
            AdmittedParticipantManifestReferenceModel(
                participant_address=address,
                implementation_name=tail[0],
                implementation_version=tail[1],
                manifest_version=tail[2],
                manifest_digest=canonical_json_digest(participant.model_dump(mode="json")),
            )
            for address in addresses
        ],
    )
    return {
        "apparatus": apparatus,
        "apparatus_manifests": {
            ("backend", backend.identity.name, backend.identity.version, "backend-manifest/v2"): backend,
            ("processor", processor.identity.name, processor.identity.version, "processor-manifest/v2"): processor,
        },
        "realization_envelope": envelope,
        "execution_authority": authority,
        "participant_manifests": {(address, *tail): participant for address in addresses},
        "participant_configuration_validators": {
            (owner.validator_id, owner.validator_version): SDLControlContextConfigurationValidator(
                experiment.family
            )
        },
    }


def compile_fixture(experiment: PackExperiment, **context: object):
    """Compile one loaded experiment with the fixture apparatus context."""

    request = experiment.compilation_request(**apparatus_context(experiment, **context))
    return request, compile_admitted_trial_plan(request)


class _FixturePack:
    """Shared scratch-pack helpers; mixed into each ``unittest.TestCase``."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = build_fixture_pack(self.tmp)

    def codes(self, **kwargs: object) -> set[str]:
        return {diagnostic.code for diagnostic in validate_pack(self.root, **kwargs).diagnostics}

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def spec(self) -> dict:
        return yaml.safe_load(self.read(_SPEC))

    def write_spec(self, document: dict) -> None:
        self.write(_SPEC, yaml.safe_dump(json.loads(json.dumps(document)), sort_keys=False))

    def edit_json(self, rel: str, change) -> None:
        document = json.loads(self.read(rel))
        change(document)
        self.write(rel, json.dumps(document, indent=2))

    def write_family(self, document: dict) -> None:
        """Write a family and re-pin every typed treatment to its new digest."""

        text = yaml.safe_dump(json.loads(json.dumps(document)), sort_keys=False)
        old = canonical_sdl_digest(admit_scenario_family(parse_sdl(self.read(_SDL)))).value
        new = canonical_sdl_digest(admit_scenario_family(parse_sdl(text))).value
        self.write(_SDL, text)
        self.write(_SPEC, self.read(_SPEC).replace(old, new))

    def only_experiment(self) -> PackExperiment:
        experiments = load_pack_experiments(self.root)
        self.assertEqual(len(experiments), 1)
        return experiments[0]


class ValidArtifactSetTests(_FixturePack, unittest.TestCase):
    def test_fixture_pack_passes_consumer_and_author_validation(self) -> None:
        result = validate_pack(self.root)
        self.assertTrue(result.ok, result.errors)
        author, _scenarios = _validation._validate_pack_for_author_ci(self.root)
        self.assertTrue(author.ok, author.errors)

    def test_loader_returns_the_admitted_artifact_set(self) -> None:
        experiment = self.only_experiment()
        self.assertEqual(experiment.path, _SPEC)
        self.assertEqual(experiment.family_path, _SDL)
        self.assertEqual(experiment.experiment.spec_id, "fixture-crossed-design")
        self.assertEqual(experiment.experiment.factorial_design.profile, "factorial-treatments-v1")
        self.assertEqual(experiment.task.task_id, "fixture-evaluation")
        self.assertEqual(list(experiment.capture_specs), ["fixture-alert-capture"])
        self.assertIsInstance(experiment.family, ExpandedScenario)
        self.assertTrue(experiment.family.semantic_validated)
        self.assertEqual(set(experiment.family.variation_points), {"sensor-layout", "drop-dir"})
        self.assertEqual(set(experiment.family.control_context_assets), {"brief-terse", "brief-rich"})
        self.assertEqual(len(experiment.experiment.run_plan.allocation.condition_assignments), 32)

    def test_unrecognized_experiment_members_are_ignored(self) -> None:
        self.write("experiments/README.md", "Notes for authors.\n")
        self.write("experiments/nested/other.exp.yaml", "not: [valid\n")
        self.assertEqual(self.codes(), set())

    def test_a_pack_without_experiments_loads_no_artifact_set(self) -> None:
        shutil.rmtree(self.root / "experiments")
        self.assertEqual(load_pack_experiments(self.root), ())

    def test_shared_tasks_and_capture_specs_join_by_identity(self) -> None:
        second = self.spec()
        second["spec_id"] = "fixture-second-design"
        text = yaml.safe_dump(json.loads(json.dumps(second)), sort_keys=False)
        self.write("experiments/second.exp.yaml", text)
        experiments = load_pack_experiments(self.root)
        self.assertEqual(
            [item.path for item in experiments], [_SPEC, "experiments/second.exp.yaml"]
        )
        self.assertEqual(experiments[0].task, experiments[1].task)

    def test_author_lane_accepts_a_composed_family(self) -> None:
        self.write(
            "sdl/modules/base.sdl.yaml",
            "name: base\nmodule:\n  id: fixture/base\n  version: 1.0.0\n"
            "  exports:\n    nodes: [anchor]\nnodes:\n  anchor:\n    type: compute\n"
            "    os: linux\n    resources: {ram: 1 gib, cpu: 1}\n",
        )
        document = yaml.safe_load(self.read(_SDL))
        composed = {"name": document["name"], "imports": [{"source": "local:modules/base.sdl.yaml", "namespace": "base"}]}
        composed.update({key: value for key, value in document.items() if key != "name"})
        text = yaml.safe_dump(composed, sort_keys=False)
        self.write(_SDL, text)
        family = _validation.parse_sdl_file(self.root / _SDL, migration_policy="accept")
        old = canonical_sdl_digest(admit_scenario_family(parse_sdl(yaml.safe_dump(document, sort_keys=False)))).value
        self.write(_SPEC, self.read(_SPEC).replace(old, canonical_sdl_digest(family).value))
        author, _scenarios = _validation._validate_pack_for_author_ci(self.root)
        self.assertTrue(author.ok, author.errors)
        self.assertIn("sdl.imports-denied", self.codes())


class CompilationTests(_FixturePack, unittest.TestCase):
    def test_every_requested_combination_compiles_with_supplied_manifests(self) -> None:
        experiment = self.only_experiment()
        request, result = compile_fixture(experiment)
        self.assertIsNotNone(result.plan, result.diagnostics)
        plan = result.plan
        self.assertEqual(len(plan.entries), 32)
        self.assertEqual(plan.profiles.treatment_profile, "factorial-treatments-v1")
        allocation = experiment.experiment.run_plan.allocation
        effects = set()
        for entry in plan.entries.values():
            levels = allocation.condition_assignments[entry.coordinate.condition_id].factor_levels
            selected = instantiate_admitted_trial_entry(
                plan=plan, plan_entry_id=entry.plan_entry_id, family=request.family
            )
            present = "sensor-9" in selected.nodes
            self.assertEqual(present, levels["sensor"] == "present")
            if present:
                jobs = [job.scheduled_job_id for job in selected.nodes["sensor-9"].runtime.scheduled_jobs]
                self.assertEqual(jobs, ["sweep"])
            self.assertEqual(selected.content["drop-manifest"].path, "/srv/outbox")
            configured = []
            for configuration in entry.participant_configurations:
                values = {value.target_id: value for value in configuration.configuration.values}
                selection = values["context.brief"].control_context_selection
                self.assertTrue(selection.asset_ref.asset_digest.startswith("sha256:"))
                configured.append(
                    (
                        configuration.participant_address,
                        values["engine.model"].value.value,
                        selection.asset_ref.asset_version,
                    )
                )
            self.assertEqual(len(configured), 2)
            effects.add((present, tuple(sorted(configured))))
        self.assertEqual(len(effects), 32)

    def test_relabelled_factors_nodes_and_targets_compile_the_same_way(self) -> None:
        renames = {
            "sensor-layout": "probe-shape",
            "sensor-9": "probe-x",
            "operator": "alpha",
            "defender": "omega",
            "engine.model": "llm.identity",
        }

        def relabel(text: str) -> str:
            for old, new in renames.items():
                text = text.replace(old, new)
            return text

        family = yaml.safe_load(relabel(self.read(_SDL)))
        document = yaml.safe_load(relabel(self.read(_SPEC)))
        factor = document["factors"]["alpha-model"]
        factor["levels"] = ["tier-a", "tier-b"]
        effects = document["factorial_design"]["level_effects"]["alpha-model"]
        effects["tier-a"], effects["tier-b"] = effects.pop("lite"), effects.pop("full")
        self.write_spec(document)
        self.write_family(family)
        relabelled = self.tmp / "participant-manifest.json"
        relabelled.write_text(
            relabel((_FIXTURE / "apparatus" / "participant-manifest.json").read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        self.assertEqual(self.codes(), set())
        experiment = self.only_experiment()
        self.assertIn("probe-shape", experiment.family.variation_points)
        _request, result = compile_fixture(experiment, participant_manifest=relabelled)
        self.assertIsNotNone(result.plan, result.diagnostics)
        self.assertEqual(len(result.plan.entries), 32)
        targets = {
            value.target_id
            for entry in result.plan.entries.values()
            for configuration in entry.participant_configurations
            for value in configuration.configuration.values
        }
        self.assertEqual(targets, {"llm.identity", "context.brief"})

    def test_an_invalid_requested_combination_rejects_the_whole_design(self) -> None:
        family = yaml.safe_load(self.read(_SDL))
        family["content"]["sensor-note"] = {
            "type": "file",
            "target": "sensor-9",
            "path": f"/var/{_MARKER}",
        }
        self.write_family(family)
        self.assertEqual(self.codes(), set())
        _request, result = compile_fixture(self.only_experiment())
        self.assertIsNone(result.plan)
        self.assertEqual(
            {diagnostic.code for diagnostic in result.diagnostics},
            {"trial-compiler.selected-scenario-rejected"},
        )
        self.assertNotIn(_MARKER, repr(result.diagnostics))

    def test_request_inputs_derive_from_the_pack_documents(self) -> None:
        experiment = self.only_experiment()
        request = experiment.compilation_request(**apparatus_context(experiment))
        refs = request.input_refs
        self.assertEqual(refs.scenario_family_ref.ref_id, "experiment-fixture")
        self.assertEqual(refs.scenario_family_ref.ref_digest, canonical_sdl_digest(experiment.family).value)
        self.assertEqual(refs.task_digest, canonical_json_digest(experiment.task.model_dump(mode="json")))
        self.assertEqual(
            refs.authoring_input_ref.ref_digest,
            canonical_json_digest(experiment.experiment.model_dump(mode="json")),
        )
        self.assertEqual(
            [(ref.ref_id, ref.ref_version) for ref in refs.capture_spec_refs],
            [("fixture-alert-capture", "1.0.0")],
        )
        self.assertEqual(
            (refs.binding_descriptor_set_ref.ref_id, refs.binding_descriptor_set_ref.ref_version),
            ("fixture-crossed-design", "1.0.0"),
        )
        self.assertEqual(dict(request.capture_specs), dict(experiment.capture_specs))


class ReleaseAndReloadTests(_FixturePack, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        pack = yaml.safe_load(self.read("pack.yaml"))
        pack["associated_artifact_manifest"] = "associated-artifacts.json"
        self.write("pack.yaml", yaml.safe_dump(pack, sort_keys=False))
        compatibility = yaml.safe_load(self.read("pack.compatibility.yaml"))
        compatibility["artifact_boundaries"]["operator_only"].append(
            {"path": "experiments", "export": "operator", "description": "Experiment artifact set."}
        )
        self.write("pack.compatibility.yaml", yaml.safe_dump(compatibility, sort_keys=False))
        self._write_content_manifest()

    def _write_content_manifest(self) -> None:
        """Declare every pack file in a RAES manifest, then bind its bytes."""

        rels = sorted(
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*")
            if path.is_file()
        )
        payload = {
            "schema_version": "associated-artifact-manifest/v1",
            "manifest_id": f"{_NAME}-associated-artifacts",
            "manifest_version": "0.1.0",
            "canonicalization_profile": "associated-artifact-set/v1",
            "scope": "scenario",
            "parent_ref": {"ref_kind": "scenario", "ref_id": _NAME},
            "artifacts": {
                f"artifact-{index}": {
                    "artifact_id": f"artifact-{index}",
                    "role": "other",
                    "media_type": "application/octet-stream",
                    "uri": f"raes-environment-pack:/{quote(rel, safe='/-._~')}",
                    "checksum": {"algorithm": "sha256", "value": "0" * 64},
                    "size_bytes": 0,
                    "created_at": "2026-10-29T00:00:00Z",
                    "source": "environment-pack-author",
                    "sensitivity": "internal",
                }
                for index, rel in enumerate(rels)
            },
            "set_digest": "sha256:" + "0" * 64,
        }
        self.write("associated-artifacts.json", json.dumps(payload))
        manifest = derive_pack_content_manifest(self.root)
        self.write("associated-artifacts.json", manifest.model_dump_json(indent=2) + "\n")

    def test_release_archive_and_reload_preserve_the_compiled_design(self) -> None:
        out = self.tmp / "out"
        _metadata, failures = _release.build_release(str(self.root), str(out), publish=True)
        self.assertEqual(failures, [])
        operator = out / f"{_NAME}-0.1.0" / "operator"
        for rel in (_SPEC, _TASK, _CAPTURE):
            self.assertEqual((operator / rel).read_bytes(), (self.root / rel).read_bytes())
        self.assertFalse((out / f"{_NAME}-0.1.0" / "participant" / "experiments").exists())
        archive = self.tmp / "pack.tar.gz"
        export_pack_archive(self.root, archive)
        staged = self.tmp / "staged" / _NAME
        staged.mkdir(parents=True)
        stage_pack_archive(archive, staged)
        validate_pack_content_manifest(staged)
        source = self.only_experiment()
        (reloaded,) = load_pack_experiments(staged)
        for field in ("experiment", "task"):
            self.assertEqual(
                canonical_json_bytes(getattr(source, field).model_dump(mode="json")),
                canonical_json_bytes(getattr(reloaded, field).model_dump(mode="json")),
            )
        self.assertEqual(
            canonical_sdl_digest(source.family).value, canonical_sdl_digest(reloaded.family).value
        )
        _request, first = compile_fixture(source)
        _request, second = compile_fixture(reloaded)
        self.assertEqual(
            canonical_json_bytes(first.plan.model_dump(mode="json")),
            canonical_json_bytes(second.plan.model_dump(mode="json")),
        )


class InvalidArtifactSetTests(_FixturePack, unittest.TestCase):
    def assert_fails(self, code: str) -> None:
        result = validate_pack(self.root)
        self.assertIn(code, {diagnostic.code for diagnostic in result.diagnostics}, result.errors)
        self.assertFalse(any(_MARKER in message for message in result.errors), result.errors)
        with self.assertRaises(PackExperimentError) as raised:
            load_pack_experiments(self.root)
        self.assertEqual(raised.exception.result, result)

    def test_unsupported_factorial_profile_is_rejected(self) -> None:
        document = self.spec()
        document["factorial_design"]["profile"] = "factorial-treatments-v9"
        document["description"] = _MARKER
        self.write_spec(document)
        self.assert_fails("experiment.spec-invalid")

    def test_malformed_and_oversized_authoring_inputs_are_rejected(self) -> None:
        for text in (
            f"spec_id: [{_MARKER}\n",
            self.read(_SPEC) + f"spec_id: {_MARKER}\n",
            self.read(_SPEC) + f"# {_MARKER * 4000}\n",
            "- a list\n",
        ):
            with self.subTest(text=text[:20]):
                self.write(_SPEC, text)
                self.assert_fails("experiment.spec-invalid")

    def test_authoring_input_bytes_and_structure_are_bounded(self) -> None:
        (self.root / _SPEC).write_bytes(b"spec_id: \xff\n")
        self.assert_fails("experiment.spec-invalid")
        self.write(_SPEC, "a:\n  b:\n    c:\n      d: e\n")
        result = validate_pack(self.root, limits=_validation.PackValidationLimits(max_yaml_depth=2))
        self.assertIn(
            ("experiment.spec-invalid", _SPEC),
            {(diagnostic.code, diagnostic.path) for diagnostic in result.diagnostics},
        )

    def test_authoring_input_over_the_metadata_bound_is_rejected(self) -> None:
        self.write(_SPEC, self.read(_SPEC) + "#" * 70_000 + "\n")
        result = validate_pack(
            self.root, limits=_validation.PackValidationLimits(max_metadata_bytes=65_536)
        )
        self.assertIn(
            ("resource.metadata-limit", _SPEC),
            {(diagnostic.code, diagnostic.path) for diagnostic in result.diagnostics},
        )

    def test_invalid_task_and_capture_documents_are_rejected(self) -> None:
        cases = (
            (_TASK, "experiment.task-invalid", '{"task_id": "a", "task_id": "b"}'),
            (_TASK, "experiment.task-invalid", "[]"),
            (_TASK, "experiment.task-invalid", '{"schema_version": "experiment-task/v1"}'),
            (_CAPTURE, "experiment.capture-invalid", "{not json"),
            (_CAPTURE, "experiment.capture-invalid", '{"capture_spec_id": "x"}'),
        )
        for rel, code, text in cases:
            with self.subTest(rel=rel, text=text):
                original = self.read(rel)
                self.write(rel, text)
                self.assert_fails(code)
                self.write(rel, original)

    def test_a_malformed_document_fails_even_when_unreferenced(self) -> None:
        self.write("experiments/unused.capture.json", '{"capture_spec_id": "unused"}')
        self.assert_fails("experiment.capture-invalid")

    def test_a_json_null_document_fails_even_when_unreferenced(self) -> None:
        for rel, code in (
            ("experiments/unused.task.json", "experiment.task-invalid"),
            ("experiments/unused.capture.json", "experiment.capture-invalid"),
        ):
            with self.subTest(rel=rel):
                self.write(rel, "null")
                self.assert_fails(code)
                (self.root / rel).unlink()

    def test_duplicate_identities_are_rejected(self) -> None:
        for rel, code in ((_TASK, "experiment.task-duplicate"), (_CAPTURE, "experiment.capture-duplicate"),
                          (_SPEC, "experiment.spec-duplicate")):
            with self.subTest(code=code):
                copy = rel.replace("experiments/", "experiments/copy-")
                self.write(copy, self.read(rel))
                self.assert_fails(code)
                (self.root / copy).unlink()

    def test_unresolved_references_are_rejected(self) -> None:
        cases = (
            ("task_ref", {"ref_kind": "task", "ref_id": "missing-task", "ref_version": "1.0.0"},
             "experiment.task-unresolved"),
            ("capture_spec_refs", [{"ref_kind": "capture-spec", "ref_id": "missing", "ref_version": "1.0.0"}],
             "experiment.capture-unresolved"),
            ("intended_scenario_ref", {"ref_kind": "scenario", "ref_id": "missing-family"},
             "experiment.scenario-unresolved"),
            ("intended_scenario_ref",
             {"ref_kind": "scenario-snapshot", "ref_id": _NAME, "ref_version": "1", "ref_digest": "sha256:" + "1" * 64},
             "experiment.scenario-unresolved"),
        )
        for key, value, code in cases:
            with self.subTest(code=code, key=key):
                original = self.read(_SPEC)
                document = self.spec()
                document[key] = value
                self.write_spec(document)
                self.assert_fails(code)
                self.write(_SPEC, original)

    def test_a_missing_family_reference_is_rejected(self) -> None:
        document = self.spec()
        del document["intended_scenario_ref"]
        del document["factors"]["sensor"]
        design = document["factorial_design"]
        design["factor_ids"].remove("sensor")
        del design["level_effects"]["sensor"]
        design["condition_bound"] = 16
        document["run_plan"]["selection_policies"] = {}
        self.write_spec(document)
        self.assert_fails("experiment.scenario-unresolved")

    def test_unversioned_references_matching_two_documents_are_ambiguous(self) -> None:
        def bump(document: dict) -> None:
            document["task_version"] = "2.0.0"

        self.write("experiments/later.task.json", self.read(_TASK))
        self.edit_json("experiments/later.task.json", bump)

        def capture_bump(document: dict) -> None:
            document["spec_version"] = "2.0.0"

        self.write("experiments/later.capture.json", self.read(_CAPTURE))
        self.edit_json("experiments/later.capture.json", capture_bump)
        document = self.spec()
        del document["task_ref"]["ref_version"]
        del document["capture_spec_refs"][0]["ref_version"]
        self.write_spec(document)
        self.assert_fails("experiment.task-ambiguous")
        self.assert_fails("experiment.capture-ambiguous")

    def test_two_capture_versions_for_one_experiment_are_ambiguous(self) -> None:
        def bump(document: dict) -> None:
            document["spec_version"] = "2.0.0"

        self.write("experiments/later.capture.json", self.read(_CAPTURE))
        self.edit_json("experiments/later.capture.json", bump)
        document = self.spec()
        document["capture_spec_refs"].append(
            {"ref_kind": "capture-spec", "ref_id": "fixture-alert-capture", "ref_version": "2.0.0"}
        )
        self.write_spec(document)
        self.assert_fails("experiment.capture-ambiguous")

    def test_two_sdl_documents_with_the_family_name_are_ambiguous(self) -> None:
        self.write("sdl/second.sdl.yaml", self.read(_SDL))
        self.assert_fails("experiment.scenario-ambiguous")

    def test_a_stale_family_pin_is_rejected(self) -> None:
        family = yaml.safe_load(self.read(_SDL))
        family["variables"]["drop_dir"]["default"] = "/srv/outbox"
        self.write(_SDL, yaml.safe_dump(family, sort_keys=False))
        self.assert_fails("experiment.treatment-invalid")

    def test_a_treatment_outside_the_point_domain_is_rejected(self) -> None:
        self.write(_SPEC, self.read(_SPEC).replace("member_id: watching", "member_id: unknown-member"))
        self.assert_fails("experiment.treatment-invalid")

    def test_a_selection_policy_outside_the_point_domain_is_rejected(self) -> None:
        document = self.spec()
        document["run_plan"]["selection_policies"]["fixed-drop-dir"]["outcome"]["value"] = "/srv/elsewhere"
        self.write_spec(document)
        self.assert_fails("experiment.selection-invalid")

    def test_a_scenario_binding_to_a_non_canonical_target_is_rejected(self) -> None:
        document = self.spec()
        document["run_plan"]["selection_policies"] = {}
        effects = document["factorial_design"]["level_effects"]["operator-model"]
        for level, value in (("lite", "/srv/inbox"), ("full", "/srv/outbox")):
            effects[level]["bindings"].append(
                {
                    "target": {
                        "plane": "scenario",
                        "scenario_family_id": _NAME,
                        "variation_point_id": "drop-dir",
                        "target_id": "variables.not-the-target",
                    },
                    "value_type": "string",
                    "value": {"kind": "literal", "value": value},
                    "owner": {
                        "contract_id": "sdl-authoring-input-v1",
                        "contract_version": "1",
                        "validator_id": "raes-selected-scenario",
                        "validator_version": "1",
                    },
                }
            )
        self.write_spec(document)
        self.assert_fails("experiment.binding-invalid")

    def test_a_family_raes_does_not_admit_is_rejected(self) -> None:
        with mock.patch.object(_validation._experiment_set, "admit_scenario_family", side_effect=SDLError("x")):
            result = validate_pack(self.root)
        self.assertIn("experiment.family-invalid", {diagnostic.code for diagnostic in result.diagnostics})


class PolicyTests(unittest.TestCase):
    def test_no_packaged_schema_restates_an_experiment_contract(self) -> None:
        for path in sorted(_SCHEMAS.glob("*")):
            with self.subTest(schema=path.name):
                self.assertNotIn("experiment", path.name)
                self.assertNotIn("experiment-", path.read_text(encoding="utf-8"))

    def test_every_experiment_code_has_an_actionable_presentation(self) -> None:
        owners = {
            "experiment.spec-invalid": "raes",
            "experiment.task-invalid": "raes",
            "experiment.capture-invalid": "raes",
            "experiment.family-invalid": "raes",
            "experiment.selection-invalid": "raes",
            "experiment.treatment-invalid": "raes",
            "experiment.binding-invalid": "raes",
            "experiment.spec-duplicate": "env-packs",
            "experiment.task-duplicate": "env-packs",
            "experiment.capture-duplicate": "env-packs",
            "experiment.task-unresolved": "env-packs",
            "experiment.task-ambiguous": "env-packs",
            "experiment.capture-unresolved": "env-packs",
            "experiment.capture-ambiguous": "env-packs",
            "experiment.scenario-unresolved": "env-packs",
            "experiment.scenario-ambiguous": "env-packs",
        }
        for code, owner in owners.items():
            with self.subTest(code=code):
                presentation = _check.presentation_for(code)
                self.assertIsNot(presentation, _check._GENERIC)
                self.assertEqual(presentation.owner, owner)
                self.assertIn(presentation.domain, {"pack", "sdl"})
                self.assertIn("experiment", presentation.explanation.lower())


if __name__ == "__main__":
    unittest.main()
