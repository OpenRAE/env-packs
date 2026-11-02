package testgate

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strings"
)

// A Command is one process that a gate runs.
type Command struct {
	// Dir is the working directory of the process.
	Dir string
	// Name is the program.
	Name string
	// Args are the arguments after the program name.
	Args []string
}

// String returns the command line, for error messages.
func (c Command) String() string {
	return strings.Join(append([]string{c.Name}, c.Args...), " ")
}

// A Result is the outcome of a command that ran.
type Result struct {
	// Stdout and Stderr are the output streams.
	Stdout, Stderr []byte
	// ExitCode is the exit status.
	ExitCode int
}

// A Runner runs commands. It returns an error only when a command cannot run.
// The result holds a non-zero exit status.
type Runner interface {
	// Run runs the command and waits for it.
	Run(ctx context.Context, c Command) (Result, error)
}

// ExecRunner runs each command as a process with a fixed environment.
type ExecRunner struct {
	// Env is the environment of each process, in the form of os.Environ.
	Env []string
}

// Run runs the command and waits for it.
func (r ExecRunner) Run(ctx context.Context, c Command) (Result, error) {
	// The gates run only git, go, and go-mutesting. They resolve each revision
	// to a commit ID with git rev-parse --verify --end-of-options, and they
	// put each path after "--" or in a position that takes only a path.
	//nolint:gosec // G204 false positive: the program is fixed, and the arguments are checked revisions and paths.
	cmd := exec.CommandContext(ctx, c.Name, c.Args...)
	cmd.Dir = c.Dir
	cmd.Env = r.Env
	var stdout, stderr bytes.Buffer
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	err := cmd.Run()
	res := Result{Stdout: stdout.Bytes(), Stderr: stderr.Bytes()}
	if exitErr, ok := errors.AsType[*exec.ExitError](err); ok {
		res.ExitCode = exitErr.ExitCode()
		return res, nil
	}
	if err != nil {
		return Result{}, fmt.Errorf("run %s: %w", c, err)
	}
	return res, nil
}

// runOK runs a command that must exit with status 0, and returns its
// standard output.
func runOK(ctx context.Context, r Runner, c Command) ([]byte, error) {
	res, err := r.Run(ctx, c)
	if err != nil {
		return nil, err
	}
	if res.ExitCode != 0 {
		return nil, fmt.Errorf("%s: exit status %d: %s", c, res.ExitCode, bytes.TrimSpace(res.Stderr))
	}
	return res.Stdout, nil
}
