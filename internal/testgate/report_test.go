package testgate

import (
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestParseReport(t *testing.T) {
	data := `{"stats":{"totalMutantsCount":5,"killedCount":2,"escapedCount":1,"skippedCount":1,"errorCount":1},
		"escaped":[{"mutator":{"mutatorName":"branch/if","originalSourceCode":"a","mutatedSourceCode":"b","originalFilePath":"x.go","originalStartLine":0}}],
		"killed":[]}`
	got, err := parseReport([]byte(data))
	if err != nil {
		t.Fatalf("parseReport() error = %v", err)
	}
	if s := got.Stats; s.Total != 5 || s.Killed != 2 || s.Escaped != 1 || s.NotCompiled != 1 || s.Errored != 1 {
		t.Errorf("parseReport() stats = %+v, want 5, 2, 1, 1, 1", s)
	}
	m := got.Escaped[0].Mutator
	if len(got.Escaped) != 1 || m.Name != "branch/if" || m.Original != "a" || m.Mutated != "b" || m.File != "x.go" {
		t.Errorf("parseReport() escaped = %+v, want the one mutant", got.Escaped)
	}
	if _, err := parseReport([]byte("{")); err == nil {
		t.Error("parseReport() of invalid JSON: error = nil, want an error")
	}
}

func TestChangedRange(t *testing.T) {
	lines := func(s string) []string { return strings.Split(s, "") }
	tests := []struct {
		name              string
		original, mutated string
		start, end        int
		changed           bool
	}{
		{name: "same", original: "abc", mutated: "abc"},
		{name: "replacement", original: "abcde", mutated: "abXde", start: 3, end: 3, changed: true},
		{name: "replacement of two lines", original: "abcde", mutated: "aXYde", start: 2, end: 3, changed: true},
		{name: "insertion", original: "abcd", mutated: "abXcd", start: 3, end: 3, changed: true},
		{name: "removal", original: "abcd", mutated: "abd", start: 3, end: 3, changed: true},
		{name: "insertion at the end", original: "ab", mutated: "abX", start: 2, end: 2, changed: true},
		{name: "removal at the end", original: "abc", mutated: "ab", start: 3, end: 3, changed: true},
		{name: "removal at the end with a matching suffix", original: "abcb", mutated: "ab", start: 3, end: 4, changed: true},
		{name: "insertion at the start", original: "ab", mutated: "xab", start: 1, end: 1, changed: true},
		{name: "two separate changes", original: "abcd", mutated: "aXcY", start: 2, end: 4, changed: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			start, end, changed := changedRange(lines(tt.original), lines(tt.mutated))
			if start != tt.start || end != tt.end || changed != tt.changed {
				t.Errorf("changedRange(%q, %q) = %d, %d, %v, want %d, %d, %v",
					tt.original, tt.mutated, start, end, changed, tt.start, tt.end, tt.changed)
			}
		})
	}
}

const functionSource = `package x

const limit = 3

func plain() {
	_ = 1
}

func (r *ptr) method() {
	_ = 2
}

func (g gen[K, V]) generic() {
	_ = 3
}

func (p (val)) paren() {
	_ = 4
}
`

func TestFunctionAt(t *testing.T) {
	tests := map[int]string{
		3: "", 5: "plain", 6: "plain", 7: "plain", 8: "", 10: "ptr.method", 14: "gen.generic", 18: "val.paren",
	}
	for line, want := range tests {
		got, err := functionAt(functionSource, line)
		if err != nil || got != want {
			t.Errorf("functionAt(line %d) = %q, %v, want %q, nil", line, got, err, want)
		}
	}
	if _, err := functionAt("package", 1); err == nil {
		t.Error("functionAt() of invalid source: error = nil, want an error")
	}
}

func TestSurvivor(t *testing.T) {
	var m mutant
	m.Mutator.Name = "branch/if"
	m.Mutator.File = "x.go"
	m.Mutator.Original = functionSource
	m.Mutator.Mutated = strings.Replace(functionSource, "_ = 2", "_ = 20", 1)
	got, changed, err := survivor(m)
	if err != nil || !changed {
		t.Fatalf("survivor() = %+v, %v, %v, want a changed mutant", got, changed, err)
	}
	want := Survivor{File: "x.go", Function: "ptr.method", Mutator: "branch/if", Start: 10, End: 10, Line: "_ = 2", Mutated: "_ = 20"}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("survivor() mismatch (-want +got):\n%s", diff)
	}
	m.Mutator.Mutated = functionSource
	if _, changed, err := survivor(m); changed || err != nil {
		t.Errorf("survivor() of an unchanged mutant = %v, %v, want false, nil", changed, err)
	}
	m.Mutator.Original = "package\n"
	m.Mutator.Mutated = "package x\n"
	if _, _, err := survivor(m); err == nil || !strings.Contains(err.Error(), "parse x.go") {
		t.Errorf("survivor() of invalid source: error = %v, want a parse error", err)
	}
}

func TestLineAt(t *testing.T) {
	lines := []string{"  a  ", "b"}
	if got := lineAt(lines, 1); got != "a" {
		t.Errorf("lineAt(1) = %q, want %q", got, "a")
	}
	if got := lineAt(lines, 2); got != "b" {
		t.Errorf("lineAt(2) = %q, want %q", got, "b")
	}
	if got := lineAt(lines, 3); got != "" {
		t.Errorf("lineAt(3) = %q, want the empty string", got)
	}
}
