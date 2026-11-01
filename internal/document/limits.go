package document

// Limits bound a document, as PackValidationLimits does in the Python code.
type Limits struct {
	// MaxBytes is the largest size of a document.
	MaxBytes int
	// MaxNodes is the largest number of scalars, mappings, and sequences. It
	// also bounds the nodes times the aliases plus one.
	MaxNodes int
	// MaxAliases is the largest number of YAML aliases.
	MaxAliases int
	// MaxDepth is the deepest nesting of mappings and sequences.
	MaxDepth int
}

// DefaultLimits returns the limits of the pack metadata documents.
func DefaultLimits() Limits {
	return Limits{MaxBytes: 1 << 20, MaxNodes: 20_000, MaxAliases: 64, MaxDepth: 64}
}
