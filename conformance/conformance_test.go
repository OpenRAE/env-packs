package conformance

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/rogpeppe/go-internal/testscript"
	"github.com/rogpeppe/go-internal/txtar"
)

var (
	impl     = flag.String("impl", "", "the implementation under test: python or go")
	bin      = flag.String("bin", "", "the `directory` of the Go commands, for -impl=go")
	faultBin = flag.String("fault-bin", "", "the `directory` of test-only Go fault drivers")
)

// TestCorpus runs each case against the implementation that -impl selects.
// Each directory in testdata holds the cases of one command.
func TestCorpus(t *testing.T) {
	switch {
	case *impl == "":
		t.Skip("the corpus runs with -impl=python or -impl=go (make conformance)")
	case *impl != "python" && *impl != "go":
		t.Fatalf("-impl=%q, want python or go", *impl)
	case *impl == "go" && *bin == "":
		t.Fatal("-impl=go needs -bin, the directory of the Go commands")
	}
	repo, err := filepath.Abs("..")
	if err != nil {
		t.Fatalf("locate the repository root: %v", err)
	}
	goBin := ""
	if *impl == "go" {
		if goBin, err = filepath.Abs(*bin); err != nil {
			t.Fatalf("locate the Go commands: %v", err)
		}
	}
	dirs, err := filepath.Glob("testdata/*")
	if err != nil {
		t.Fatalf("list the commands: %v", err)
	}
	for _, dir := range dirs {
		t.Run(filepath.Base(dir), func(t *testing.T) {
			testscript.Run(t, params(dir, repo, goBin))
		})
	}
}

// params returns the testscript parameters for the cases in directory dir.
// For the Go implementation, goBin is the absolute directory of the Go
// commands; it is empty for the Python implementation.
func params(dir, repo, goBin string) testscript.Params {
	return testscript.Params{
		Dir: dir,
		Setup: func(env *testscript.Env) error {
			env.Setenv("REPO", repo)
			return nil
		},
		Condition: func(cond string) (bool, error) {
			if cond != "python" && cond != "go" {
				return false, errors.New("unknown condition " + strconv.Quote(cond))
			}
			return cond == *impl, nil
		},
		Cmds: map[string]func(ts *testscript.TestScript, neg bool, args []string){
			"fault": func(ts *testscript.TestScript, neg bool, args []string) {
				fault(ts, neg, args, repo, goBin)
			},
			"exits": func(ts *testscript.TestScript, neg bool, args []string) {
				exits(ts, neg, args, goBin)
			},
			"cmpjson": cmpjson,
			"glob":    glob,
		},
	}
}

// fault runs the tool-failure contract through a test-only driver. Go ports
// must supply their driver; a missing driver never falls back to Python.
func fault(ts *testscript.TestScript, neg bool, args []string, repo, goBin string) {
	if neg || len(args) != 1 {
		ts.Fatalf("usage: fault <command>")
	}
	if goBin == "" {
		exits(ts, false, []string{"3", "python3", filepath.Join(repo, "conformance", "python_fault.py"), args[0]}, "")
		return
	}
	if *faultBin == "" {
		ts.Fatalf("Go tool-failure cases require -fault-bin with test-only command drivers")
	}
	dir, err := filepath.Abs(*faultBin)
	ts.Check(err)
	exits(ts, false, []string{"3", args[0]}, dir)
}

// exits runs a command of the implementation under test and checks its exit
// status:
//
//	exits <status> <command> [<argument>...]
//
// The stdout and stderr commands then check the output of the command.
func exits(ts *testscript.TestScript, neg bool, args []string, goBin string) {
	if neg || len(args) < 2 {
		ts.Fatalf("usage: exits <status> <command> [<argument>...]")
	}
	want, err := strconv.Atoi(args[0])
	ts.Check(err)
	command, err := commandPath(goBin, args[1])
	ts.Check(err)
	got := 0
	if err := ts.Exec(command, args[2:]...); err != nil {
		exitErr, ok := errors.AsType[*exec.ExitError](err)
		if !ok {
			ts.Fatalf("run %s: %v", args[1], err)
		}
		got = exitErr.ExitCode()
	}
	if got != want {
		ts.Fatalf("%s: exit status %d, want %d", args[1], got, want)
	}
}

// commandPath returns the command to run for name. For the Go
// implementation, it is the executable name in the directory goBin, so that a
// missing Go command never falls back to a Python command on PATH. For the
// Python implementation, goBin is empty, and PATH finds name.
func commandPath(goBin, name string) (string, error) {
	if goBin == "" {
		return name, nil
	}
	path := filepath.Join(goBin, name)
	if _, err := exec.LookPath(path); err != nil {
		return "", fmt.Errorf("the Go command %s is not in -bin: %w", name, err)
	}
	return path, nil
}

