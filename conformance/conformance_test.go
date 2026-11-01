package conformance

import (
	"encoding/json"
	"errors"
	"flag"
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
	impl = flag.String("impl", "", "the implementation under test: python or go")
	bin  = flag.String("bin", "", "the `directory` of the Go commands, for -impl=go")
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
	dirs, err := filepath.Glob("testdata/*")
	if err != nil {
		t.Fatalf("list the commands: %v", err)
	}
	for _, dir := range dirs {
		t.Run(filepath.Base(dir), func(t *testing.T) {
			testscript.Run(t, params(dir, repo))
		})
	}
}

// params returns the testscript parameters for the cases in directory dir.
func params(dir, repo string) testscript.Params {
	return testscript.Params{
		Dir: dir,
		Setup: func(env *testscript.Env) error {
			env.Setenv("REPO", repo)
			if *impl == "go" {
				env.Setenv("PATH", *bin+string(os.PathListSeparator)+env.Getenv("PATH"))
			}
			return nil
		},
		Condition: func(cond string) (bool, error) {
			if cond != "python" && cond != "go" {
				return false, errors.New("unknown condition " + strconv.Quote(cond))
			}
			return cond == *impl, nil
		},
		Cmds: map[string]func(ts *testscript.TestScript, neg bool, args []string){
			"exits":   exits,
			"cmpjson": cmpjson,
			"glob":    glob,
		},
	}
}

// exits runs a command and checks its exit status:
//
//	exits <status> <command> [<argument>...]
//
// The stdout and stderr commands then check the output of the command.
func exits(ts *testscript.TestScript, neg bool, args []string) {
	if neg || len(args) < 2 {
		ts.Fatalf("usage: exits <status> <command> [<argument>...]")
	}
	want, err := strconv.Atoi(args[0])
	ts.Check(err)
	got := 0
	if err := ts.Exec(args[1], args[2:]...); err != nil {
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
