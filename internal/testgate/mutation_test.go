package testgate

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/OpenRAE/env-packs/internal/report"
	"github.com/google/go-cmp/cmp"
)

// gateSource is the original source of the mutants in the tests.
const gateSource = "package a\n\nfunc F(x int) int {\n\tif x > 0 {\n\t\treturn 1\n\t}\n\treturn 0\n}\n"

// gateDiff changes lines 4 and 5 of a.go, and a test file.
const gateDiff = `diff --git a/a.go b/a.go
--- a/a.go
+++ b/a.go
@@ -4,2 +4,2 @@ func F(x int) int {
-	if x > 1 {
-		return 2
+	if x > 0 {
+		return 1
diff --git a/a_test.go b/a_test.go
--- a/a_test.go
+++ b/a_test.go
@@ -1 +1 @@
-package a
+package a // test
`

const gateRecords = `version: 1
equivalents:
  - file: a.go
    function: F
    mutator: numbers/incrementer
    line: return 1
    mutated: return 2
    reason: The caller ignores the value.
`

// escapedMutant returns an escaped mutant of gateSource in file a.go.
func escapedMutant(mutator, old, replacement string) mutant {
	var m mutant
	m.Mutator.Name = mutator
	m.Mutator.File = "a.go"
	m.Mutator.Original = gateSource
	m.Mutator.Mutated = strings.Replace(gateSource, old, replacement, 1)
	return m
}

// gateReport returns a go-mutesting report with three killed mutants, two on
// the changed lines, and four escaped mutants: one on a changed line, one
// outside the changed lines, one with the original source, and one that
// gateRecords records.
func gateReport(t *testing.T) string {
	t.Helper()
	var r mutestingReport
	r.Stats.Total, r.Stats.Killed, r.Stats.NotCompiled, r.Stats.Escaped = 10, 3, 1, 4
	r.Killed = []mutant{
		escapedMutant("expression/comparison", "x > 0", "x < 0"),
		escapedMutant("numbers/decrementer", "return 1", "return 0"),
		escapedMutant("numbers/decrementer", "return 0", "return -1"),
	}
	r.Escaped = []mutant{
		escapedMutant("numbers/incrementer", "return 1", "return 2"),
		escapedMutant("numbers/incrementer", "return 0", "return 1"),
		escapedMutant("branch/case", "", ""),
		escapedMutant("expression/comparison", "x > 0", "x >= 0"),
	}
	data, _ := json.Marshal(r)
	return string(data)
}

// gate is the state of a fake repository for the mutation gate.
type gate struct {
	t       *testing.T
	diff    string
	files   string
	records string
	report  string
	// fail maps the start of a command line to the result of that command.
	fail map[string]Result
	// answer replaces respond when it is set.
	answer func(c Command) (Result, error)
}

// runner returns a fake runner that acts like git and go-mutesting. A test
// can wrap its answers with answer.
func (g *gate) runner() *fakeRunner {
	if g.answer != nil {
		return &fakeRunner{answer: g.answer}
	}
	return &fakeRunner{answer: g.respond}
}

// respond answers one command like git and go-mutesting.
func (g *gate) respond(c Command) (Result, error) {
	{
		line := c.String()
		for prefix, res := range g.fail {
			if strings.HasPrefix(line, prefix) {
				return res, nil
			}
		}
		switch {
		case strings.HasPrefix(line, "git rev-parse "):
			return ok("base0123\n")
		case strings.HasPrefix(line, "git diff "):
			return ok(g.diff)
		case strings.HasPrefix(line, "git ls-tree "):
			return ok(g.files)
		case strings.HasPrefix(line, "git worktree add "):
			g.write(c.Args[4], RecordsFile, g.records)
		case strings.HasPrefix(line, "go-mutesting "):
			g.write(c.Dir, "report.json", g.report)
		}
		return ok("")
	}
}

// write writes a file into dir, and makes dir. Empty content writes nothing.
func (g *gate) write(dir, name, content string) {
	g.t.Helper()
	if err := os.MkdirAll(dir, 0o700); err != nil {
		g.t.Fatalf("make %s: %v", dir, err)
	}
	if content == "" {
		return
	}
	if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o600); err != nil {
		g.t.Fatalf("write %s: %v", name, err)
	}
}