// cmpjson compares two JSON documents by their decoded content:
//
//	cmpjson <file> <file>
//
// The names stdout and stderr name the output of the last command.
func cmpjson(ts *testscript.TestScript, neg bool, args []string) {
	if neg || len(args) != 2 {
		ts.Fatalf("usage: cmpjson <file> <file>")
	}
	got, want := decodeJSON(ts, args[0]), decodeJSON(ts, args[1])
	if diff := cmp.Diff(want, got); diff != "" {
		ts.Fatalf("%s and %s differ (-%s +%s):\n%s", args[0], args[1], args[1], args[0], diff)
	}
}

// glob sets a variable to the one path that a pattern matches:
//
//	glob <variable> <pattern>
//
// A release directory has the pack version in its name, and the version of a
// hosted pack changes with each release of env-packs.
func glob(ts *testscript.TestScript, neg bool, args []string) {
	if neg || len(args) != 2 {
		ts.Fatalf("usage: glob <variable> <pattern>")
	}
	matches, err := filepath.Glob(ts.MkAbs(args[1]))
	ts.Check(err)
	if len(matches) != 1 {
		ts.Fatalf("%s matches %d paths, want 1", args[1], len(matches))
	}
	ts.Setenv(args[0], matches[0])
}

// decodeJSON decodes the JSON document in the file name.
func decodeJSON(ts *testscript.TestScript, name string) any {
	var v any
	if err := json.Unmarshal([]byte(ts.ReadFile(name)), &v); err != nil {
		ts.Fatalf("decode %s: %v", name, err)
	}
	return v
}

// pythonSkip matches a line of a script that skips the Python implementation,
// and deviation matches the reason that such a skip must give.
var (
	pythonSkip = regexp.MustCompile(`(?m)^\[python\]\s+skip\b(.*)$`)
	deviation  = regexp.MustCompile(`^\s+'deviation: [^']+ \(#\d+\)'\s*$`)
)

// TestPythonSkipsNameAnIssue checks that each case that skips the Python
// implementation gives the deviation and the issue that resolves it.
func TestPythonSkipsNameAnIssue(t *testing.T) {
	files, err := filepath.Glob("testdata/*/*.txtar")
	if err != nil {
		t.Fatalf("list the cases: %v", err)
	}
	for _, file := range files {
		archive, err := txtar.ParseFile(file)
		if err != nil {
			t.Fatalf("parse %s: %v", file, err)
		}
		for _, m := range pythonSkip.FindAllStringSubmatch(string(archive.Comment), -1) {
			if !deviation.MatchString(m[1]) {
				t.Errorf("%s: %q, want [python] skip 'deviation: <reason> (#<issue>)'", file, m[0])
			}
		}
	}
}

// TestCommandPath checks that a Go command must be in -bin, also when PATH
// has a command with the same name.
func TestCommandPath(t *testing.T) {
	goBin, other := t.TempDir(), t.TempDir()
	for _, file := range []string{filepath.Join(goBin, "raes-pack-check"), filepath.Join(other, "raes-pack-kit")} {
		if err := os.WriteFile(file, []byte("#!/bin/sh\n"), 0o700); err != nil { //nolint:gosec // G306 false positive: the test makes an executable script in its own directory.
			t.Fatalf("write %s: %v", file, err)
		}
	}
	t.Setenv("PATH", other)
	if got, err := commandPath(goBin, "raes-pack-check"); err != nil || got != filepath.Join(goBin, "raes-pack-check") {
		t.Errorf("commandPath(raes-pack-check) = %q, %v; want the command in -bin", got, err)
	}
	if got, err := commandPath(goBin, "raes-pack-kit"); err == nil {
		t.Errorf("commandPath(raes-pack-kit) = %q, nil; want an error for a command that is only on PATH", got)
	}
	if got, err := commandPath("", "raes-pack-kit"); err != nil || got != "raes-pack-kit" {
		t.Errorf("commandPath() for Python = %q, %v; want the bare name", got, err)
	}
}

// directExec matches a line of a script that runs a command of the
// implementation without exits.
var directExec = regexp.MustCompile(`(?m)^\s*!?\s*\??\s*exec\s+raes-`)

// TestCasesRunCommandsThroughExits checks that each case runs the commands of
// the implementation through exits, which selects the implementation.
func TestCasesRunCommandsThroughExits(t *testing.T) {
	files, err := filepath.Glob("testdata/*/*.txtar")
	if err != nil || len(files) == 0 {
		t.Fatalf("list the cases: %v, %d files", err, len(files))
	}
	for _, file := range files {
		archive, err := txtar.ParseFile(file)
		if err != nil {
			t.Fatalf("parse %s: %v", file, err)
		}
		if m := directExec.Find(archive.Comment); m != nil {
			t.Errorf("%s: %q runs a command of the implementation without exits", file, m)
		}
	}
}
