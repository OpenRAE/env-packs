package raes

// Compiler assertions protect the capabilities that future consumers need.
// They do not claim compatibility with an upstream implementation.
var _ interface {
	AdmitContract(contract string, value any) (map[string]any, []Diagnostic, error)
} = ContractValidator(nil)

var _ interface {
	TrialCompilationRequest(input TrialInput) (TrialRequest, error)
} = Experiments(nil)

var _ interface {
	ValidateAndNormalize(configuration map[string]any) (map[string]any, error)
} = ParticipantConfigurationValidator(nil)

// Compile the caller-owned context without reducing handles or validators to JSON.
var _ = TrialInput{
	Family:                             Scenario(nil),
	ApparatusManifests:                 map[ManifestKey]map[string]any{},
	ParticipantManifests:               map[ManifestKey]map[string]any{},
	ParticipantConfigurationValidators: map[ManifestKey]ParticipantConfigurationValidator{},
}

var _ = ManifestLimits{MaxArtifacts: 1, MaxArtifactBytes: 1, MaxTotalBytes: 1}
