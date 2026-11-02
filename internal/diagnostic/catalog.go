package diagnostic

import (
	"bytes"
	_ "embed" // The catalog is an embedded data file.
	"encoding/json"
	"errors"
	"fmt"
	"strings"
)

// catalogJSON is the presentation catalog of check.py in the Python code,
// with the hints for the keywords that the Python schema subset does not
// apply (design 0005). In check.py, the entry of "yaml.invalid" repeats the
// entry of "yaml", so that code takes the entry of "yaml" here.
//
//go:embed catalog.json
var catalogJSON []byte

// A Catalog explains diagnostics to users, by code. It is presentation only,
// and it adds no check.
type Catalog struct {
	families map[string]Presentation
	hints    map[string]string
	generic  Presentation
}

// A Presentation explains a diagnostic to a user.
type Presentation struct {
	// Severity is "error".
	Severity string
	// Domain is "pack", "compatibility", "trust", or "sdl".
	Domain string
	// Owner is the authority of the contract: "env-packs" or "raes".
	Owner string
	// Explanation states the problem.
	Explanation string
	// Reason states why the contract has the rule.
	Reason string
	// Suggestion tells how to correct the problem.
	Suggestion string
	// Doc is the documentation target: DocPage and the anchor of the domain.
	Doc string
}

// The data of the catalog file.
type (
	catalogData struct {
		Domains     map[string]domainData `json:"domains"`
		Families    map[string]entryData  `json:"families"`
		Generic     entryData             `json:"generic"`
		SchemaHints map[string]string     `json:"schema_hints"`
	}
	domainData struct {
		Owner  string `json:"owner"`
		Anchor string `json:"anchor"`
	}
	entryData struct {
		Domain      string `json:"domain"`
		Explanation string `json:"explanation"`
		Reason      string `json:"reason"`
		Suggestion  string `json:"suggestion"`
	}
)

// The errors of parseCatalog.
var (
	errDecode        = errors.New("decode the catalog")
	errUnknownDomain = errors.New("an entry of the catalog has an unknown domain")
)

// NewCatalog returns the presentation catalog. It panics when the embedded
// catalog is not valid, which TestNewCatalog rules out.
func NewCatalog() *Catalog {
	c, err := parseCatalog(catalogJSON)
	if err != nil {
		panic(err)
	}
	return c
}

// parseCatalog returns the catalog in data. Each entry must name a domain of
// the catalog, and data must have no unknown field.
func parseCatalog(data []byte) (*Catalog, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	var cd catalogData
	if err := dec.Decode(&cd); err != nil {
		return nil, fmt.Errorf("%w: %w", errDecode, err)
	}
	generic, err := cd.presentation(cd.Generic)
	if err != nil {
		return nil, err
	}
	c := &Catalog{families: make(map[string]Presentation, len(cd.Families)), hints: cd.SchemaHints, generic: generic}
	for key, entry := range cd.Families {
		if c.families[key], err = cd.presentation(entry); err != nil {
			return nil, fmt.Errorf("family %q: %w", key, err)
		}
	}
	return c, nil
}

// presentation returns the presentation of entry, with the owner and the
// anchor of its domain.
func (cd catalogData) presentation(entry entryData) (Presentation, error) {
	domain, ok := cd.Domains[entry.Domain]
	if !ok {
		return Presentation{}, errUnknownDomain
	}
	return Presentation{
		Severity:    "error",
		Domain:      entry.Domain,
		Owner:       domain.Owner,
		Explanation: entry.Explanation,
		Reason:      entry.Reason,
		Suggestion:  entry.Suggestion,
		Doc:         DocPage + "#" + domain.Anchor,
	}, nil
}

// Presentation returns the presentation of d: the entry of the longest dotted
// prefix of its code, or the generic entry. A "*.schema.<keyword>" code adds
// the hint of its keyword to the suggestion.
func (c *Catalog) Presentation(d Diagnostic) Presentation {
	p := c.generic
	for key, found := d.code, true; found; key, _, found = strings.CutLast(key, ".") {
		if entry, ok := c.families[key]; ok {
			p = entry
			break
		}
	}
	if _, keyword, ok := strings.Cut(d.code, ".schema."); ok {
		if hint, ok := c.hints[keyword]; ok {
			p.Suggestion += " " + hint
		}
	}
	return p
}
