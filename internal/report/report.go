// Package report holds the findings of the repository tools and writes them,
// with the exit statuses that the tools share.
package report

import (
	"bufio"
	"cmp"
	"errors"
	"fmt"
	"io"
	"slices"
)

// The exit statuses of the repository tools.
const (
	// StatusOK reports a run without findings.
	StatusOK = 0
	// StatusFindings reports a run with findings.
	StatusFindings = 1
	// StatusUsage reports invalid usage.
	StatusUsage = 2
	// StatusFailure reports a run that could not complete.
	StatusFailure = 3
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
// message, then the fix.
func (f Finding) String() string {
	return f.Location + ": " + f.Rule + ": " + f.Message + "\n\tfix: " + f.Fix
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

// Streams are the buffered output streams of a tool. A bufio.Writer keeps
// its first write error, and Flush returns it, so a tool does not check each
// write.
type Streams struct {
	Stdout, Stderr *bufio.Writer
}

// NewStreams returns buffered streams that write to stdout and stderr.
func NewStreams(stdout, stderr io.Writer) Streams {
	return Streams{Stdout: bufio.NewWriter(stdout), Stderr: bufio.NewWriter(stderr)}
}

// Flush writes the buffered output of both streams. It returns status, or
// StatusFailure when a write failed.
func (s Streams) Flush(status int) int {
	if errors.Join(s.Stdout.Flush(), s.Stderr.Flush()) != nil {
		return StatusFailure
	}
	return status
}

// Findings writes the sorted findings to Stdout, and their number to Stderr
// after the name of the tool. It returns StatusFindings when there is a
// finding, and StatusOK otherwise.
func (s Streams) Findings(tool string, findings []Finding) int {
	findings = Sort(findings)
	for _, f := range findings {
		fmt.Fprintf(s.Stdout, "%s\n", f)
	}
	fmt.Fprintf(s.Stderr, "%s: %d findings\n", tool, len(findings))
	if len(findings) > 0 {
		return StatusFindings
	}
	return StatusOK
}