func newGate(t *testing.T) *gate {
	t.Helper()
	return &gate{t: t, diff: gateDiff, records: gateRecords, report: gateReport(t)}
}

func gateOptions(t *testing.T) MutationOptions {
	t.Helper()
	return MutationOptions{Repo: "repo", Base: "origin/main", Exec: "/bin/testgate", TempDir: t.TempDir(), Timeout: 90 * time.Second, MemoryMiB: 4096}
}

func TestMutation(t *testing.T) {
	g := newGate(t)
	r := g.runner()
	opts := gateOptions(t)
	got, err := Mutation(context.Background(), r, opts)
	if err != nil {
		t.Fatalf("Mutation() error = %v", err)
	}
	want := MutationResult{
		Findings: []report.Finding{{
			Location: "a.go:4",
			Rule:     RuleMutant,
			Message:  `no test kills the expression/comparison mutant in F: "if x > 0 {" becomes "if x >= 0 {"`,
			Fix:      "Add a test that fails with the mutant. If no test can observe the change, record the mutant in mutation.yaml with the reason.",
		}},
		Files: 1, Mutants: 10, Skipped: 3, Killed: 2, NotCompiled: 1, Escaped: 2, Equivalent: 1,
		Packages: []PackageScore{{Dir: ".", Killed: 2, Survived: 1, Equivalent: 1}},
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("Mutation() mismatch (-want +got):\n%s", diff)
	}
	var lines []string
	for _, c := range r.commands {
		lines = append(lines, strings.ReplaceAll(c.String(), opts.TempDir, "TMP"))
	}
	tree := r.commands[2].Args[4]
	if r.commands[3].Dir != tree {
		t.Errorf("go-mutesting ran in %s, want the worktree %s", r.commands[3].Dir, tree)
	}
	wantLines := []string{
		"git rev-parse --verify --end-of-options origin/main^{commit}",
		"git diff -U0 --no-color --no-ext-diff --no-textconv --find-renames --diff-algorithm=myers --src-prefix=a/ --dst-prefix=b/ --merge-base base0123 HEAD -- *.go",
		"git worktree add --detach --quiet " + strings.ReplaceAll(tree, opts.TempDir, "TMP") + " HEAD",
		"go-mutesting --config=" + strings.ReplaceAll(tree, opts.TempDir, "TMP") + "/.testgate-go-mutesting.yaml --exec=/bin/testgate exec -memory 4096 --exec-timeout=90 -- a.go",
		"git worktree remove --force " + strings.ReplaceAll(tree, opts.TempDir, "TMP"),
	}
	if diff := cmp.Diff(wantLines, lines); diff != "" {
		t.Errorf("Mutation() commands mismatch (-want +got):\n%s", diff)
	}
	if entries, err := os.ReadDir(opts.TempDir); err != nil || len(entries) != 0 {
		t.Errorf("Mutation() left %v, %v in the temporary directory, want nothing", entries, err)
	}
}

func TestMutationConfig(t *testing.T) {
	g := newGate(t)
	r := g.runner()
	var config string
	answer := r.answer
	r.answer = func(c Command) (Result, error) {
		if c.Name == "go-mutesting" {
			data, err := os.ReadFile(strings.TrimPrefix(c.Args[0], "--config="))
			if err != nil {
				t.Fatalf("read the go-mutesting configuration: %v", err)
			}
			config = string(data)
		}
		return answer(c)
	}
	if _, err := Mutation(context.Background(), r, gateOptions(t)); err != nil {
		t.Fatalf("Mutation() error = %v", err)
	}
	if config != mutestingConfig || !strings.Contains(config, "skip_without_test: false") {
		t.Errorf("go-mutesting configuration = %q, want %q", config, mutestingConfig)
	}
}

