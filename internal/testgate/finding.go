package testgate

import (
	"cmp"
	"slices"
)

// Rule identifiers of the findings.
const (
	// RuleMutant marks a mutant that no test kills.
	RuleMutant = "mutant"
	// RuleRecord marks a defect in mutation.yaml.
	RuleRecord = "mutation-record"
	// RuleRegression marks a regression test that does not fail on the base.
	RuleRegression = "regression"
)

// A Finding is one problem that a gate found.
type Finding struct {
	// Location is "file:line", or a file when no line applies.
	Location string
	// Rule is the identifier of the broken rule.
	Rule string
	// Message states the problem.
	Message string
	// Fix tells how to correct the problem.
	Fix string
}

// String formats the finding as two lines: the location, the rule, and the
// message, then the fix.
func (f Finding) String() string {
	return f.Location + ": " + f.Rule + ": " + f.Message + "\n\tfix: " + f.Fix
}

// SortFindings sorts findings by location, rule, and message, and removes
// exact duplicates. It returns the sorted slice.
func SortFindings(findings []Finding) []Finding {
	slices.SortFunc(findings, func(a, b Finding) int {
		return cmp.Or(
			cmp.Compare(a.Location, b.Location),
			cmp.Compare(a.Rule, b.Rule),
			cmp.Compare(a.Message, b.Message),
			cmp.Compare(a.Fix, b.Fix),
		)
	})
	return slices.Compact(findings)
}
