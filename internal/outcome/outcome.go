// Package outcome holds the process contract of the commands and the
// repository tools: the exit statuses, the output streams, and the handling of
// defects (design 0006, ADR 0031).
package outcome

import (
	"bufio"
	"errors"
	"fmt"
	"io"
)

// The exit statuses.
const (
	// OK reports a run without problems.
	OK = 0
	// Blocking reports a run that found blocking problems in its input.
	Blocking = 1
	// Usage reports an invalid invocation.
	Usage = 2
	// ToolFailure reports a defect or a failure that is not in the input.
	ToolFailure = 3
)

// Streams are the buffered output streams of a run. A bufio.Writer keeps its
// first write error, and Flush returns it, so a run does not check each write.
type Streams struct {
	Stdout, Stderr *bufio.Writer
	// stdout is the writer of Stdout, so that a defect can drop the output
	// that Stdout holds.
	stdout io.Writer
}

// NewStreams returns buffered streams that write to stdout and stderr.
func NewStreams(stdout, stderr io.Writer) Streams {
	return Streams{Stdout: bufio.NewWriter(stdout), Stderr: bufio.NewWriter(stderr), stdout: stdout}
}

// Flush writes the buffered output of both streams. It returns status, or
// ToolFailure when a write failed, so that a full disk or a closed pipe is
// never a success.
func (s Streams) Flush(status int) int {
	if errors.Join(s.Stdout.Flush(), s.Stderr.Flush()) != nil {
		return ToolFailure
	}
	return status
}

// Run runs body, the body of the command name, and returns the exit status.
// The body handles its expected failures and returns a status. An error from
// the body, or a panic, is a defect: Run drops the output that Stdout holds,
// writes "name: internal error (type)" to Stderr, and returns ToolFailure.
// The message names the Go type of the error or of the panic value, and never
// its text, because the text can hold a path or a value.
func Run(name string, s Streams, body func(Streams) (int, error)) (status int) {
	defer func() {
		if cause := recover(); cause != nil {
			status = defect(name, s, cause)
		}
	}()
	status, err := body(s)
	if err != nil {
		return defect(name, s, err)
	}
	return s.Flush(status)
}

// defect reports the defect cause of the command name and returns the exit
// status.
func defect(name string, s Streams, cause any) int {
	s.Stdout.Reset(s.stdout)
	fmt.Fprintf(s.Stderr, "%s: internal error (%T)\n", name, cause)
	return s.Flush(ToolFailure)
}
