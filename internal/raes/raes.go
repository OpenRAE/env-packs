// Package raes declares the RAES operations that env-packs uses (design
// 0007). The Go code calls RAES only through these interfaces. One adapter
// implements them with the RAES Go module, and only the adapter imports that
// module.
//
// The interfaces copy no RAES schema, enumeration, address grammar, or
// validator (ADR 0009). A document that RAES owns passes through them as its
// published JSON form, and env-packs reads only the fields that its own
// contracts need. A failure carries the structured data of RAES, and never
// its message text.
package raes

import (
	"io"
	"io/fs"
)

// A Diagnostic is one structured diagnostic of RAES.
type Diagnostic struct {
	// Code is the stable code of RAES, such as
	// "associated-artifact.parent-mismatch".
	Code string
	// Severity is the severity that RAES gives.
	Severity string
	// Stage is the stage of RAES that found the problem.
	Stage string
	// Source names the source of the problem, such as "/sdl/scenario.sdl.yaml".
	Source string
	// Pointer is the JSON pointer of the problem in its source.
	Pointer string
	// Range is the source range of the problem, or nil.
	Range *Range
}

// A Range is a range of lines and columns in a source. Lines and columns
// start at 1.
type Range struct {
	StartLine, StartColumn, EndLine, EndColumn int
}

// An Error is a failure that RAES reports for its input.
type Error struct {
	// Code is the RAES code of the failure, such as the code of an import
	// refusal.
	Code string
	// Located reports whether RAES located the failure in a source.
	Located bool
	// Diagnostics are the structured diagnostics of the failure.
	Diagnostics []Diagnostic
}

// Error returns the code of the failure.
func (e *Error) Error() string {
	return "raes: " + e.Code
}

// A Scenario is an SDL scenario that RAES parsed and validated. It is a
// handle: the adapter keeps the RAES value, and only the adapter that made a
// scenario accepts it.
type Scenario interface {
	// Document returns the published JSON form of the scenario. env-packs
	// reads from it the facts that its contracts need, such as the name, the
	// module identity, the parameters with their defaults, the exports of
	// each section, and the content sets of the nodes.
	Document() map[string]any
	// SemanticallyValidated reports whether RAES validated the semantics of
	// the scenario.
	SemanticallyValidated() bool
}

// SDLLimits are the limits of an SDL parse. The adapter takes the other
// limits of the RAES parser from the defaults of RAES.
type SDLLimits struct {
	// MaxComposedBytes is the most bytes that the sources of one composed
	// scenario can have.
	MaxComposedBytes int64
}

// SDL parses and validates SDL documents.
type SDL interface {
	// DefaultSDLLimits returns the default limits of RAES.
	DefaultSDLLimits() SDLLimits
	// Parse parses one SDL document that has no imports.
	Parse(source []byte, limits SDLLimits) (Scenario, error)
	// ParseSources parses the document at root. sources holds each SDL
	// document and lock that its imports can read, by pack-relative path.
	ParseSources(sources map[string][]byte, root string, limits SDLLimits) (Scenario, error)
	// ParseFile parses the document at path in fsys, and reads its imports
	// from fsys.
	ParseFile(fsys fs.FS, path string, limits SDLLimits) (Scenario, error)
	// AuthoredScenario returns the scenario that source declares, before its
	// imports expand. The caller must parse source with imports first.
	AuthoredScenario(source []byte) (Scenario, error)
}

// Digests gives the canonical digests of RAES.
type Digests interface {
	// SDLDigest returns the canonical semantic digest of a scenario, such as
	// "sha256:...".
	SDLDigest(s Scenario) (string, error)
	// JSONDigest returns the canonical digest of a JSON value.
	JSONDigest(value any) (string, error)
}

// An Edit is one structured edit of an SDL document.
type Edit struct {
	// Operation is "set", "append", or "delete".
	Operation string
	// Pointer is the JSON pointer of the edited value, such as "/imports".
	Pointer string
	// Value is the new value of "set" and "append".
	Value any
}

// An EditResult is the result of an edit.
type EditResult struct {
	// Status is the status that RAES gives, such as "edited".
	Status string
	// Content is the edited document.
	Content []byte
	// Diagnostics are the diagnostics of the edited document.
	Diagnostics []Diagnostic
}

// Language gives the SDL language services of RAES.
type Language interface {
	// Edit applies a structured edit to an SDL document.
	Edit(source []byte, edit Edit) (EditResult, error)
	// Completions returns the completions at a cursor path, as the document
	// of RAES that the MCP tool returns.
	Completions(source []byte, cursorPath, prefix string) (map[string]any, error)
	// Diagnostics returns the diagnostics document of RAES for a document.
	Diagnostics(source []byte) (map[string]any, error)
	// Format returns the format document of RAES for a document.
	Format(source []byte) (map[string]any, error)
}

// Modules loads and resolves module locks. A lock is the published JSON form
// of a RAES lock file.
type Modules interface {
	// LockfileName returns the name of a RAES lock file.
	LockfileName() string
	// LoadLockfile loads the lock in the directory dir of fsys.
	LoadLockfile(fsys fs.FS, dir string) (map[string]any, error)
	// ResolveLock resolves the exact module lock of the SDL document at path
	// in fsys under the default trust policy of RAES.
	ResolveLock(fsys fs.FS, path string) (map[string]any, error)
}

