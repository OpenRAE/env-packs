"""Admission of a pack's RAES experiment artifact set (issue #504, ADR 0042).

RAES owns every experiment contract, selection rule, and trial compiler. This
module only joins already-read pack documents by their RAES identities and
hands each join to the RAES owning validator. It reads no file and reports
failures as stable codes through the caller's bounded collector.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import TypeVar

from raes import SDLError, admit_scenario_family
from raes.canonical import canonical_sdl_digest
from raes.experiment_selection import validate_experiment_selection_against_family
from raes.scenario import ExpandedScenario, Scenario
from raes.selected_scenario import ExpandedScenarioBindingTargetResolver
from raes_contracts.canonical import canonical_json_digest
from raes_contracts.contracts import (
    AdmittedApparatusBindingModel,
    AdmittedTrialPlanInputRefsModel,
    ExperimentBindingDescriptorSetModel,
    ExperimentCaptureSpecModel,
    ExperimentFactorialTreatmentDesignModel,
    ExperimentReferenceModel,
    ExperimentScenarioFamilyReferenceModel,
    ExperimentSpecModel,
    ExperimentTaskModel,
    ParticipantImplementationManifestModel,
    ScenarioBindingTargetModel,
    TrialCompilationLimitsModel,
    TrialExecutionAuthorityModel,
)
from raes_contracts.experiment_bindings import (
    ApparatusManifest,
    ApparatusManifestKey,
    ParticipantManifestKey,
    validate_experiment_binding_targets,
)
from raes_contracts.experiment_spec import ExperimentSpecValidationError, parse_experiment_spec
from raes_contracts.participant_configuration import ParticipantConfigurationValidator
from raes_contracts.realization_envelope import BackendRealizationEnvelopeModel
from raes_processor.trial_compiler import TrialCompilationRequest

EXPERIMENTS_DIR = "experiments"
SPEC_SUFFIX = ".exp.yaml"
TASK_SUFFIX = ".task.json"
CAPTURE_SUFFIX = ".capture.json"

# RAES names the expanded family phase in its scenario-family reference.
_FAMILY_REF_VERSION = "expanded-scenario-family/v1"

AddError = Callable[[str, str], None]
_Document = TypeVar("_Document")


@dataclass(frozen=True)
class PackExperiment(object):
    """One admitted experiment and the pack documents it references.

    Every model is the RAES-validated value from one static validation pass.
    ``family`` is the admitted ``ExpandedScenario`` named by the experiment's
    ``intended_scenario_ref``. ``capture_specs`` holds only the capture
    specifications the experiment references, keyed by their RAES id.
    """

    path: str
    experiment: ExperimentSpecModel
    task: ExperimentTaskModel
    capture_specs: Mapping[str, ExperimentCaptureSpecModel]
    family: ExpandedScenario
    family_path: str

    def compilation_request(
        self,
        *,
        apparatus: AdmittedApparatusBindingModel,
        apparatus_manifests: Mapping[ApparatusManifestKey, ApparatusManifest],
        realization_envelope: BackendRealizationEnvelopeModel,
        execution_authority: TrialExecutionAuthorityModel,
        participant_manifests: Mapping[
            ParticipantManifestKey, ParticipantImplementationManifestModel
        ]
        | None = None,
        participant_configuration_validators: Mapping[
            tuple[str, str], ParticipantConfigurationValidator
        ]
        | None = None,
        limits: TrialCompilationLimitsModel | None = None,
    ) -> TrialCompilationRequest:
        """Join this artifact set with trusted apparatus context for RAES.

        The input references derive from the pack documents themselves. The
        binding descriptor set is part of the authoring input, so its
        reference carries the authoring input's id and version. The caller
        supplies and is responsible for the apparatus context.
        """

        return TrialCompilationRequest(
            family=self.family,
            experiment=self.experiment,
            task=self.task,
            input_refs=self._input_refs(),
            apparatus=apparatus,
            realization_envelope=realization_envelope,
            execution_authority=execution_authority,
            apparatus_manifests=apparatus_manifests,
            capture_specs=self.capture_specs,
            participant_manifests=participant_manifests or {},
            limits=limits or TrialCompilationLimitsModel(),
            participant_configuration_validators=participant_configuration_validators or {},
        )

    def _input_refs(self) -> AdmittedTrialPlanInputRefsModel:
        """Pin every pack document by its canonical RAES digest."""

        experiment = self.experiment
        descriptors = experiment.binding_descriptors
        return AdmittedTrialPlanInputRefsModel(
            authoring_input_ref=ExperimentReferenceModel(
                ref_kind="authoring-input",
                ref_id=experiment.spec_id,
                ref_version=experiment.spec_version,
                ref_digest=canonical_json_digest(experiment.model_dump(mode="json")),
            ),
            task_ref=experiment.task_ref,
            task_digest=canonical_json_digest(self.task.model_dump(mode="json")),
            scenario_family_ref=ExperimentScenarioFamilyReferenceModel(
                ref_kind="scenario-family",
                ref_id=self.family.name,
                ref_version=_FAMILY_REF_VERSION,
                ref_digest=canonical_sdl_digest(self.family).value,
            ),
            capture_spec_refs=[
                ExperimentReferenceModel(
                    ref_kind="capture-spec",
                    ref_id=capture.capture_spec_id,
                    ref_version=capture.spec_version,
                    ref_digest=canonical_json_digest(capture.model_dump(mode="json")),
                )
                for capture in self.capture_specs.values()
            ],
            binding_descriptor_set_ref=None
            if descriptors is None
            else ExperimentReferenceModel(
                ref_kind="other",
                ref_id=experiment.spec_id,
                ref_version=experiment.spec_version,
                ref_digest=canonical_json_digest(descriptors.model_dump(mode="json")),
            ),
        )


def experiment_members(inventory: Iterable[str], suffix: str) -> list[str]:
    """Return sorted direct ``experiments/`` members with one suffix."""

    return sorted(
        rel
        for rel in inventory
        if PurePosixPath(rel).parent == PurePosixPath(EXPERIMENTS_DIR) and rel.endswith(suffix)
    )


def _index(
    documents: Mapping[str, _Document],
    identity: Callable[[_Document], tuple[str, str]],
    kind: str,
    add: AddError,
) -> dict[tuple[str, str], list[tuple[str, _Document]]]:
    """Index admitted documents by RAES identity and report duplicates."""

    index: dict[tuple[str, str], list[tuple[str, _Document]]] = {}
    for rel, document in sorted(documents.items()):
        index.setdefault(identity(document), []).append((rel, document))
    for rows in index.values():
        for rel, _document in rows[1:]:
            add(f"experiment.{kind}-duplicate", rel)
    return index


def _admit_documents(
    documents: Mapping[str, object],
    model: type[_Document],
    kind: str,
    add: AddError,
) -> dict[str, _Document]:
    """Validate each decoded document through its RAES contract model."""

    admitted: dict[str, _Document] = {}
    for rel, document in documents.items():
        try:
            admitted[rel] = model.model_validate(document)  # type: ignore[attr-defined]
        except ValueError:
            add(f"experiment.{kind}-invalid", rel)
    return admitted


def _resolve(
    index: Mapping[tuple[str, str], list[tuple[str, _Document]]],
    ref_id: str,
    ref_version: str | None,
) -> list[tuple[str, _Document]]:
    """Return every indexed document a RAES id/version reference matches."""

    return [
        row
        for (document_id, document_version), rows in sorted(index.items())
        if document_id == ref_id and ref_version in (None, document_version)
        for row in rows
    ]


def _one(
    matches: list[tuple[str, _Document]], kind: str, rel: str, add: AddError
) -> tuple[str, _Document] | None:
    """Return the single match, or record why the reference does not resolve."""

    if len(matches) == 1:
        return matches[0]
    add(f"experiment.{kind}-{'unresolved' if not matches else 'ambiguous'}", rel)
    return None


def _captures(
    spec: ExperimentSpecModel,
    index: Mapping[tuple[str, str], list[tuple[str, ExperimentCaptureSpecModel]]],
    rel: str,
    add: AddError,
) -> dict[str, ExperimentCaptureSpecModel] | None:
    """Resolve every capture reference to one document per capture id.

    The RAES trial compiler keys capture payloads by capture id, so two
    references that resolve to one id cannot both reach it.
    """

    captures: dict[str, ExperimentCaptureSpecModel] = {}
    complete = True
    for reference in spec.capture_spec_refs:
        match = _one(_resolve(index, reference.ref_id, reference.ref_version), "capture", rel, add)
        if match is None:
            complete = False
        elif match[1].capture_spec_id in captures:
            add("experiment.capture-ambiguous", rel)
            complete = False
        else:
            captures[match[1].capture_spec_id] = match[1]
    return captures if complete else None


def _family(
    spec: ExperimentSpecModel,
    scenarios: Mapping[str, object],
    rel: str,
    add: AddError,
) -> tuple[str, ExpandedScenario] | None:
    """Admit the pack SDL document the experiment names as its family."""

    reference = spec.intended_scenario_ref
    if reference is None or reference.ref_kind != "scenario":
        add("experiment.scenario-unresolved", rel)
        return None
    matches = [
        (sdl_rel, scenario)
        for sdl_rel, scenario in sorted(scenarios.items())
        if getattr(scenario, "name", None) == reference.ref_id
    ]
    match = _one(matches, "scenario", rel, add)
    if match is None:
        return None
    sdl_rel, scenario = match
    if isinstance(scenario, ExpandedScenario) and scenario.semantic_validated:
        return sdl_rel, scenario
    try:
        if not isinstance(scenario, Scenario):
            raise ValueError("family is not an authored scenario")
        return sdl_rel, admit_scenario_family(scenario)
    except (SDLError, ValueError):
        add("experiment.family-invalid", rel)
    return None


def _check_family(
    spec: ExperimentSpecModel, family: ExpandedScenario, rel: str, add: AddError
) -> bool:
    """Run every RAES family check that needs no apparatus manifest."""

    resolver = ExpandedScenarioBindingTargetResolver(family)
    checks: tuple[tuple[str, Callable[[], object]], ...] = (
        ("selection", lambda: validate_experiment_selection_against_family(spec, family=family)),
        ("treatment", lambda: _check_treatments(spec, resolver)),
        ("binding", lambda: _check_scenario_bindings(spec, resolver)),
    )
    ok = True
    for kind, check in checks:
        try:
            check()
        except ValueError:
            add(f"experiment.{kind}-invalid", rel)
            ok = False
    return ok


def _check_treatments(
    spec: ExperimentSpecModel, resolver: ExpandedScenarioBindingTargetResolver
) -> None:
    """Admit every typed scenario selection through the RAES target resolver."""

    design = spec.factorial_design
    if not isinstance(design, ExperimentFactorialTreatmentDesignModel):
        return
    for levels in design.level_effects.values():
        for effect in levels.values():
            for selection in effect.selections:
                resolver.validate_selection(selection)


def _check_scenario_bindings(
    spec: ExperimentSpecModel, resolver: ExpandedScenarioBindingTargetResolver
) -> None:
    """Admit scenario-plane bindings; other planes need supplied manifests."""

    descriptors = spec.binding_descriptors
    if descriptors is None:
        return
    scenario = [
        descriptor
        for descriptor in descriptors.descriptors
        if isinstance(descriptor.target, ScenarioBindingTargetModel)
    ]
    if scenario:
        validate_experiment_binding_targets(
            ExperimentBindingDescriptorSetModel(
                schema_version=descriptors.schema_version, descriptors=scenario
            ),
            scenario_resolver=resolver,
            participant_manifests={},
            apparatus_manifests={},
        )


def _parse_spec(
    text: str, rel: str, add: AddError, task: ExperimentTaskModel | None = None
) -> ExperimentSpecModel | None:
    """Parse one authoring input through the RAES experiment loader."""

    try:
        return parse_experiment_spec(text, path=None, task=task)
    except ExperimentSpecValidationError:
        add("experiment.spec-invalid", rel)
    return None


def admit_experiment_set(
    *,
    tasks: Mapping[str, object],
    captures: Mapping[str, object],
    specs: Mapping[str, str],
    scenarios: Mapping[str, object],
    add: AddError,
) -> tuple[PackExperiment, ...]:
    """Admit every recognized document and join each experiment.

    ``tasks`` and ``captures`` map member paths to decoded JSON documents;
    ``specs`` maps member paths to decoded YAML text; ``scenarios`` maps SDL
    member paths to parsed scenarios. Only fully joined experiments return.
    """

    task_index = _index(
        _admit_documents(tasks, ExperimentTaskModel, "task", add),
        lambda task: (task.task_id, task.task_version),
        "task",
        add,
    )
    capture_index = _index(
        _admit_documents(captures, ExperimentCaptureSpecModel, "capture", add),
        lambda capture: (capture.capture_spec_id, capture.spec_version),
        "capture",
        add,
    )
    parsed = {
        rel: spec for rel, text in specs.items() if (spec := _parse_spec(text, rel, add)) is not None
    }
    _index(parsed, lambda spec: (spec.spec_id, spec.spec_version), "spec", add)
    admitted: list[PackExperiment] = []
    for rel, spec in sorted(parsed.items()):
        experiment = _join(rel, specs[rel], spec, task_index, capture_index, scenarios, add)
        if experiment is not None:
            admitted.append(experiment)
    return tuple(admitted)


def _join(
    rel: str,
    text: str,
    spec: ExperimentSpecModel,
    task_index: Mapping[tuple[str, str], list[tuple[str, ExperimentTaskModel]]],
    capture_index: Mapping[tuple[str, str], list[tuple[str, ExperimentCaptureSpecModel]]],
    scenarios: Mapping[str, object],
    add: AddError,
) -> PackExperiment | None:
    """Resolve one experiment's references and run the RAES family checks."""

    task_match = _one(
        _resolve(task_index, spec.task_ref.ref_id, spec.task_ref.ref_version), "task", rel, add
    )
    captures = _captures(spec, capture_index, rel, add)
    family = _family(spec, scenarios, rel, add)
    if task_match is None or captures is None or family is None:
        return None
    _task_rel, task = task_match
    bound = _parse_spec(text, rel, add, task=task)
    family_rel, admitted_family = family
    if bound is None or not _check_family(bound, admitted_family, rel, add):
        return None
    return PackExperiment(
        path=rel,
        experiment=bound,
        task=task,
        capture_specs=MappingProxyType(captures),
        family=admitted_family,
        family_path=family_rel,
    )


__all__ = [
    "CAPTURE_SUFFIX",
    "EXPERIMENTS_DIR",
    "PackExperiment",
    "SPEC_SUFFIX",
    "TASK_SUFFIX",
    "admit_experiment_set",
    "experiment_members",
]
