package main

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/OpenRAE/env-packs/internal/testgate"
	"github.com/google/go-cmp/cmp"
)

// mainEnv is the environment variable that makes the test binary run the
// command instead of the tests.
const mainEnv = "TESTGATE_TEST_MAIN"

// TestMain runs the command, not the tests, when TestMainProcess starts the
// test binary as a child process.
func TestMain(m *testing.M) {
	if os.Getenv(mainEnv) == "1" {
		main()
		return
	}
	m.Run()
}

// TestMainProcess runs the main function in a child process, to check that
// it passes the command line, the environment, the streams, and the exit
// status.
func TestMainProcess(t *testing.T) {
	binary, err := os.Executable()
	if err != nil {
		t.Fatalf("locate the test binary: %v", err)
	}
	tests := []struct {
		args       []string
		env        []string
		wantStatus int
		wantStderr string
	}{
		{args: []string{"lint"}, wantStatus: 2, wantStderr: "testgate: unknown mode \"lint\"; give mutation, regression, or exec\n"},
		{args: []string{"exec"}, wantStatus: 3, wantStderr: "testgate: read MUTATE_TIMEOUT: strconv.Atoi: parsing \"\": invalid syntax\n"},
		{
			args:       []string{"exec", "-memory", "2048"},
			env:        []string{"MUTATE_TIMEOUT=1", "MUTATE_ORIGINAL=/testgate-missing/x.go"},
			wantStatus: 3,
			wantStderr: "testgate: read the original file: open /testgate-missing/x.go: no such file or directory\n",
		},
	}
	for _, tt := range tests {
		//nolint:gosec // G204 false positive: the command is this test binary, and the test sets each argument.
		cmd := exec.CommandContext(t.Context(), binary, tt.args...)
		cmd.Env = append(append(withoutMutation(os.Environ()), mainEnv+"=1"), tt.env...)
		var stdout, stderr bytes.Buffer
		cmd.Stdout, cmd.Stderr = &stdout, &stderr
		err := cmd.Run()
		status := 0
		if exitErr, ok := errors.AsType[*exec.ExitError](err); ok {
			status = exitErr.ExitCode()
		} else if err != nil {
			t.Fatalf("run the child process: %v", err)
		}
		if status != tt.wantStatus || stdout.String() != "" || stderr.String() != tt.wantStderr {
			t.Errorf("main(%q) = %d, stdout %q, stderr %q; want %d, no stdout, and stderr %q",
				tt.args, status, stdout.String(), stderr.String(), tt.wantStatus, tt.wantStderr)
		}
	}
}

// fakeRunner answers each command with a function.
type fakeRunner struct {
	answer func(c testgate.Command) (testgate.Result, error)
}

func (f fakeRunner) Run(_ context.Context, c testgate.Command) (testgate.Result, error) {
	return f.answer(c)
}

// answers returns a fake runner that answers each command that starts with a
// key of the map with its value, and other commands with no output.
func answers(byPrefix map[string]string) fakeRunner {
	return fakeRunner{answer: func(c testgate.Command) (testgate.Result, error) {
		line := c.String()
		for prefix, out := range byPrefix {
			if strings.HasPrefix(line, prefix) {
				return testgate.Result{Stdout: []byte(out)}, nil
			}
		}
		if strings.HasPrefix(line, "git worktree add ") {
			return testgate.Result{}, os.MkdirAll(c.Args[4], 0o700)
		}
		return testgate.Result{}, nil
	}}
}

// failing is a runner that cannot run a command.
var failing = fakeRunner{answer: func(testgate.Command) (testgate.Result, error) {
	return testgate.Result{}, errors.New("no git")
}}

// runCommand runs the command with args after the program name, and returns
// the exit status and the output streams.
func runCommand(t *testing.T, runner testgate.Runner, environ []string, args ...string) (status int, stdout, stderr string) {
	t.Helper()
	var out, errOut bytes.Buffer
	status = run(context.Background(), process{
		args:    append([]string{"testgate"}, args...),
		environ: environ,
		exe:     "/bin/testgate",
		tempDir: t.TempDir(),
		runner:  runner,
		stdout:  &out,
		stderr:  &errOut,
	})
	return status, out.String(), errOut.String()
}