// Concepts gives the external concept bindings of a scenario.
type Concepts interface {
	// ConceptSubjects returns the published JSON form of each subject that a
	// concept binding of the scenario can bind.
	ConceptSubjects(s Scenario) ([]map[string]any, error)
	// AdmitConceptBindings admits a bindings document against pinned scheme
	// snapshots. It reports whether each binding resolves to a current, exact
	// concept. Both documents are JSON values.
	AdmitConceptBindings(s Scenario, bindings, snapshots any) (bool, error)
}

// ManifestLimits are the limits of an associated-artifact manifest.
type ManifestLimits struct {
	// MaxArtifacts is the most artifacts that a manifest can have.
	MaxArtifacts int
}

// Artifacts validates associated-artifact manifests. A manifest is its
// published JSON form.
type Artifacts interface {
	// DefaultManifestLimits returns the default limits of RAES.
	DefaultManifestLimits() ManifestLimits
	// LoadManifest reads one manifest from JSON bytes, and validates its form.
	LoadManifest(data []byte) (map[string]any, error)
	// ValidateManifest validates the bytes of each artifact, which readers
	// give by artifact id, and the parent scenario of a manifest.
	ValidateManifest(manifest map[string]any, parent Scenario, readers map[string]io.Reader, limits ManifestLimits) ([]Diagnostic, error)
	// SetDigest returns the digest of the artifact set of a manifest.
	SetDigest(manifest map[string]any) (string, error)
}

// A Requirement is one artifact requirement of a scenario.
type Requirement struct {
	// Trail is the owner trail of the requirement in the scenario.
	Trail []string
	// Document is the published JSON form of the requirement.
	Document map[string]any
}

// Requirements gives the artifact requirements of scenarios, and the compiled
// addresses of RAES.
type Requirements interface {
	// ArtifactRequirements returns each artifact requirement of a scenario.
	ArtifactRequirements(s Scenario) ([]Requirement, error)
	// RequirementAddress returns the compiled address of the requirement with
	// an owner trail, under the provisioning plan root.
	RequirementAddress(trail []string) (string, error)
	// CheckAddress checks that address is a compiled address.
	CheckAddress(address string) error
}

// A ContractValidator validates documents against the published RAES
// contracts.
type ContractValidator interface {
	// ValidateContract checks value against the published contract with the
	// name contract, such as an artifact identity or an experiment
	// specification.
	ValidateContract(contract string, value any) ([]Diagnostic, error)
}

// A BackendProfileLoader loads the backend profiles of RAES.
type BackendProfileLoader interface {
	// LoadBackendProfile returns the published JSON form of the backend
	// profile with an id.
	LoadBackendProfile(id string) (map[string]any, error)
}

// Experiments admits experiments against scenario families. The documents
// are JSON values.
type Experiments interface {
	// ParseExperimentSpec parses an experiment specification with its task.
	ParseExperimentSpec(text []byte, task any) (map[string]any, error)
	// AdmitScenarioFamily admits a scenario as a scenario family.
	AdmitScenarioFamily(s Scenario) (Scenario, error)
	// ValidateSelection checks the selection of an experiment against a
	// family.
	ValidateSelection(spec any, family Scenario) error
	// ValidateBindingTargets checks the binding descriptors of an experiment
	// that target the scenario plane against a family.
	ValidateBindingTargets(descriptors any, family Scenario) error
	// ValidateParticipantConfiguration checks the configuration of a
	// participant implementation against its manifest.
	ValidateParticipantConfiguration(manifest, configuration any) error
	// TrialCompilationRequest builds and checks the trial compilation request
	// of an experiment.
	TrialCompilationRequest(request any) (map[string]any, error)
}

// A Compilation is a scenario that RAES compiled. It is a handle: only the
// adapter that made it accepts it.
type Compilation interface {
	// Nodes returns the number of node deployments of the compiled model.
	Nodes() int
	// Networks returns the number of networks of the compiled model.
	Networks() int
	// Diagnostics returns the diagnostics of the compile.
	Diagnostics() []Diagnostic
}

// A Plan summarizes the plan of a compiled scenario with the reference stub
// manifest of RAES.
type Plan struct {
	// Valid reports whether the plan is valid.
	Valid bool
	// Resources is the number of resources of each plan, by plan name.
	Resources map[string]int
	// Diagnostics are the diagnostics of the plan.
	Diagnostics []Diagnostic
}

// Planning compiles and plans scenarios for the MCP tool. It runs nothing.
type Planning interface {
	// Compile compiles a scenario with parameter values.
	Compile(s Scenario, parameters map[string]any) (Compilation, error)
	// PlanWithStubs plans a compiled scenario with the reference stub
	// manifest of RAES.
	PlanWithStubs(c Compilation) (Plan, error)
}

// Content gives the operations that the content checks of the hosted packs
// use (chunk 27).
type Content interface {
	// Instantiate instantiates a scenario with variable values.
	Instantiate(s Scenario, values map[string]any) (Scenario, error)
	// AdmitInstantiated admits an instantiated scenario.
	AdmitInstantiated(s Scenario) error
	// ResolveRealizationDesignation resolves the realization designation of
	// a scenario.
	ResolveRealizationDesignation(s Scenario, designation any) (map[string]any, error)
	// EvaluateRealizationConstraint evaluates a realization constraint.
	EvaluateRealizationConstraint(constraint, structure any) (map[string]any, error)
	// AdmitRealizationObservation admits a realization observation.
	AdmitRealizationObservation(observation any) (map[string]any, error)
}