func TestMutationLinesFile(t *testing.T) {
	for _, all := range []bool{false, true} {
		g := newGate(t)
		g.files = "a.go\x00"
		r := g.runner()
		var lines string
		var found bool
		r.answer = func(c Command) (Result, error) {
			if c.Name == "go-mutesting" {
				data, err := os.ReadFile(filepath.Join(c.Dir, linesFile))
				lines, found = string(data), err == nil
			}
			return g.respond(c)
		}
		opts := gateOptions(t)
		opts.All = all
		if _, err := Mutation(context.Background(), r, opts); err != nil {
			t.Fatalf("Mutation(all=%v) error = %v", all, err)
		}
		if want := `{"a.go":{"4":true,"5":true},"a_test.go":{"1":true}}`; !all && (!found || lines != want) {
			t.Errorf("Mutation() changed lines file = %q, %v; want %q", lines, found, want)
		}
		if all && found {
			t.Errorf("Mutation(-all) wrote the changed lines file %q, want no file", lines)
		}
	}
}

func TestMutationAll(t *testing.T) {
	g := newGate(t)
	g.files = "README.md\x00a.go\x00a_test.go\x00b.go\x00testdata/x.go\x00"
	g.records = gateRecords + `  - file: b.go
    function: G
    mutator: branch/if
    line: if y {
    mutated: if y {}
    reason: Stale.
`
	r := g.runner()
	opts := gateOptions(t)
	opts.All, opts.Base = true, ""
	got, err := Mutation(context.Background(), r, opts)
	if err != nil {
		t.Fatalf("Mutation(-all) error = %v", err)
	}
	var messages []string
	for _, f := range report.Sort(got.Findings) {
		messages = append(messages, f.Location+": "+f.Message)
	}
	want := []string{
		`a.go:4: no test kills the expression/comparison mutant in F: "if x > 0 {" becomes "if x >= 0 {"`,
		`a.go:7: no test kills the numbers/incrementer mutant in F: "return 0" becomes "return 1"`,
		`mutation.yaml: record 2 (b.go, "if y {") matches no surviving mutant`,
	}
	if diff := cmp.Diff(want, messages); diff != "" {
		t.Errorf("Mutation(-all) findings mismatch (-want +got):\n%s", diff)
	}
	if got.Files != 2 || got.Equivalent != 1 {
		t.Errorf("Mutation(-all) = %d files, %d equivalent; want 2 and 1", got.Files, got.Equivalent)
	}
	if line := r.commands[0].String(); line != "git ls-tree -r -z --name-only HEAD" {
		t.Errorf("Mutation(-all) first command = %q, want git ls-tree", line)
	}
	if args := r.commands[2].Args; strings.Join(args[len(args)-3:], " ") != "-- a.go b.go" {
		t.Errorf("Mutation(-all) go-mutesting arguments = %q, want the two files", args)
	}
}

func TestMutationNothingToMutate(t *testing.T) {
	g := newGate(t)
	g.diff = "diff --git a/a_test.go b/a_test.go\n--- a/a_test.go\n+++ b/a_test.go\n@@ -1 +1 @@\n-x\n+y\n"
	r := g.runner()
	got, err := Mutation(context.Background(), r, gateOptions(t))
	if err != nil || got.Files != 0 || len(got.Findings) != 0 || len(r.commands) != 2 {
		t.Errorf("Mutation() without changed code = %+v, %v after %d commands; want an empty result after 2", got, err, len(r.commands))
	}
}

