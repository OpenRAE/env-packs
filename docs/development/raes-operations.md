# RAES operations of env-packs

This page lists the RAES operations that env-packs uses (#552, design 0007).
The Go code calls each operation through the interfaces of `internal/raes`.
One adapter implements the interfaces with the RAES Go module. The RAES Go
module does not exist yet, so the adapter does not exist yet. A chunk that
needs an operation waits for the RAES issue that delivers it.

## The rule for the interfaces

The interfaces copy no RAES schema, enumeration, address grammar, or validator
(ADR 0009).

- A document that RAES owns passes through the interfaces as its published JSON
  form. env-packs reads only the fields that its own contracts need.
- A parsed scenario is a handle. It gives its published JSON form, from which
  env-packs reads the facts that it needs.
- A failure is an `*Error` with the code of RAES and its structured
  diagnostics: code, severity, stage, source, pointer, and range. No failure
  uses the message text of RAES as data.

## Operations

The issue column names the RAES Go port issue that delivers the operation.
OpenRAE/rae#1825 defines the public Go API that RAES gives to its consumers.

| Operation | Interface methods | RAES issue |
| --- | --- | --- |
| Parse and validate SDL with limits and structured errors | `SDL.DefaultSDLLimits`, `SDL.Parse`, `SDL.ParseSources`, `SDL.ParseFile`, `SDL.AuthoredScenario` | OpenRAE/rae#1782 (source loading), OpenRAE/rae#1783 (models and semantic validation), and OpenRAE/rae#1785 (imports and composition) |
| Canonical SDL digest | `Digests.SDLDigest` | OpenRAE/rae#1783 |
| Canonical JSON digest | `Digests.JSONDigest` | OpenRAE/rae#1779 |
| SDL language services | `Language.Edit`, `Language.Completions`, `Language.Diagnostics`, `Language.Format` | OpenRAE/rae#1786 |
| Module lock and resolution | `Modules.LockfileName`, `Modules.LoadLockfile`, `Modules.ResolveLock` | OpenRAE/rae#1785 |
| External concept bindings | `Concepts.AdmitConceptBindings` | OpenRAE/rae#1781 |
| External concept subjects of a scenario | `Concepts.ConceptSubjects` | No RAES Go port issue names `raes.external_concept_subjects`. |
| Associated-artifact manifests | `Artifacts.DefaultManifestLimits`, `Artifacts.LoadManifest`, `Artifacts.ValidateManifest`, `Artifacts.SetDigest` | No RAES Go port issue names `raes_contracts.associated_artifacts`. |
| Artifact requirements of a scenario | `Requirements.ArtifactRequirements` | No RAES Go port issue names `raes.artifact_requirements`. |
| Compiled addresses | `Requirements.RequirementAddress`, `Requirements.CheckAddress` | OpenRAE/rae#1779 |
| Validation of a document against a published contract | `ContractValidator.ValidateContract` | OpenRAE/rae#1780 |
| Backend profiles | `BackendProfileLoader.LoadBackendProfile` | OpenRAE/rae#1790 |
| Scenario families and binding targets | `Experiments.AdmitScenarioFamily`, `Experiments.ValidateBindingTargets` | OpenRAE/rae#1785 (selected scenarios) |
| Experiments and trial compilation | `Experiments.ParseExperimentSpec`, `Experiments.ValidateSelection`, `Experiments.TrialCompilationRequest` | OpenRAE/rae#1788 |
| Participant configuration | `Experiments.ValidateParticipantConfiguration` | No RAES Go port issue names `raes_contracts.contracts.participant_configuration`. |
| Compile a scenario | `Planning.Compile` | OpenRAE/rae#1787 |
| Plan with the reference stub manifest | `Planning.PlanWithStubs` | OpenRAE/rae#1787 (planner) and OpenRAE/rae#1790 (stubs) |

## Operations of the content checks

The content checks that chunk 27 keeps use these operations. The tests of the
hosted packs call them today.

| Operation | Interface method | RAES issue |
| --- | --- | --- |
| Instantiate a scenario | `Content.Instantiate` | OpenRAE/rae#1785 |
| Admit an instantiated scenario | `Content.AdmitInstantiated` | OpenRAE/rae#1785 |
| Resolve a realization designation | `Content.ResolveRealizationDesignation` | No RAES Go port issue names `raes.realization_designation`. |
| Evaluate a realization constraint | `Content.EvaluateRealizationConstraint` | No RAES Go port issue names `raes_contracts.realization_structure`. |
| Compile an instantiated scenario and read its published document | `Planning.CompileInstantiated`, `Compilation.Document` | OpenRAE/rae#1787 |
| Read the compiled time-model contract | `Planning.TimeModelContract` | OpenRAE/rae#1787 |
| Build and plan with a custom backend manifest | `Planning.StubManifest`, `Planning.PlanWithManifest` | OpenRAE/rae#1787 and OpenRAE/rae#1790 |
| Read realization concern descriptors | `Content.RealizationConcernDescriptors` | No RAES Go port issue names this operation. |
| Check required observation support | `Content.HasRequiredObservationSupport` | OpenRAE/rae#1787 (processor semantics; exact public API remains a dependency) |

The content checks also read the RAES vocabulary (OpenRAE/rae#1781) and the
apparatus models. No RAES Go port issue names `raes_contracts.apparatus`.

## Map of the RAES symbols

The RAES 10.4 inventory covers 97 distinct imported symbols across application
code, tools, and the eleven content-test modules retained by chunk 27.
It includes `raes_backend_protocols`, which the earlier inventory omitted.
The map records intended adapter responsibilities, not implemented Go parity.
Published document fields and vocabulary stay RAES contracts. The adapter
must validate them through RAES; this repository must not copy their schemas.

The audit uses Python syntax trees to collect imports from `src/`, `tools/`,
and these retained tests: `test_techvault_pack`, `test_techvault_study_pack`,
`test_ai_escape_lab_pack`, `test_owlbear_kit`, `test_smtp_imap_mailbox_domain`,
`test_kit_compute_substrate`, `test_published_kits`,
`test_hosted_pack_content_binding`, `test_hosted_pack_byte_binding`,
`test_raes_reference_eligibility`, and `test_bundled_kits`.

| RAES Python symbol | Go replacement | Used by |
| --- | --- | --- |
| `raes.SDLError` | `SDL` methods: an `*Error` | `_experiment_set.py`, `authoring.py`, `component_boundary.py`, `content_ci.py`, `digest.py`, `kits.py`, `release.py`, `validation.py`, `test_raes_reference_eligibility.py` |
| `raes.SDLImportError` | `SDL.ParseSources`: an `*Error` with `Located` | `validation.py` |
| `raes.SDLImportErrorCode` | `Error.Code` | `validation.py` |
| `raes.SDLInstantiationError` | `Content.Instantiate`: an `*Error` | `test_techvault_pack.py` |
| `raes.SDLParseError` | `SDL.ParseFile`: an `*Error` | `test_owlbear_kit.py` |
| `raes.SDLParserLimits` | `SDLLimits`, `SDL.DefaultSDLLimits` | `validation.py` |
| `raes.SDLSelectionError` | `Experiments.AdmitScenarioFamily`: an `*Error` | `_experiment_set.py` |
| `raes.Scenario` | `Scenario` | `digest.py`, `kits.py` |
| `raes.admit_instantiated_scenario` | `Content.AdmitInstantiated` | `test_techvault_study_pack.py` |
| `raes.admit_scenario_family` | `Experiments.AdmitScenarioFamily` | `_experiment_set.py` |
| `raes.artifact_requirements.ArtifactRequirement` | `Requirement`, `Requirements.ArtifactRequirements` | `publication.py` |
| `raes.artifact_requirements.ArtifactSatisfactionRoute` | a field of the JSON form of a requirement | `publication.py` |
| `raes.artifact_requirements.Source` | `Requirements.ArtifactRequirements` (the owner trail) | `publication.py` |
| `raes.associated_artifacts.ScenarioArtifactParent` | `Artifacts.ValidateManifest` (adapter wraps the scenario parent) | `digest.py`, `kits.py` |
| `raes.canonical.canonical_sdl_digest` | `Digests.SDLDigest` | `_experiment_set.py` |
| `raes.canonical_sdl_digest` | `Digests.SDLDigest` | `kits.py` |
| `raes.experiment_selection.validate_experiment_selection_against_family` | `Experiments.ValidateSelection` | `_experiment_set.py` |
| `raes.external_concept_subjects.external_concept_subjects` | `Concepts.ConceptSubjects` | `validation.py`, `refresh_pack_sdl_binding.py` |
| `raes.instantiate_scenario` | `Content.Instantiate` | `test_techvault_pack.py`, `test_techvault_study_pack.py` |
| `raes.language_service.apply_structured_edit` | `Language.Edit` | `kits.py`, `wizard.py` |
| `raes.language_service.language_completions` | `Language.Completions` | `authoring.py` |
| `raes.language_service.language_diagnostics` | `Language.Diagnostics` | `authoring.py` |
| `raes.language_service.language_format` | `Language.Format` | `authoring.py` |
| `raes.load_sdl_fragment` | `SDL.AuthoredScenario` | `digest.py`, `kits.py` |
| `raes.module_registry.LOCKFILE_NAME` | `Modules.LockfileName` | `validation.py` |
| `raes.module_registry.LockRecord` | a record in the JSON form of a lock | `kits.py` |
| `raes.module_registry.Lockfile` | the JSON form of a lock | `kits.py` |
| `raes.module_registry.TrustPolicy` | `Modules.ResolveLock` (default trust policy) | `kits.py` |
| `raes.module_registry.load_lockfile` | `Modules.LoadLockfile` | `component_boundary.py`, `release.py` |
| `raes.module_registry.resolve_lock_records` | `Modules.ResolveLock` | `kits.py` |
| `raes.parse_sdl` | `SDL.Parse` | `authoring.py`, `kits.py`, `validation.py`, `test_raes_reference_eligibility.py`, `refresh_pack_sdl_binding.py` |
| `raes.parse_sdl_file` | `SDL.ParseFile` | `content_ci.py`, `digest.py`, `kits.py`, `validation.py`, `test_ai_escape_lab_pack.py`, `test_kit_compute_substrate.py`, `test_owlbear_kit.py`, `test_published_kits.py`, `test_smtp_imap_mailbox_domain.py`, `test_techvault_pack.py`, `test_techvault_study_pack.py` |
| `raes.parse_sdl_sources` | `SDL.ParseSources` | `validation.py` |
| `raes.realization_designation.designation_records` | `Content.ResolveRealizationDesignation` (adapter derives records) | `test_techvault_pack.py` |
| `raes.realization_designation.resolve_realization_designation` | `Content.ResolveRealizationDesignation` | `test_techvault_pack.py` |
| `raes.scenario.ExpandedScenario` | `Scenario` | `_experiment_set.py` |
| `raes.scenario.Scenario` | `Scenario` | `_experiment_set.py` |
| `raes.selected_scenario.ExpandedScenarioBindingTargetResolver` | `Experiments.ValidateBindingTargets` | `_experiment_set.py` |
| `raes_backend_protocols.capabilities.BackendManifest` | `Planning.StubManifest`, `Planning.PlanWithManifest` (published manifest) | `test_kit_compute_substrate.py` |
| `raes_backend_protocols.provisioner_capabilities.OperatingSystemCompatibility` | a field of the published backend manifest; RAES validates it | `test_kit_compute_substrate.py` |
| `raes_backend_stubs.stubs.create_stub_manifest` | `Planning.PlanWithStubs`, `Planning.StubManifest` | `authoring.py`, `test_kit_compute_substrate.py` |
| `raes_contracts.addressing.PLAN_ADDRESS_ROOT_BY_DOMAIN` | `Requirements.RequirementAddress` | `publication.py` |
| `raes_contracts.addressing.render_compiled_address` | `Requirements.RequirementAddress` | `publication.py` |
| `raes_contracts.addressing.require_compiled_address` | `Requirements.CheckAddress` | `publication.py` |
| `raes_contracts.apparatus.RealizationObservationCapability` | a field of the published support declaration; RAES validates it | `test_kit_compute_substrate.py`, `test_techvault_pack.py` |
| `raes_contracts.apparatus.RealizationSupportDeclaration` | `Content.HasRequiredObservationSupport` (published declarations) | `test_techvault_pack.py` |
| `raes_contracts.artifact_identity.ArtifactIdentity` | `ContractValidator.ValidateContract` | `digest.py`, `publication.py` |
| `raes_contracts.artifact_identity.ArtifactMechanismProfile` | `ContractValidator.ValidateContract` | `publication.py` |
| `raes_contracts.artifact_requirements.ArtifactMechanismCapability` | `ContractValidator.ValidateContract` | `publication.py` |
| `raes_contracts.associated_artifacts.AssociatedArtifactValidationLimits` | `ManifestLimits`, `Artifacts.DefaultManifestLimits` | `digest.py` |
| `raes_contracts.associated_artifacts.associated_artifact_set_digest` | `Artifacts.SetDigest` | `digest.py`, `kits.py`, `release.py` |
| `raes_contracts.associated_artifacts.load_associated_artifact_manifest_json` | `Artifacts.LoadManifest` | `digest.py`, `kits.py` |
| `raes_contracts.associated_artifacts.validate_associated_artifact_manifest` | `Artifacts.ValidateManifest` | `digest.py`, `kits.py` |
| `raes_contracts.backend_profiles.BackendProfileIdentityError` | `BackendProfileLoader.LoadBackendProfile`: an `*Error` | `publication.py` |
| `raes_contracts.backend_profiles.load_backend_profile` | `BackendProfileLoader.LoadBackendProfile` | `publication.py` |
| `raes_contracts.canonical.canonical_json_digest` | `Digests.JSONDigest` | `_experiment_set.py` |
| `raes_contracts.contracts.AdmittedApparatusBindingModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.AdmittedTrialPlanInputRefsModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.AssociatedArtifactManifestModel` | the JSON form of a manifest | `digest.py`, `kits.py` |
| `raes_contracts.contracts.ExperimentArtifactRefModel` | `ContractValidator.ValidateContract` | `digest.py` |
| `raes_contracts.contracts.ExperimentBindingDescriptorSetModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ExperimentCaptureSpecModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ExperimentFactorialTreatmentDesignModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ExperimentReferenceModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ExperimentScenarioFamilyReferenceModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ExperimentSpecModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ExperimentTaskModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ExternalConceptBindingDocumentModel` | `Concepts.AdmitConceptBindings` | `validation.py` |
| `raes_contracts.contracts.ParticipantImplementationManifestModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.ScenarioBindingTargetModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.TrialCompilationLimitsModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.TrialExecutionAuthorityModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.contracts.participant_configuration.ParticipantConfigurationValidator` | `Experiments.ValidateParticipantConfiguration` | `_experiment_set.py` |
| `raes_contracts.diagnostics.Diagnostic` | `Diagnostic` | `digest.py` |
| `raes_contracts.experiment_bindings.ApparatusManifest` | `Experiments.ValidateBindingTargets` (a manifest) | `_experiment_set.py` |
| `raes_contracts.experiment_bindings.ApparatusManifestKey` | `Experiments.ValidateBindingTargets` (a manifest key) | `_experiment_set.py` |
| `raes_contracts.experiment_bindings.ExperimentBindingTargetError` | `Experiments.ValidateBindingTargets`: an `*Error` | `_experiment_set.py` |
| `raes_contracts.experiment_bindings.ParticipantManifestKey` | `Experiments.ValidateBindingTargets` (a manifest key) | `_experiment_set.py` |
| `raes_contracts.experiment_bindings.validate_experiment_binding_targets` | `Experiments.ValidateBindingTargets` | `_experiment_set.py` |
| `raes_contracts.experiment_spec.ExperimentSpecValidationError` | `Experiments.ParseExperimentSpec`: an `*Error` | `_experiment_set.py` |
| `raes_contracts.experiment_spec.parse_experiment_spec` | `Experiments.ParseExperimentSpec` | `_experiment_set.py` |
| `raes_contracts.external_concept_bindings.ExternalConceptResolutionOutcome` | `Concepts.AdmitConceptBindings` (the result) | `validation.py` |
| `raes_contracts.external_concept_bindings.ExternalConceptSchemeSnapshotModel` | `Concepts.AdmitConceptBindings` | `validation.py` |
| `raes_contracts.external_concept_bindings.admit_external_concept_bindings` | `Concepts.AdmitConceptBindings` | `validation.py` |
| `raes_contracts.json_ingress.StrictJsonIngressError` | `Artifacts.LoadManifest`: an `*Error` | `digest.py`, `kits.py` |
| `raes_contracts.realization_envelope.BackendRealizationEnvelopeModel` | `ContractValidator.ValidateContract` | `_experiment_set.py` |
| `raes_contracts.realization_structure.evaluate_realization_constraint` | `Content.EvaluateRealizationConstraint` | `test_techvault_pack.py` |
| `raes_contracts.vocabulary.ObservationStrength` | published vocabulary values in content fixtures; RAES owns admission | `test_kit_compute_substrate.py`, `test_techvault_pack.py` |
| `raes_contracts.vocabulary.RealizationSupportMode` | published vocabulary values in content fixtures; RAES owns admission | `test_techvault_pack.py` |
| `raes_contracts.vocabulary.RealizationVerificationScope` | published vocabulary values in content fixtures; RAES owns admission | `test_kit_compute_substrate.py`, `test_techvault_pack.py` |
| `raes_processor.compiler.compile_runtime_model` | `Planning.CompileInstantiated`, `Compilation.Document` | `test_techvault_study_pack.py` |
| `raes_processor.compiler.compile_scenario_runtime_model` | `Planning.Compile`, `Compilation.Document` | `authoring.py`, `test_kit_compute_substrate.py`, `test_owlbear_kit.py`, `test_smtp_imap_mailbox_domain.py`, `test_techvault_pack.py` |
| `raes_processor.compiler.time_model.time_model_contract_model` | `Planning.TimeModelContract` | `test_techvault_study_pack.py` |
| `raes_processor.planner.plan` | `Planning.PlanWithStubs`, `Planning.PlanWithManifest` | `authoring.py`, `test_kit_compute_substrate.py`, `test_owlbear_kit.py`, `test_smtp_imap_mailbox_domain.py` |
| `raes_processor.semantics.realization_concerns.realization_concern_descriptors` | `Content.RealizationConcernDescriptors` | `test_kit_compute_substrate.py` |
| `raes_processor.semantics.realization_observation_admission.has_required_observation_support` | `Content.HasRequiredObservationSupport` | `test_techvault_pack.py` |
| `raes_processor.trial_compiler.TrialCompilationRequest` | `Experiments.TrialCompilationRequest` | `_experiment_set.py` |