func TestRunUsage(t *testing.T) {
	tests := []struct {
		name       string
		args       []string
		wantStderr string
	}{
		{name: "no mode", wantStderr: "testgate: give a mode: mutation, regression, or exec\n"},
		{name: "unknown mode", args: []string{"lint"}, wantStderr: "testgate: unknown mode \"lint\"; give mutation, regression, or exec\n"},
		{name: "unknown flag", args: []string{"-color", "mutation"}, wantStderr: "flag provided but not defined: -color"},
		{name: "mutation without a base", args: []string{"mutation"}, wantStderr: "testgate: mutation takes -base or -all, and no arguments\n"},
		{name: "mutation with a base and all", args: []string{"mutation", "-base", "x", "-all"}, wantStderr: "testgate: mutation takes -base or -all"},
		{name: "mutation with an argument", args: []string{"mutation", "-all", "x"}, wantStderr: "testgate: mutation takes -base or -all"},
		{name: "unknown mutation flag", args: []string{"mutation", "-fast"}, wantStderr: "flag provided but not defined: -fast"},
		{name: "regression without a base", args: []string{"regression"}, wantStderr: "testgate: regression takes -base, and no arguments\n"},
		{name: "regression with an argument", args: []string{"regression", "-base", "x", "y"}, wantStderr: "testgate: regression takes -base"},
		{name: "unknown regression flag", args: []string{"regression", "-all"}, wantStderr: "flag provided but not defined: -all"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, stdout, stderr := runCommand(t, failing, nil, tt.args...)
			if status != 2 || stdout != "" || !strings.Contains(stderr, tt.wantStderr) {
				t.Errorf("run(%q) = %d, stdout %q, stderr %q; want 2, no stdout, and stderr with %q", tt.args, status, stdout, stderr, tt.wantStderr)
			}
		})
	}
}

func TestRunMutation(t *testing.T) {
	r := answers(map[string]string{"git rev-parse": "abc\n"})
	status, stdout, stderr := runCommand(t, r, nil, "mutation", "-base", "origin/main")
	wantStderr := "testgate: 0 mutants in 0 files: 0 skipped, 0 killed, 0 not compiled, 0 escaped, 0 equivalent\ntestgate: 0 findings\n"
	if status != 0 || stdout != "" || stderr != wantStderr {
		t.Errorf("run(mutation) = %d, stdout %q, stderr %q; want 0, no stdout, and stderr %q", status, stdout, stderr, wantStderr)
	}
}

func TestRunMutationFailures(t *testing.T) {
	status, _, stderr := runCommand(t, failing, nil, "mutation", "-all")
	if status != 3 || !strings.Contains(stderr, "no git") {
		t.Errorf("run(mutation) with a failing runner = %d, stderr %q; want 3 and the error", status, stderr)
	}
	var out, errOut bytes.Buffer
	status = run(context.Background(), process{
		args:   []string{"testgate", "mutation", "-all"},
		exeErr: errors.New("no executable"),
		runner: failing,
		stdout: &out,
		stderr: &errOut,
	})
	if status != 3 || errOut.String() != "testgate: locate testgate for the exec step: no executable\n" {
		t.Errorf("run(mutation) without an executable = %d, stderr %q; want 3 and the error", status, errOut.String())
	}
}

const regressionTestFile = `package pkg

import "testing"

// Regression test for #9.
func TestFix(t *testing.T) {}
`

func TestRunRegression(t *testing.T) {
	r := answers(map[string]string{
		"git rev-parse":               "abc\n",
		"git diff -U0":                "diff --git a/pkg/a_test.go b/pkg/a_test.go\n--- a/pkg/a_test.go\n+++ b/pkg/a_test.go\n@@ -6 +6 @@\n-// Old.\n+// Regression test for #1.\n",
		"git show HEAD:pkg/a_test.go": regressionTestFile,
		"git merge-base":              "0123456789abcdef\n",
		"go test":                     `{"Action":"pass","Package":"example.com/m/pkg","Test":"TestFix"}` + "\n",
	})
	status, stdout, stderr := runCommand(t, r, nil, "regression", "-base", "origin/main")
	wantStdout := "pkg/a_test.go:6: regression: regression test TestFix passes on the merge base 0123456789ab\n\tfix: Make the test fail without the fix. Write it against the API of the merge base, and do not skip it.\n"
	wantStderr := "testgate: 1 regression tests, 0 fail on the merge base\ntestgate: 1 findings\n"
	if status != 1 || stdout != wantStdout || stderr != wantStderr {
		t.Errorf("run(regression) = %d, stdout %q, stderr %q; want 1, stdout %q, and stderr %q", status, stdout, stderr, wantStdout, wantStderr)
	}
	status, _, stderr = runCommand(t, failing, nil, "regression", "-base", "origin/main")
	if status != 3 || !strings.Contains(stderr, "no git") {
		t.Errorf("run(regression) with a failing runner = %d, stderr %q; want 3 and the error", status, stderr)
	}
}

