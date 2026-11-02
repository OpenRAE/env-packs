package testgate

import (
	"context"
	"fmt"
	"slices"
	"strings"

	"github.com/bluekeyes/go-gitdiff/gitdiff"
)

// Lines is a set of line numbers in one file.
type Lines map[int]bool

// Intersects reports whether the set holds a line from start to end.
func (l Lines) Intersects(start, end int) bool {
	for n := start; n <= end; n++ {
		if l[n] {
			return true
		}
	}
	return false
}

// Changes maps the path of each changed file, relative to the repository
// root, to its added and changed lines.
type Changes map[string]Lines

// A Diff holds the changes of the output of git diff -U0 to each file.
type Diff struct {
	// Added maps each file to the lines that the diff adds or changes. A file
	// without added lines, such as a deleted file, has no entry.
	Added Changes
	// Removed maps each file to the places of the hunks that only remove
	// lines. A place is the line of the new file before the removed lines, as
	// in the hunk header. A deleted file has no entry.
	Removed map[string][]int
}

// ParseDiff reads the output of git diff -U0.
func ParseDiff(diff string) (Diff, error) {
	files, _, err := gitdiff.Parse(strings.NewReader(diff))
	if err != nil {
		return Diff{}, fmt.Errorf("parse the diff: %w", err)
	}
	d := Diff{Added: make(Changes), Removed: make(map[string][]int)}
	for _, f := range files {
		for _, frag := range f.TextFragments {
			d.addFragment(f, frag)
		}
	}
	return d, nil
}

// addFragment adds the added lines of a fragment of the file f, or the place
// of the fragment when it only removes lines.
func (d Diff) addFragment(f *gitdiff.File, frag *gitdiff.TextFragment) {
	if frag.LinesAdded == 0 {
		if !f.IsDelete {
			d.Removed[f.NewName] = append(d.Removed[f.NewName], int(frag.NewPosition))
		}
		return
	}
	line := int(frag.NewPosition)
	for _, l := range frag.Lines {
		switch l.Op {
		case gitdiff.OpAdd:
			d.Added.add(f.NewName, line)
			line++
		case gitdiff.OpContext:
			line++
		case gitdiff.OpDelete:
		}
	}
}

// add adds line to the lines of file.
func (c Changes) add(file string, line int) {
	if c[file] == nil {
		c[file] = make(Lines)
	}
	c[file][line] = true
}

// revParse resolves rev to a commit ID. The commit ID is safe to use as an
// argument of other git commands.
func revParse(ctx context.Context, r Runner, repo, rev string) (string, error) {
	out, err := runOK(ctx, r, Command{Dir: repo, Name: "git", Args: []string{
		"rev-parse", "--verify", "--end-of-options", rev + "^{commit}",
	}})
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(out)), nil
}

// changedLines returns the changes of HEAD since the merge base of commit base
// and HEAD, in the files that the pathspecs match. The options make the output
// the same for each git configuration.
func changedLines(ctx context.Context, r Runner, repo, base string, pathspecs ...string) (Diff, error) {
	args := append([]string{
		"diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--find-renames",
		"--diff-algorithm=myers", "--src-prefix=a/", "--dst-prefix=b/",
		"--merge-base", base, "HEAD", "--",
	}, pathspecs...)
	out, err := runOK(ctx, r, Command{Dir: repo, Name: "git", Args: args})
	if err != nil {
		return Diff{}, err
	}
	return ParseDiff(string(out))
}

// mutable reports whether the mutation gate mutates the file: a Go file that
// is not a test file and that is not in a testdata directory.
func mutable(name string) bool {
	return strings.HasSuffix(name, ".go") && !strings.HasSuffix(name, "_test.go") &&
		!slices.Contains(strings.Split(name, "/"), "testdata")
}
