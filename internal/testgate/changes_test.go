package testgate

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

// sampleDiff has a changed file, a new file, a deleted file, quoted and
// tab-ended paths, an added line that looks like a file header, and a hunk
// with context lines.
const sampleDiff = `diff --git a/x.go b/x.go
index 1111111..2222222 100644
--- a/x.go
+++ b/x.go
@@ -3 +3,2 @@ func a() {
-	return 1
+	return 2
+++ b/evil.go
@@ -10,0 +12,2 @@ func b() {
+	one()
+	two()
@@ -20,2 +23,0 @@ func c() {
-	gone()
-	gone()
diff --git a/new.go b/new.go
new file mode 100644
--- /dev/null
+++ b/new.go
@@ -0,0 +1,3 @@
+package x
+
+// x
diff --git a/old.go b/old.go
deleted file mode 100644
--- a/old.go
+++ /dev/null
@@ -1,2 +0,0 @@
-package x
-
diff --git "a/q\"uote.go" "b/q\"uote.go"
--- "a/q\"uote.go"
+++ "b/q\"uote.go"
@@ -5 +5 @@
-a
+b
\ No newline at end of file
diff --git a/sp ace.go b/sp ace.go
--- a/sp ace.go	
+++ b/sp ace.go	
@@ -7,0 +8 @@
+c
diff --git a/context.go b/context.go
--- a/context.go
+++ b/context.go
@@ -1,2 +1,4 @@
 a
+b
 c
+d
`

// hunk returns a zero-context hunk that replaces oldCount lines at oldStart
// with newCount lines at newStart.
func hunk(oldStart, oldCount, newStart, newCount int) string {
	return fmt.Sprintf("@@ -%d,%d +%d,%d @@\n", oldStart, oldCount, newStart, newCount) +
		strings.Repeat("-old\n", oldCount) + strings.Repeat("+new\n", newCount)
}

// fileDiff returns the diff of file with the hunks.
func fileDiff(file string, hunks ...string) string {
	return "diff --git a/" + file + " b/" + file + "\n--- a/" + file + "\n+++ b/" + file + "\n" + strings.Join(hunks, "")
}

func TestParseDiff(t *testing.T) {
	got, err := ParseDiff(sampleDiff)
	if err != nil {
		t.Fatalf("ParseDiff() error = %v", err)
	}
	want := Diff{
		Added: Changes{
			"x.go":       {3: true, 4: true, 12: true, 13: true},
			"new.go":     {1: true, 2: true, 3: true},
			`q"uote.go`:  {5: true},
			"sp ace.go":  {8: true},
			"context.go": {2: true, 4: true},
		},
		Removed: map[string][]int{"x.go": {23}},
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("ParseDiff() mismatch (-want +got):\n%s", diff)
	}
}

func TestParseDiffErrors(t *testing.T) {
	for _, hunk := range []string{"@@ -1", "@@ -1 +1", "@@ -1 +1 @x", "@@ -1 1 @@", "@@ -1 +x @@", "@@ -1 +1,y @@", "@@ -1 +1,2 @@\n+a"} {
		diff := "diff --git a/x.go b/x.go\n--- a/x.go\n+++ b/x.go\n" + hunk + "\n"
		if _, err := ParseDiff(diff); err == nil || !strings.HasPrefix(err.Error(), "parse the diff: ") {
			t.Errorf("ParseDiff() with %q: error = %v, want a parse error", hunk, err)
		}
	}
	// A deleted file does not add lines, but its headers must still be valid.
	if _, err := ParseDiff("diff --git a/x.go b/x.go\n--- a/x.go\n+++ /dev/null\n@@ -1 +y @@\n"); err == nil {
		t.Error("ParseDiff() with an invalid header of a deleted file: error = nil, want an error")
	}
}

func TestLinesIntersects(t *testing.T) {
	lines := Lines{5: true, 9: true}
	tests := []struct {
		start, end int
		want       bool
	}{
		{start: 1, end: 4, want: false},
		{start: 1, end: 5, want: true},
		{start: 5, end: 5, want: true},
		{start: 6, end: 8, want: false},
		{start: 9, end: 12, want: true},
		{start: 10, end: 12, want: false},
	}
	for _, tt := range tests {
		if got := lines.Intersects(tt.start, tt.end); got != tt.want {
			t.Errorf("Lines.Intersects(%d, %d) = %v, want %v", tt.start, tt.end, got, tt.want)
		}
	}
}

func TestMutable(t *testing.T) {
	tests := map[string]bool{
		"x.go": true, "internal/a/a.go": true, "internal/a/a_test.go": false, "x.txt": false,
		"internal/a/testdata/f.go": false, "testdata/x.go": false, "internal/testdatas/x.go": true,
	}
	for name, want := range tests {
		if got := mutable(name); got != want {
			t.Errorf("mutable(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestRevParse(t *testing.T) {
	r := &fakeRunner{answer: func(Command) (Result, error) { return ok("0123abc\n") }}
	got, err := revParse(context.Background(), r, "repo", "origin/main")
	if err != nil || got != "0123abc" {
		t.Fatalf("revParse() = %q, %v, want %q, nil", got, err, "0123abc")
	}
	want := []Command{{Dir: "repo", Name: "git", Args: []string{"rev-parse", "--verify", "--end-of-options", "origin/main^{commit}"}}}
	if diff := cmp.Diff(want, r.commands); diff != "" {
		t.Errorf("revParse() commands mismatch (-want +got):\n%s", diff)
	}
	r.answer = func(Command) (Result, error) { return exit(128, "fatal: bad revision") }
	if _, err := revParse(context.Background(), r, "repo", "nope"); err == nil || !strings.Contains(err.Error(), "fatal: bad revision") {
		t.Errorf("revParse() of a bad revision: error = %v, want the git error", err)
	}
}

func TestChangedLines(t *testing.T) {
	r := &fakeRunner{answer: func(Command) (Result, error) { return ok(sampleDiff) }}
	got, err := changedLines(context.Background(), r, "repo", "0123abc", "*.go")
	if err != nil || len(got.Added["x.go"]) != 4 {
		t.Fatalf("changedLines() = %v, %v, want the lines of the sample diff", got, err)
	}
	want := []Command{{Dir: "repo", Name: "git", Args: []string{
		"diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "--find-renames",
		"--diff-algorithm=myers", "--src-prefix=a/", "--dst-prefix=b/",
		"--merge-base", "0123abc", "HEAD", "--", "*.go",
	}}}
	if diff := cmp.Diff(want, r.commands); diff != "" {
		t.Errorf("changedLines() commands mismatch (-want +got):\n%s", diff)
	}
	r.answer = func(Command) (Result, error) { return exit(129, "usage") }
	if _, err := changedLines(context.Background(), r, "repo", "0123abc"); err == nil {
		t.Error("changedLines() with a failing git: error = nil, want an error")
	}
	r.answer = func(Command) (Result, error) { return ok("diff --git a/x b/x\n+++ b/x\n@@ bad\n") }
	if _, err := changedLines(context.Background(), r, "repo", "0123abc"); err == nil {
		t.Error("changedLines() with an invalid diff: error = nil, want an error")
	}
}