func TestMutationErrors(t *testing.T) {
	tests := []struct {
		name    string
		change  func(g *gate, opts *MutationOptions)
		wantErr string
	}{
		{
			name: "bad base",
			change: func(g *gate, _ *MutationOptions) {
				g.fail = map[string]Result{"git rev-parse": {ExitCode: 128, Stderr: []byte("bad revision")}}
			},
			wantErr: "bad revision",
		},
		{
			name: "failing diff",
			change: func(g *gate, _ *MutationOptions) {
				g.fail = map[string]Result{"git diff": {ExitCode: 129, Stderr: []byte("bad diff")}}
			},
			wantErr: "bad diff",
		},
		{
			name: "failing file list",
			change: func(g *gate, opts *MutationOptions) {
				opts.All = true
				g.fail = map[string]Result{"git ls-tree": {ExitCode: 128, Stderr: []byte("no HEAD")}}
			},
			wantErr: "no HEAD",
		},
		{
			name:    "exec path with a space",
			change:  func(_ *gate, opts *MutationOptions) { opts.Exec = "/my tools/testgate" },
			wantErr: "has white space",
		},
		{
			name:    "missing temporary directory",
			change:  func(_ *gate, opts *MutationOptions) { opts.TempDir = filepath.Join(opts.TempDir, "missing") },
			wantErr: "make a temporary directory",
		},
		{
			name: "failing worktree",
			change: func(g *gate, _ *MutationOptions) {
				g.fail = map[string]Result{"git worktree add": {ExitCode: 128, Stderr: []byte("locked")}}
			},
			wantErr: "locked",
		},
		{
			name: "worktree that cannot be written",
			change: func(g *gate, _ *MutationOptions) {
				g.records = ""
				g.answer = func(c Command) (Result, error) {
					res, err := g.respond(c)
					if strings.HasPrefix(c.String(), "git worktree add ") {
						err = errors.Join(err, os.Chmod(c.Args[4], 0o400))
					}
					return res, err
				}
			},
			wantErr: "write the go-mutesting configuration",
		},
		{
			name: "changed lines that cannot be written",
			change: func(g *gate, _ *MutationOptions) {
				g.answer = func(c Command) (Result, error) {
					res, err := g.respond(c)
					if strings.HasPrefix(c.String(), "git worktree add ") {
						err = errors.Join(err, os.Mkdir(filepath.Join(c.Args[4], linesFile), 0o700))
					}
					return res, err
				}
			},
			wantErr: "write the changed lines",
		},
		{
			name: "failing go-mutesting",
			change: func(g *gate, _ *MutationOptions) {
				g.fail = map[string]Result{"go-mutesting": {ExitCode: 1, Stderr: []byte("cannot load")}}
			},
			wantErr: "cannot load",
		},
		{
			name:    "missing report",
			change:  func(g *gate, _ *MutationOptions) { g.report = "" },
			wantErr: "read the go-mutesting report",
		},
		{
			name:    "invalid report",
			change:  func(g *gate, _ *MutationOptions) { g.report = "{" },
			wantErr: "decode the go-mutesting report",
		},
		{
			name:    "failed exec step",
			change:  func(g *gate, _ *MutationOptions) { g.report = `{"stats":{"errorCount":1}}` },
			wantErr: "the exec step failed for 1 mutants",
		},
		{
			name:    "missing records",
			change:  func(g *gate, _ *MutationOptions) { g.records = "" },
			wantErr: "read mutation.yaml",
		},
		{
			name:    "invalid records",
			change:  func(g *gate, _ *MutationOptions) { g.records = "version: 1\nequivalent: []\n" },
			wantErr: "decode mutation.yaml",
		},
		{
			name:    "mutant of another file",
			change:  func(g *gate, _ *MutationOptions) { g.report = `{"escaped":[{"mutator":{"originalFilePath":"z.go"}}]}` },
			wantErr: "go-mutesting reported a mutant of z.go, which the gate did not mutate",
		},
		{
			name: "mutant that does not parse",
			change: func(g *gate, _ *MutationOptions) {
				g.report = `{"escaped":[{"mutator":{"originalFilePath":"a.go","originalSourceCode":"package\n\n\n}\n","mutatedSourceCode":"package\n\n\n{\n"}}]}`
			},
			wantErr: "parse a.go",
		},
		{
			name: "failing worktree removal",
			change: func(g *gate, _ *MutationOptions) {
				g.fail = map[string]Result{"git worktree remove": {ExitCode: 128, Stderr: []byte("busy")}}
			},
			wantErr: "busy",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			g := newGate(t)
			opts := gateOptions(t)
			tt.change(g, &opts)
			_, err := Mutation(context.Background(), g.runner(), opts)
			if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Errorf("Mutation() error = %v, want an error with %q", err, tt.wantErr)
			}
		})
	}
}

