package testgate

import (
	"context"
	"errors"
	"fmt"
	"slices"
	"strconv"
	"strings"
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

// ParseDiff reads the output of git diff -U0 with the prefixes a/ and b/. It
// returns the lines that the diff adds or changes in each file. A file without
// added lines, such as a deleted file, has no entry.
func ParseDiff(diff string) (Changes, error) {
	changes := make(Changes)
	file, header := "", false
	for line := range strings.SplitSeq(diff, "\n") {
		switch {
		case strings.HasPrefix(line, "diff --git "):
			file, header = "", true
		case header && strings.HasPrefix(line, "+++ "):
			file = newPath(strings.TrimPrefix(line, "+++ "))
		case strings.HasPrefix(line, "@@ "):
			header = false
			if err := changes.addHunk(file, line); err != nil {
				return nil, err
			}
		}
	}
	return changes, nil
}

// newPath returns the path of a "+++" header without the prefix b/. Git
// quotes a path with special characters, and it ends a path that has a space
// with a tab. A deleted file has the path /dev/null and no added lines.
func newPath(s string) string {
	s = strings.TrimSuffix(s, "\t")
	if unquoted, err := strconv.Unquote(s); err == nil {
		s = unquoted
	}
	return strings.TrimPrefix(s, "b/")
}

// addHunk adds the new lines of a hunk header, "@@ -a,b +c,d @@", to file.
func (c Changes) addHunk(file, header string) error {
	fields := strings.Fields(header)
	if len(fields) < 4 || fields[3] != "@@" {
		return fmt.Errorf("invalid hunk header %q", header)
	}
	start, count, err := hunkRange(fields[2])
	if err != nil {
		return fmt.Errorf("invalid hunk header %q: %w", header, err)
	}
	for n := start; n < start+count; n++ {
		if c[file] == nil {
			c[file] = make(Lines)
		}
		c[file][n] = true
	}
	return nil
}

// hunkRange parses "+c,d" or "+c" into the first line and the number of
// lines.
func hunkRange(s string) (start, count int, err error) {
	s, ok := strings.CutPrefix(s, "+")
	if !ok {
		return 0, 0, errors.New("no range of new lines")
	}
	first, n, hasCount := strings.Cut(s, ",")
	if start, err = strconv.Atoi(first); err != nil {
		return 0, 0, err
	}
	count = 1
	if hasCount {
		if count, err = strconv.Atoi(n); err != nil {
			return 0, 0, err
		}
	}
	return start, count, nil
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

// changedLines returns the lines that HEAD adds or changes since the merge
// base of commit base and HEAD, in the files that the pathspecs match. The
// options make the output the same for each git configuration.
func changedLines(ctx context.Context, r Runner, repo, base string, pathspecs ...string) (Changes, error) {
	args := append([]string{
		"diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--find-renames",
		"--diff-algorithm=myers", "--src-prefix=a/", "--dst-prefix=b/",
		"--merge-base", base, "HEAD", "--",
	}, pathspecs...)
	out, err := runOK(ctx, r, Command{Dir: repo, Name: "git", Args: args})
	if err != nil {
		return nil, err
	}
	return ParseDiff(string(out))
}

// mutable reports whether the mutation gate mutates the file: a Go file that
// is not a test file and that is not in a testdata directory.
func mutable(name string) bool {
	return strings.HasSuffix(name, ".go") && !strings.HasSuffix(name, "_test.go") &&
		!slices.Contains(strings.Split(name, "/"), "testdata")
}
