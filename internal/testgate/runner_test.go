package testgate

import (
	"context"
	"errors"
	"path/filepath"
	"strings"
	"testing"
)

// fakeRunner answers each command with a function, and records the commands.
type fakeRunner struct {
	commands []Command
	answer   func(c Command) (Result, error)
}

func (f *fakeRunner) Run(_ context.Context, c Command) (Result, error) {
	f.commands = append(f.commands, c)
	return f.answer(c)
}

// ok returns the result of a command that exits with status 0.
func ok(stdout string) (Result, error) {
	return Result{Stdout: []byte(stdout)}, nil
}

// exit returns the result of a command that fails.
func exit(code int, stderr string) (Result, error) {
	return Result{Stderr: []byte(stderr), ExitCode: code}, nil
}

func TestExecRunner(t *testing.T) {
	r := ExecRunner{Env: []string{"TESTGATE_VALUE=from the environment"}}
	res, err := r.Run(context.Background(), Command{Dir: t.TempDir(), Name: "sh", Args: []string{"-c", `printf %s "$TESTGATE_VALUE"; printf e >&2; exit 3`}})
	if err != nil {
		t.Fatalf("ExecRunner.Run() error = %v", err)
	}
	if string(res.Stdout) != "from the environment" || string(res.Stderr) != "e" || res.ExitCode != 3 {
		t.Errorf("ExecRunner.Run() = %+v, want the environment value, stderr e, and status 3", res)
	}
	dir, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatalf("resolve the temporary directory: %v", err)
	}
	res, err = r.Run(context.Background(), Command{Dir: dir, Name: "sh", Args: []string{"-c", "pwd -P"}})
	if err != nil || res.ExitCode != 0 || strings.TrimSpace(string(res.Stdout)) != dir {
		t.Errorf("ExecRunner.Run(pwd) = %+v, %v, want the working directory %s", res, err, dir)
	}
	if _, err := r.Run(context.Background(), Command{Name: "testgate-no-such-program"}); err == nil {
		t.Error("ExecRunner.Run() of a missing program: error = nil, want an error")
	}
}

func TestRunOK(t *testing.T) {
	r := &fakeRunner{answer: func(Command) (Result, error) { return ok("out") }}
	out, err := runOK(context.Background(), r, Command{Name: "git", Args: []string{"status"}})
	if err != nil || string(out) != "out" {
		t.Errorf("runOK() = %q, %v, want %q, nil", out, err, "out")
	}
	r.answer = func(Command) (Result, error) { return exit(2, "  bad flag\n") }
	_, err = runOK(context.Background(), r, Command{Name: "git", Args: []string{"status"}})
	if err == nil || err.Error() != "git status: exit status 2: bad flag" {
		t.Errorf("runOK() of a failing command: error = %v, want the command, the status, and the stderr", err)
	}
	failure := errors.New("cannot start")
	r.answer = func(Command) (Result, error) { return Result{}, failure }
	if _, err := runOK(context.Background(), r, Command{Name: "git"}); !errors.Is(err, failure) {
		t.Errorf("runOK() of a command that cannot start: error = %v, want %v", err, failure)
	}
}