func TestMutationRunnerFailure(t *testing.T) {
	failure := errors.New("no git")
	r := &fakeRunner{answer: func(Command) (Result, error) { return Result{}, failure }}
	if _, err := Mutation(context.Background(), r, gateOptions(t)); !errors.Is(err, failure) {
		t.Errorf("Mutation() with a failing runner: error = %v, want %v", err, failure)
	}
}

func TestEvaluateRecordFindings(t *testing.T) {
	got, err := evaluate(mutestingReport{}, nil, nil, Records{Version: 2}, false)
	if err != nil || len(got.Findings) != 1 || got.Findings[0].Rule != RuleRecord {
		t.Errorf("evaluate() with a bad version = %+v, %v; want one record finding", got, err)
	}
}

func TestSurvivorFindingOutsideAFunction(t *testing.T) {
	f := survivorFinding(Survivor{File: "a.go", Mutator: "numbers/incrementer", Start: 3, Line: "const n = 1", Mutated: "const n = 2"})
	if f.Location != "a.go:3" || f.Message != `no test kills the numbers/incrementer mutant outside a function: "const n = 1" becomes "const n = 2"` {
		t.Errorf("survivorFinding() = %+v, want the place outside a function", f)
	}
}

func TestPackageScore(t *testing.T) {
	tests := []struct {
		score PackageScore
		want  float64
		ok    bool
	}{
		{score: PackageScore{Killed: 3}, want: 100, ok: true},
		{score: PackageScore{Killed: 1, Survived: 3, Equivalent: 9}, want: 25, ok: true},
		{score: PackageScore{Survived: 2}, want: 0, ok: true},
		{score: PackageScore{Equivalent: 2}},
	}
	for _, tt := range tests {
		if got, ok := tt.score.Score(); got != tt.want || ok != tt.ok {
			t.Errorf("%+v.Score() = %v, %v, want %v, %v", tt.score, got, ok, tt.want, tt.ok)
		}
	}
}

func TestEvaluatePackages(t *testing.T) {
	killed := func(file string) mutant {
		m := escapedMutant("branch/if", "x > 0", "x < 0")
		m.Mutator.File = file
		return m
	}
	rep := mutestingReport{Killed: []mutant{killed("b/b.go"), killed("a/a.go"), killed("b/c.go")}}
	got, err := evaluate(rep, []string{"a/a.go", "b/b.go", "b/c.go"}, nil, Records{Version: 1}, true)
	want := []PackageScore{{Dir: "a", Killed: 1}, {Dir: "b", Killed: 2}}
	if err != nil {
		t.Fatalf("evaluate() error = %v", err)
	}
	if diff := cmp.Diff(want, got.Packages); diff != "" {
		t.Errorf("evaluate() packages mismatch (-want +got):\n%s", diff)
	}
}

// TestEvaluateOneRecordPerMutant checks that a record covers one mutant, so
// that a second identical mutant needs its own record.
func TestEvaluateOneRecordPerMutant(t *testing.T) {
	m := escapedMutant("numbers/incrementer", "return 1", "return 2")
	records, err := ParseRecords([]byte(gateRecords))
	if err != nil {
		t.Fatalf("ParseRecords() error = %v", err)
	}
	got, err := evaluate(mutestingReport{Escaped: []mutant{m, m}}, []string{"a.go"}, nil, records, true)
	if err != nil {
		t.Fatalf("evaluate() error = %v", err)
	}
	if got.Equivalent != 1 || len(got.Findings) != 1 || got.Findings[0].Location != "a.go:5" {
		t.Errorf("evaluate() of two identical mutants with one record = %d equivalent, findings %v; want 1 and one finding at a.go:5",
			got.Equivalent, got.Findings)
	}
	records.Equivalents = append(records.Equivalents, records.Equivalents[0])
	got, err = evaluate(mutestingReport{Escaped: []mutant{m, m}}, []string{"a.go"}, nil, records, true)
	if err != nil || got.Equivalent != 2 || len(got.Findings) != 0 {
		t.Errorf("evaluate() of two identical mutants with two records = %d equivalent, findings %v, %v; want 2 and none",
			got.Equivalent, got.Findings, err)
	}
}
