package testgate

import (
	"fmt"

	"github.com/OpenRAE/env-packs/internal/report"
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
// all values except Reason, and each record covers one mutant. Two identical
// mutants need two records.
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
	// Mutated is the text of that line in the mutant, without leading and
	// trailing space.
	Mutated string `yaml:"mutated"`
	// Occurrence selects one of the identical lines Line of the function,
	// as in Survivor. Zero selects the first.
	Occurrence int `yaml:"occurrence"`
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
// than 1, and a record without a file, a mutator, a line, the mutated line,
// or a reason.
func (r Records) Check() []report.Finding {
	var findings []report.Finding
	if r.Version != 1 {
		findings = append(findings, recordFinding(fmt.Sprintf("version is %d; the only supported version is 1", r.Version)))
	}
	for i, e := range r.Equivalents {
		if e.File == "" || e.Mutator == "" || e.Line == "" || e.Mutated == "" || e.Reason == "" {
			findings = append(findings, recordFinding(fmt.Sprintf("record %d needs a file, a mutator, a line, the mutated line, and a reason", i+1)))
		}
	}
	return findings
}

// match returns the index of the first record of survivor s that no earlier
// survivor used, or -1.
func (r Records) match(s Survivor, used []bool) int {
	for i, e := range r.Equivalents {
		if !used[i] && e.File == s.File && e.Function == s.Function && e.Mutator == s.Mutator &&
			e.Line == s.Line && e.Mutated == s.Mutated && max(e.Occurrence, 1) == s.Occurrence {
			return i
		}
	}
	return -1
}

func recordFinding(message string) report.Finding {
	return report.Finding{
		Location: RecordsFile,
		Rule:     RuleRecord,
		Message:  message,
		Fix:      "Correct the record as docs/development/go-test-standard.md describes.",
	}
}