func TestRunExec(t *testing.T) {
	dir := t.TempDir()
	original, mutated := filepath.Join(dir, "x.go"), filepath.Join(dir, "x.go.0")
	for file, content := range map[string]string{original: "package x\n", mutated: "package y\n"} {
		if err := os.WriteFile(file, []byte(content), 0o600); err != nil {
			t.Fatalf("write %s: %v", file, err)
		}
	}
	environ := []string{
		"MUTATE_ORIGINAL=" + original, "MUTATE_CHANGED=" + mutated, "MUTATE_PACKAGE=" + dir,
		"MUTATE_TIMEOUT=1", "MUTATE_TIMEOUT=30",
	}
	var command testgate.Command
	r := fakeRunner{answer: func(c testgate.Command) (testgate.Result, error) {
		command = c
		return testgate.Result{Stdout: []byte(`{"Action":"pass","Package":"example.com/x"}` + "\n")}, nil
	}}
	status, stdout, stderr := runCommand(t, r, environ, "exec")
	if status != testgate.ExecEscaped || stdout != "" || stderr != "" {
		t.Errorf("run(exec) = %d, stdout %q, stderr %q; want %d and no output", status, stdout, stderr, testgate.ExecEscaped)
	}
	if want := "go test -json -count=1 -timeout=30s " + dir; command.String() != want || command.Dir != "." {
		t.Errorf("run(exec) ran %q in %q, want %q in the working directory", command, command.Dir, want)
	}
	status, _, stderr = runCommand(t, r, environ[1:], "exec")
	if status != 3 || !strings.Contains(stderr, "testgate: read the original file") {
		t.Errorf("run(exec) without MUTATE_ORIGINAL = %d, stderr %q; want 3 and a read error", status, stderr)
	}
}

func TestRunExecMemory(t *testing.T) {
	var limits []uint64
	var limitErr error
	limit := func(n uint64) error {
		limits = append(limits, n)
		return limitErr
	}
	p := func(args ...string) (int, string) {
		var errOut bytes.Buffer
		status := run(context.Background(), process{
			args:        append([]string{"testgate", "exec"}, args...),
			environ:     []string{"MUTATE_TIMEOUT=1"},
			runner:      failing,
			limitMemory: limit,
			stdout:      &bytes.Buffer{},
			stderr:      &errOut,
		})
		return status, errOut.String()
	}
	if status, stderr := p("-memory", "16"); status != 3 || !strings.Contains(stderr, "read the original file") {
		t.Errorf("run(exec -memory 16) = %d, stderr %q; want 3 and a read error after the limit", status, stderr)
	}
	if status, _ := p("-memory", "0"); status != 3 {
		t.Errorf("run(exec -memory 0) = %d, want 3", status)
	}
	if want := []uint64{16 << 20}; len(limits) != 1 || limits[0] != want[0] {
		t.Errorf("run(exec) limits = %v, want %v and no limit for 0", limits, want)
	}
	limitErr = errors.New("no limit")
	if status, stderr := p("-memory", "16"); status != 3 || stderr != "testgate: limit the memory of the tests: no limit\n" {
		t.Errorf("run(exec) with a failing limit = %d, stderr %q; want 3 and the error", status, stderr)
	}
	if status, stderr := p("x"); status != 2 || stderr != "testgate: exec takes no arguments\n" {
		t.Errorf("run(exec x) = %d, stderr %q; want 2 and a usage error", status, stderr)
	}
	if status, stderr := p("-fast"); status != 2 || !strings.Contains(stderr, "flag provided but not defined: -fast") {
		t.Errorf("run(exec -fast) = %d, stderr %q; want 2 and a usage error", status, stderr)
	}
}

func TestRunMutationLimits(t *testing.T) {
	for _, tt := range []struct {
		args []string
		want string
	}{
		{args: []string{"mutation", "-base", "x"}, want: "--exec=/bin/testgate exec -memory 4096"},
		{args: []string{"mutation", "-base", "x", "-memory", "100", "-timeout", "5s"}, want: "--exec=/bin/testgate exec -memory 100 --exec-timeout=5"},
	} {
		var mutesting string
		r := answers(map[string]string{
			"git rev-parse": "abc\n",
			"git diff":      "diff --git a/a.go b/a.go\n--- a/a.go\n+++ b/a.go\n@@ -1 +1 @@\n-package a\n+package a // A.\n",
		})
		recording := fakeRunner{answer: func(c testgate.Command) (testgate.Result, error) {
			if c.Name == "go-mutesting" {
				mutesting = c.String()
				return testgate.Result{ExitCode: 1, Stderr: []byte("stop")}, nil
			}
			return r.answer(c)
		}}
		status, _, stderr := runCommand(t, recording, nil, tt.args...)
		if status != 3 || !strings.Contains(stderr, "stop") || !strings.Contains(mutesting, tt.want) {
			t.Errorf("run(%q) = %d, stderr %q, go-mutesting %q; want 3 and %q", tt.args, status, stderr, mutesting, tt.want)
		}
	}
}

