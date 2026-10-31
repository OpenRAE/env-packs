package testgate

import (
	"fmt"
	"slices"

	"github.com/OpenRAE/env-packs/internal/strictyaml"
)

// RecordsFile is the file of the equivalent mutants, relative to the
// repository root.
const RecordsFile = "mutation.yaml"

// Records is the content of mutation.yaml.
type Records struct {
	// Version is the format version. It is 1.
	Version int `yaml:"version"`
	// Equivalents are the mutants that change no behavior that a test can
	// observe.
	Equivalents []Equivalent `yaml:"equivalents"`
}

// An Equivalent records one equivalent mutant. The gate matches a record by
// all values except Reason.
type Equivalent struct {
	// File is the path of the file, relative to the repository root.
	File string `yaml:"file"`
	// Function is the function of the mutant, as in Survivor.
	Function string `yaml:"function"`
	// Mutator is the name of the go-mutesting mutator.
	Mutator string `yaml:"mutator"`
	// Line is the text of the first changed line, without leading and
	// trailing space.
	Line string `yaml:"line"`
	// Reason tells why no test can observe the change.
	Reason string `yaml:"reason"`
}

// ParseRecords decodes mutation.yaml strictly.
func ParseRecords(data []byte) (Records, error) {
	var r Records
	if err := strictyaml.Decode(data, &r); err != nil {
		return Records{}, fmt.Errorf("decode %s: %w", RecordsFile, err)
	}
	return r, nil
}

// Check returns a finding for each defect of the records: a version other
// than 1, a record without a file, a mutator, a line, or a reason, and a
// record that repeats an earlier record.
func (r Records) Check() []Finding {
	var findings []Finding
	if r.Version != 1 {
		findings = append(findings, recordFinding(fmt.Sprintf("version is %d; the only supported version is 1", r.Version)))
	}
	seen := make(map[Equivalent]bool)
	for i, e := range r.Equivalents {
		if e.File == "" || e.Mutator == "" || e.Line == "" || e.Reason == "" {
			findings = append(findings, recordFinding(fmt.Sprintf("record %d needs a file, a mutator, a line, and a reason", i+1)))
		}
		key := e
		key.Reason = ""
		if seen[key] {
			findings = append(findings, recordFinding(fmt.Sprintf("record %d repeats an earlier record", i+1)))
		}
		seen[key] = true
	}
	return findings
}

// match returns the index of the record of survivor s, or -1.
func (r Records) match(s Survivor) int {
	return slices.IndexFunc(r.Equivalents, func(e Equivalent) bool {
		return e.File == s.File && e.Function == s.Function && e.Mutator == s.Mutator && e.Line == s.Line
	})
}

func recordFinding(message string) Finding {
	return Finding{
		Location: RecordsFile,
		Rule:     RuleRecord,
		Message:  message,
		Fix:      "Correct the record as docs/development/go-test-standard.md describes.",
	}
}
