package testgate

import (
	"context"
	"errors"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"maps"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"unicode"
	"unicode/utf8"

	"github.com/OpenRAE/env-packs/internal/report"
)

// regressionMarker is the text in the doc comment of a regression test.
var regressionMarker = regexp.MustCompile(`Regression test for #\d+`)

// RegressionOptions configure one run of the regression gate.
type RegressionOptions struct {
	// Repo is the root directory of the git repository and the Go module.
	Repo string
	// Base is the base revision.
	Base string
	// TempDir is the directory for the temporary files of the run.
	TempDir string
}

// RegressionResult is the outcome of one run of the regression gate.
type RegressionResult struct {
	// Findings are the regression tests that do not fail on the merge base.
	Findings []report.Finding
	// Tests counts the regression tests that the change adds or changes.
	Tests int
	// Proven counts the regression tests that fail on the merge base.
	Proven int
}

// A regressionTest is a test function with the regression marker in its doc
// comment.
type regressionTest struct {
	file string
	name string
	line int
}

// Regression runs the regression gate.
func Regression(ctx context.Context, r Runner, opts RegressionOptions) (RegressionResult, error) {
	base, err := revParse(ctx, r, opts.Repo, opts.Base)
	if err != nil {
		return RegressionResult{}, err
	}
	tests, err := changedRegressionTests(ctx, r, opts.Repo, base)
	if err != nil {
		return RegressionResult{}, err
	}
	if len(tests) == 0 {
		return RegressionResult{}, nil
	}
	out, err := runOK(ctx, r, Command{Dir: opts.Repo, Name: "git", Args: []string{"merge-base", base, "HEAD"}})
	if err != nil {
		return RegressionResult{}, err
	}
	mergeBase := strings.TrimSpace(string(out))
	res := RegressionResult{Tests: len(tests)}
	byDir := make(map[string][]regressionTest)
	for _, t := range tests {
		byDir[path.Dir(t.file)] = append(byDir[path.Dir(t.file)], t)
	}
	dirs := slices.Sorted(maps.Keys(byDir))
	err = withWorktree(ctx, r, opts.Repo, opts.TempDir, mergeBase, func(tree string) error {
		if copyErr := copyTestFiles(ctx, r, opts.Repo, tree, base, dirs); copyErr != nil {
			return copyErr
		}
		for _, dir := range dirs {
			if proveErr := proveDir(ctx, r, tree, dir, byDir[dir], mergeBase, &res); proveErr != nil {
				return proveErr
			}
		}
		return nil
	})
	return res, err
}

// changedRegressionTests returns the regression tests that HEAD adds or
// changes since the merge base of base and HEAD. A change that only removes
// lines of a test changes it too. It reads the test files of HEAD, and it
// skips the files in testdata directories.
func changedRegressionTests(ctx context.Context, r Runner, repo, base string) ([]regressionTest, error) {
	diff, err := changedLines(ctx, r, repo, base, "*_test.go")
	if err != nil {
		return nil, err
	}
	files := slices.Concat(slices.Collect(maps.Keys(diff.Added)), slices.Collect(maps.Keys(diff.Removed)))
	slices.Sort(files)
	var tests []regressionTest
	for _, file := range slices.Compact(files) {
		if slices.Contains(strings.Split(file, "/"), "testdata") {
			continue
		}
		src, err := runOK(ctx, r, Command{Dir: repo, Name: "git", Args: []string{"show", "HEAD:" + file}})
		if err != nil {
			return nil, err
		}
		found, err := regressionTests(file, src, diff.Added[file], diff.Removed[file])
		if err != nil {
			return nil, err
		}
		tests = append(tests, found...)
	}
	return tests, nil
}

// regressionTests returns the regression tests of a test file whose
// declaration, with its doc comment, has a changed line, or has a place
// inside it where the change removes lines.
func regressionTests(file string, src []byte, changed Lines, removed []int) ([]regressionTest, error) {
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, file, src, parser.ParseComments|parser.SkipObjectResolution)
	if err != nil {
		return nil, err
	}
	var tests []regressionTest
	for _, d := range f.Decls {
		fn, ok := d.(*ast.FuncDecl)
		if !ok || fn.Recv != nil || !isTestName(fn.Name.Name) || !regressionMarker.MatchString(fn.Doc.Text()) {
			continue
		}
		start, end := fset.Position(fn.Doc.Pos()).Line, fset.Position(fn.End()).Line
		inside := func(place int) bool { return start <= place && place < end }
		if changed.Intersects(start, end) || slices.ContainsFunc(removed, inside) {
			tests = append(tests, regressionTest{file: file, name: fn.Name.Name, line: fset.Position(fn.Pos()).Line})
		}
	}
	return tests, nil
}

