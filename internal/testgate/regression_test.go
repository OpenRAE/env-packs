package testgate

import (
	"context"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

// regressionSource is the test file pkg/a_test.go at HEAD. The comments
// give the line numbers that the tests use.
const regressionSource = `package pkg

import "testing"

// TestA checks the fix.
// Regression test for #12.
func TestA(t *testing.T) {}

// Regression test for #13.
func TestB(t *testing.T) {}

// Regression test for #14.
func TestC(t *testing.T) {}

// Regression test for #15.
func TestD(t *testing.T) {}

// Regression test for #16.
func TestUnchanged(t *testing.T) {}

// Regression test for #17.
func helper() {}

type s struct{}

// Regression test for #18.
func (s) TestMethod(t *testing.T) {}

// Testing is not a test. Regression test for #19.
func Testing(t *testing.T) {}

// TestNoMarker has no marker.
func TestNoMarker(t *testing.T) {}
`

// regressionDiff changes the doc comment of TestA (line 6), TestB (line 10),
// TestC (lines 12 and 13), TestD (line 16), and lines 21 to 33. It does not
// change TestUnchanged. It also changes a test file in testdata.
const regressionDiff = `diff --git a/pkg/a_test.go b/pkg/a_test.go
--- a/pkg/a_test.go
+++ b/pkg/a_test.go
@@ -6 +6 @@
@@ -10 +10 @@
@@ -12,2 +12,2 @@
@@ -16 +16 @@
@@ -21,0 +21,13 @@
diff --git a/a/testdata/f_test.go b/a/testdata/f_test.go
--- a/a/testdata/f_test.go
+++ b/a/testdata/f_test.go
@@ -1 +1 @@
`

// regressionEvents is the go test -json output on the merge base.
const regressionEvents = `{"Action":"start","Package":"example.com/m/pkg"}
{"Action":"run","Package":"example.com/m/pkg","Test":"TestA"}
{"Action":"fail","Package":"example.com/m/pkg","Test":"TestA"}
{"Action":"run","Package":"example.com/m/pkg","Test":"TestB"}
{"Action":"pass","Package":"example.com/m/pkg","Test":"TestB"}
{"Action":"run","Package":"example.com/m/pkg","Test":"TestC"}
{"Action":"skip","Package":"example.com/m/pkg","Test":"TestC"}
{"Action":"fail","Package":"example.com/m/pkg"}
`

// regressionRepo is the state of a fake repository for the regression gate.
type regressionRepo struct {
	t      *testing.T
	diff   string
	source string
	events string
	fail   map[string]Result
	// tree is the worktree directory, and copied records the content of the
	// test files there when the tests run.
	tree   string
	copied map[string]string
}

func newRegressionRepo(t *testing.T) *regressionRepo {
	t.Helper()
	return &regressionRepo{t: t, diff: regressionDiff, source: regressionSource, events: regressionEvents}
}

func (g *regressionRepo) runner() *fakeRunner {
	return &fakeRunner{answer: func(c Command) (Result, error) {
		line := c.String()
		for prefix, res := range g.fail {
			if strings.HasPrefix(line, prefix) {
				return res, nil
			}
		}
		switch {
		case strings.HasPrefix(line, "git rev-parse "):
			return ok("base0123\n")
		case strings.HasPrefix(line, "git diff -U0 "):
			return ok(g.diff)
		case line == "git show HEAD:pkg/a_test.go":
			return ok(g.source)
		case line == "git show HEAD:pkg/testdata/in.txt":
			return ok("input")
		case strings.HasPrefix(line, "git merge-base "):
			return ok("merge0123456789abcdef\n")
		case strings.HasPrefix(line, "git worktree add "):
			g.tree = c.Args[4]
			g.write("pkg/old_test.go", "package pkg\n")
			g.write("pkg/a_test.go", "package pkg // base\n")
		case strings.HasPrefix(line, "git diff --name-only -z --no-renames --diff-filter=D "):
			return ok("pkg/a.go.orig\x00pkg/old_test.go\x00")
		case strings.HasPrefix(line, "git diff --name-only -z --no-renames --diff-filter=d "):
			return ok("pkg/a.go\x00pkg/a_test.go\x00pkg/testdata/in.txt\x00other/b_test.go\x00")
		case strings.HasPrefix(line, "go test "):
			g.copied = g.snapshot()
			return Result{Stdout: []byte(g.events), ExitCode: 1}, nil
		}
		return ok("")
	}}
}

func (g *regressionRepo) write(name, content string) {
	g.t.Helper()
	file := filepath.Join(g.tree, name)
	if err := os.MkdirAll(filepath.Dir(file), 0o700); err != nil {
		g.t.Fatalf("make the directory of %s: %v", name, err)
	}
	if err := os.WriteFile(file, []byte(content), 0o600); err != nil {
		g.t.Fatalf("write %s: %v", name, err)
	}
}

// snapshot returns the files of the worktree and their content.
func (g *regressionRepo) snapshot() map[string]string {
	g.t.Helper()
	files := make(map[string]string)
	tree := os.DirFS(g.tree)
	err := fs.WalkDir(tree, ".", func(name string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		data, err := fs.ReadFile(tree, name)
		files[name] = string(data)
		return err
	})
	if err != nil {
		g.t.Fatalf("read the worktree: %v", err)
	}
	return files
}

func regressionOptions(t *testing.T) RegressionOptions {
	t.Helper()
	return RegressionOptions{Repo: "repo", Base: "origin/main", TempDir: t.TempDir()}
}

func TestRegression(t *testing.T) {
	g := newRegressionRepo(t)
	r := g.runner()
	got, err := Regression(context.Background(), r, regressionOptions(t))
	if err != nil {
		t.Fatalf("Regression() error = %v", err)
	}
	finding := func(line, problem string) Finding {
		return Finding{
			Location: "pkg/a_test.go:" + line,
			Rule:     RuleRegression,
			Message:  "regression test " + problem + " on the merge base merge0123456",
			Fix:      "Make the test fail without the fix. Write it against the API of the merge base, and do not skip it.",
		}
	}
	want := RegressionResult{
		Findings: []Finding{finding("10", "TestB passes"), finding("13", "TestC skips"), finding("16", "TestD does not run")},
		Tests:    4,
		Proven:   1,
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("Regression() mismatch (-want +got):\n%s", diff)
	}
	wantFiles := map[string]string{"pkg/a_test.go": regressionSource, "pkg/testdata/in.txt": "input"}
	if diff := cmp.Diff(wantFiles, g.copied); diff != "" {
		t.Errorf("Regression() worktree files mismatch (-want +got):\n%s", diff)
	}
	var testCommand Command
	for _, c := range r.commands {
		if c.Name == "go" {
			testCommand = c
		}
	}
	if testCommand.Dir != g.tree || testCommand.String() != "go test -json -count=1 -run ^(TestA|TestB|TestC|TestD)$ ./pkg" {
		t.Errorf("Regression() test command = %+v, want the four tests of ./pkg in the worktree", testCommand)
	}
}

func TestRegressionTwoPackages(t *testing.T) {
	g := newRegressionRepo(t)
	g.diff = `diff --git a/p/a_test.go b/p/a_test.go
--- a/p/a_test.go
+++ b/p/a_test.go
@@ -6 +6 @@
diff --git a/q/a_test.go b/q/a_test.go
--- a/q/a_test.go
+++ b/q/a_test.go
@@ -6 +6 @@
`
	r := g.runner()
	answer := r.answer
	r.answer = func(c Command) (Result, error) {
		line := c.String()
		switch {
		case line == "git show HEAD:p/a_test.go" || line == "git show HEAD:q/a_test.go":
			return ok(regressionSource)
		case strings.HasPrefix(line, "git diff --name-only"):
			return ok("")
		case strings.HasPrefix(line, "go test "):
			return Result{Stdout: []byte(regressionEvents), ExitCode: 1}, nil
		}
		return answer(c)
	}
	got, err := Regression(context.Background(), r, regressionOptions(t))
	if err != nil || got.Tests != 2 || got.Proven != 2 || len(got.Findings) != 0 {
		t.Errorf("Regression() of two packages = %+v, %v; want two proven tests", got, err)
	}
}

func TestRegressionBuildFailure(t *testing.T) {
	g := newRegressionRepo(t)
	g.events = buildFailOutput
	got, err := Regression(context.Background(), g.runner(), regressionOptions(t))
	if err != nil {
		t.Fatalf("Regression() error = %v", err)
	}
	if len(got.Findings) != 4 || got.Proven != 0 || !strings.Contains(got.Findings[0].Message, "TestA does not compile") {
		t.Errorf("Regression() of tests that do not compile = %+v, want four findings", got)
	}
}

func TestRegressionNoTests(t *testing.T) {
	g := newRegressionRepo(t)
	g.diff = strings.Replace(regressionDiff, "@@ -6 +6 @@\n@@ -10 +10 @@\n@@ -12,2 +12,2 @@\n@@ -16 +16 @@\n", "", 1)
	r := g.runner()
	got, err := Regression(context.Background(), r, regressionOptions(t))
	if err != nil || got.Tests != 0 || len(got.Findings) != 0 {
		t.Errorf("Regression() without changed regression tests = %+v, %v; want an empty result", got, err)
	}
	for _, c := range r.commands {
		if strings.HasPrefix(c.String(), "git worktree") {
			t.Errorf("Regression() without changed regression tests ran %q", c)
		}
	}
}

func TestRegressionErrors(t *testing.T) {
	fail := func(prefix, stderr string) func(g *regressionRepo) {
		return func(g *regressionRepo) { g.fail = map[string]Result{prefix: {ExitCode: 128, Stderr: []byte(stderr)}} }
	}
	tests := []struct {
		name    string
		change  func(g *regressionRepo)
		wantErr string
	}{
		{name: "bad base", change: fail("git rev-parse", "bad revision"), wantErr: "bad revision"},
		{name: "failing diff", change: fail("git diff -U0", "bad diff"), wantErr: "bad diff"},
		{name: "failing show", change: fail("git show HEAD:pkg/a_test.go", "no file"), wantErr: "no file"},
		{name: "test file that does not parse", change: func(g *regressionRepo) { g.source = "package" }, wantErr: "pkg/a_test.go"},
		{name: "failing merge base", change: fail("git merge-base", "no merge base"), wantErr: "no merge base"},
		{name: "failing worktree", change: fail("git worktree add", "locked"), wantErr: "locked"},
		{name: "failing list of deleted files", change: fail("git diff --name-only -z --no-renames --diff-filter=D", "bad list"), wantErr: "bad list"},
		{name: "failing list of other files", change: fail("git diff --name-only -z --no-renames --diff-filter=d", "bad list"), wantErr: "bad list"},
		{name: "failing copy", change: fail("git show HEAD:pkg/testdata/in.txt", "no data"), wantErr: "no data"},
		{name: "test output that is not JSON", change: func(g *regressionRepo) { g.events = "FAIL\n" }, wantErr: "decode the output of go test -json"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			g := newRegressionRepo(t)
			tt.change(g)
			_, err := Regression(context.Background(), g.runner(), regressionOptions(t))
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Errorf("Regression() error = %v, want an error with %q", err, tt.wantErr)
			}
		})
	}
}

