// Package report holds the findings of the repository tools and writes them.
// The tools use the exit statuses and the streams of package outcome.
package report

import (
	"cmp"
	"fmt"
	"slices"

	"github.com/OpenRAE/env-packs/internal/outcome"
	"github.com/OpenRAE/env-packs/internal/terminal"
)

// A Finding is one problem that a tool found.
type Finding struct {
	// Location is "file:line", or a file or directory when no line applies.
	Location string
	// Rule is the identifier of the broken rule.
	Rule string
	// Message states the problem.
	Message string
	// Fix tells how to correct the problem.
	Fix string
}

// String formats the finding as two lines: the location, the rule, and the
// message, then the fix. A field can hold a file name or a value from a
// change, so String escapes each field for a terminal (design 0006).
func (f Finding) String() string {
	return terminal.Escape(f.Location) + ": " + terminal.Escape(f.Rule) + ": " + terminal.Escape(f.Message) +
		"\n\tfix: " + terminal.Escape(f.Fix)
}

// Sort sorts findings by location, rule, message, and fix, and removes exact
// duplicates. It returns the sorted slice.
func Sort(findings []Finding) []Finding {
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

// Write writes the sorted findings to the stdout of s, and their number to
// its stderr after the name of the tool. It returns outcome.Blocking when
// there is a finding, and outcome.OK otherwise.
func Write(s outcome.Streams, tool string, findings []Finding) int {
	findings = Sort(findings)
	for _, f := range findings {
		fmt.Fprintf(s.Stdout, "%s\n", f)
	}
	fmt.Fprintf(s.Stderr, "%s: %d findings\n", tool, len(findings))
	if len(findings) > 0 {
		return outcome.Blocking
	}
	return outcome.OK
}