// isTestName reports whether name is the name of a test function: Test, or
// Test and a name that does not start with a lowercase letter.
func isTestName(name string) bool {
	rest, ok := strings.CutPrefix(name, "Test")
	first, _ := utf8.DecodeRuneInString(rest)
	return ok && !unicode.IsLower(first)
}

// copyTestFiles copies into the worktree tree each test file and each
// testdata file that HEAD changes in the directories dirs, and removes each
// such file that HEAD deletes. Git reports only clean relative paths.
func copyTestFiles(ctx context.Context, r Runner, repo, tree, base string, dirs []string) error {
	for _, filter := range []string{"D", "d"} {
		out, err := runOK(ctx, r, Command{Dir: repo, Name: "git", Args: append([]string{
			"diff", "--name-only", "-z", "--no-renames", "--diff-filter=" + filter, "--merge-base", base, "HEAD", "--",
		}, dirs...)})
		if err != nil {
			return err
		}
		for file := range strings.SplitSeq(strings.TrimSuffix(string(out), "\x00"), "\x00") {
			if !slices.ContainsFunc(dirs, func(dir string) bool { return testFileOf(file, dir) }) {
				continue
			}
			if err := copyTestFile(ctx, r, repo, tree, filter == "D", file); err != nil {
				return err
			}
		}
	}
	return nil
}

// testFileOf reports whether file is a test file of the package in directory
// dir, or a file in its testdata directory.
func testFileOf(file, dir string) bool {
	return path.Dir(file) == dir && strings.HasSuffix(file, "_test.go") ||
		strings.HasPrefix(file, path.Join(dir, "testdata")+"/")
}

// copyTestFile applies one changed file of HEAD to the worktree tree: it
// removes a deleted file, and writes the content of HEAD for another file.
func copyTestFile(ctx context.Context, r Runner, repo, tree string, deleted bool, file string) error {
	target := filepath.Join(tree, filepath.FromSlash(file))
	if deleted {
		return os.Remove(target)
	}
	data, err := runOK(ctx, r, Command{Dir: repo, Name: "git", Args: []string{"show", "HEAD:" + file}})
	if err != nil {
		return err
	}
	return errors.Join(os.MkdirAll(filepath.Dir(target), 0o700), os.WriteFile(target, data, 0o600))
}

// proveDir runs the regression tests of the package in directory dir of the
// worktree tree. It adds to res a finding for each test that does not fail,
// and counts each test that fails.
func proveDir(ctx context.Context, r Runner, tree, dir string, tests []regressionTest, mergeBase string, res *RegressionResult) error {
	names := make([]string, 0, len(tests))
	for _, t := range tests {
		names = append(names, t.name)
	}
	out, err := r.Run(ctx, Command{Dir: tree, Name: "go", Args: []string{
		"test", "-json", "-count=1", "-run", "^(" + strings.Join(names, "|") + ")$", "./" + dir,
	}})
	if err != nil {
		return err
	}
	events, err := parseEvents(out.Stdout)
	if err != nil {
		return err
	}
	pkg := packageOf(events)
	for _, t := range tests {
		problem := regressionProblem(events, pkg, t.name)
		if problem == "" {
			res.Proven++
			continue
		}
		res.Findings = append(res.Findings, report.Finding{
			Location: t.file + ":" + strconv.Itoa(t.line),
			Rule:     RuleRegression,
			Message:  fmt.Sprintf("regression test %s %s on the merge base %.12s", t.name, problem, mergeBase),
			Fix:      "Make the test fail without the fix. Write it against the API of the merge base, and do not skip it.",
		})
	}
	return nil
}

// regressionProblem returns why a regression test does not prove the defect,
// or the empty string when it fails.
func regressionProblem(events []event, pkg, test string) string {
	if buildFailed(events) {
		return "does not compile"
	}
	switch outcome(events, pkg, test) {
	case "fail":
		return ""
	case "pass":
		return "passes"
	case "skip":
		return "skips"
	}
	return "does not run"
}