func TestRegressionRunnerFailure(t *testing.T) {
	g := newRegressionRepo(t)
	failure := errors.New("no go")
	r := g.runner()
	answer := r.answer
	r.answer = func(c Command) (Result, error) {
		if c.Name == "go" {
			return Result{}, failure
		}
		return answer(c)
	}
	if _, err := Regression(context.Background(), r, regressionOptions(t)); !errors.Is(err, failure) {
		t.Errorf("Regression() with a failing go: error = %v, want %v", err, failure)
	}
}

func TestCopyTestFile(t *testing.T) {
	tree := t.TempDir()
	r := &fakeRunner{answer: func(Command) (Result, error) { return ok("data") }}
	if err := copyTestFile(context.Background(), r, "repo", tree, false, "a/b/c_test.go"); err != nil {
		t.Fatalf("copyTestFile() error = %v", err)
	}
	if data, err := readFile(filepath.Join(tree, "a", "b", "c_test.go")); err != nil || string(data) != "data" {
		t.Errorf("copyTestFile() wrote %q, %v; want the content of HEAD", data, err)
	}
	if err := copyTestFile(context.Background(), r, "repo", tree, true, "a/b/c_test.go"); err != nil {
		t.Fatalf("copyTestFile(deleted) error = %v", err)
	}
	if _, err := os.Stat(filepath.Join(tree, "a", "b", "c_test.go")); !errors.Is(err, os.ErrNotExist) {
		t.Errorf("copyTestFile(deleted) left the file: %v", err)
	}
	if err := copyTestFile(context.Background(), r, "repo", tree, true, "missing_test.go"); err == nil {
		t.Error("copyTestFile(deleted) of a missing file: error = nil, want an error")
	}
	if err := os.WriteFile(filepath.Join(tree, "file"), nil, 0o600); err != nil {
		t.Fatalf("write a file: %v", err)
	}
	if err := copyTestFile(context.Background(), r, "repo", tree, false, "file/x_test.go"); err == nil {
		t.Error("copyTestFile() below a file: error = nil, want an error")
	}
}

func TestIsTestName(t *testing.T) {
	tests := map[string]bool{"Test": true, "TestA": true, "Test_a": true, "Test1": true, "Testing": false, "test": false, "TestÄ": true, "Testé": false}
	for name, want := range tests {
		if got := isTestName(name); got != want {
			t.Errorf("isTestName(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestTestFileOf(t *testing.T) {
	tests := []struct {
		file, dir string
		want      bool
	}{
		{file: "pkg/a_test.go", dir: "pkg", want: true},
		{file: "pkg/a.go", dir: "pkg", want: false},
		{file: "pkg/sub/a_test.go", dir: "pkg", want: false},
		{file: "pkg/testdata/x", dir: "pkg", want: true},
		{file: "pkg/testdata/sub/x", dir: "pkg", want: true},
		{file: "pkg/testdatax/x", dir: "pkg", want: false},
		{file: "a_test.go", dir: ".", want: true},
		{file: "testdata/x", dir: ".", want: true},
	}
	for _, tt := range tests {
		if got := testFileOf(tt.file, tt.dir); got != tt.want {
			t.Errorf("testFileOf(%q, %q) = %v, want %v", tt.file, tt.dir, got, tt.want)
		}
	}
}