func TestRunMutationScores(t *testing.T) {
	g := newScoreRepo(t)
	status, stdout, stderr := runCommand(t, g, nil, "mutation", "-all")
	want := "testgate: 2 mutants in 2 files: 0 skipped, 1 killed, 0 not compiled, 1 escaped, 1 equivalent\n" +
		"testgate: a: 1 killed, 0 survived, 0 equivalent, score 100.0%\n" +
		"testgate: b: 0 killed, 0 survived, 1 equivalent, no score\n" +
		"testgate: 0 findings\n"
	if status != 0 || stdout != "" || stderr != want {
		t.Errorf("run(mutation -all) = %d, stdout %q, stderr %q; want 0, no stdout, and stderr %q", status, stdout, stderr, want)
	}
}

// newScoreRepo returns a fake runner for a mutation run on a.go and b.go. A
// test kills the mutant of a.go, and a record matches the mutant of b.go.
func newScoreRepo(t *testing.T) fakeRunner {
	t.Helper()
	const source = "package p\n\nfunc F() int {\n\treturn 1\n}\n"
	mutated := strings.Replace(source, "return 1", "return 2", 1)
	mutantJSON := func(file string) string {
		return fmt.Sprintf(`{"mutator":{"mutatorName":"numbers/incrementer","originalFilePath":%q,"originalSourceCode":%q,"mutatedSourceCode":%q}}`, file, source, mutated)
	}
	report := `{"stats":{"totalMutantsCount":2},"killed":[` + mutantJSON("a/a.go") + `],"escaped":[` + mutantJSON("b/b.go") + `]}`
	records := "version: 1\nequivalents:\n  - file: b/b.go\n    function: F\n    mutator: numbers/incrementer\n    line: return 1\n    mutated: return 2\n    reason: R.\n"
	return fakeRunner{answer: func(c testgate.Command) (testgate.Result, error) {
		line := c.String()
		switch {
		case strings.HasPrefix(line, "git ls-tree "):
			return testgate.Result{Stdout: []byte("a/a.go\x00b/b.go\x00")}, nil
		case strings.HasPrefix(line, "git worktree add "):
			return testgate.Result{}, errors.Join(os.MkdirAll(c.Args[4], 0o700), os.WriteFile(filepath.Join(c.Args[4], "mutation.yaml"), []byte(records), 0o600))
		case strings.HasPrefix(line, "go-mutesting "):
			return testgate.Result{}, os.WriteFile(filepath.Join(c.Dir, "report.json"), []byte(report), 0o600)
		}
		return testgate.Result{}, nil
	}}
}

func TestLookup(t *testing.T) {
	environ := []string{"A=1", "AB=2", "A=3", "B="}
	tests := map[string]string{"A": "3", "AB": "2", "B": "", "C": ""}
	for key, want := range tests {
		if got := lookup(environ, key); got != want {
			t.Errorf("lookup(%q) = %q, want %q", key, got, want)
		}
	}
}

// failingWriter fails every write.
type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) {
	return 0, errors.New("write failed")
}

func TestRunOutputFailure(t *testing.T) {
	r := answers(map[string]string{"git rev-parse": "abc\n"})
	for _, args := range [][]string{{"testgate"}, {"testgate", "mutation", "-base", "x"}} {
		status := run(context.Background(), process{args: args, runner: r, tempDir: t.TempDir(), stdout: failingWriter{}, stderr: failingWriter{}})
		if status != 3 {
			t.Errorf("run(%q) with failing output = %d, want 3", args, status)
		}
	}
}

func TestWithoutMutation(t *testing.T) {
	environ := []string{"PATH=/bin", "MUTATE_TIMEOUT=10", "HOME=/home/u", "MUTATE_PACKAGE=x"}
	got := withoutMutation(environ)
	if diff := cmp.Diff([]string{"PATH=/bin", "HOME=/home/u"}, got); diff != "" {
		t.Errorf("withoutMutation() mismatch (-want +got):\n%s", diff)
	}
	if environ[1] != "MUTATE_TIMEOUT=10" {
		t.Errorf("withoutMutation() changed its input: %q", environ)
	}
}
