package testgate

import (
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestParseRecords(t *testing.T) {
	data := "version: 1\nequivalents:\n  - file: x.go\n    function: f\n    mutator: branch/if\n    line: if a {\n    mutated: if a {}\n    reason: R.\n"
	got, err := ParseRecords([]byte(data))
	if err != nil {
		t.Fatalf("ParseRecords() error = %v", err)
	}
	want := Records{Version: 1, Equivalents: []Equivalent{{File: "x.go", Function: "f", Mutator: "branch/if", Line: "if a {", Mutated: "if a {}", Reason: "R."}}}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("ParseRecords() mismatch (-want +got):\n%s", diff)
	}
	for _, bad := range []string{"version: 1\nequivalent: []\n", "version: 1\n---\nversion: 1\n"} {
		if _, err := ParseRecords([]byte(bad)); err == nil || !strings.Contains(err.Error(), "decode mutation.yaml") {
			t.Errorf("ParseRecords(%q) error = %v, want a decode error", bad, err)
		}
	}
}

func TestRecordsCheck(t *testing.T) {
	full := Equivalent{File: "x.go", Function: "f", Mutator: "branch/if", Line: "if a {", Mutated: "if a {}", Reason: "R."}
	without := func(change func(e *Equivalent)) Equivalent {
		e := full
		change(&e)
		return e
	}
	tests := []struct {
		name    string
		records Records
		want    []string
	}{
		{name: "valid", records: Records{Version: 1, Equivalents: []Equivalent{full}}},
		{name: "no function", records: Records{Version: 1, Equivalents: []Equivalent{without(func(e *Equivalent) { e.Function = "" })}}},
		{name: "version", records: Records{Version: 2}, want: []string{"version is 2; the only supported version is 1"}},
		{name: "no file", records: Records{Version: 1, Equivalents: []Equivalent{without(func(e *Equivalent) { e.File = "" })}},
			want: []string{"record 1 needs a file, a mutator, a line, the mutated line, and a reason"}},
		{name: "no mutator", records: Records{Version: 1, Equivalents: []Equivalent{without(func(e *Equivalent) { e.Mutator = "" })}},
			want: []string{"record 1 needs a file, a mutator, a line, the mutated line, and a reason"}},
		{name: "no line", records: Records{Version: 1, Equivalents: []Equivalent{without(func(e *Equivalent) { e.Line = "" })}},
			want: []string{"record 1 needs a file, a mutator, a line, the mutated line, and a reason"}},
		{name: "no mutated line", records: Records{Version: 1, Equivalents: []Equivalent{without(func(e *Equivalent) { e.Mutated = "" })}},
			want: []string{"record 1 needs a file, a mutator, a line, the mutated line, and a reason"}},
		{name: "no reason", records: Records{Version: 1, Equivalents: []Equivalent{without(func(e *Equivalent) { e.Reason = "" })}},
			want: []string{"record 1 needs a file, a mutator, a line, the mutated line, and a reason"}},
		{name: "two records for two identical mutants", records: Records{Version: 1, Equivalents: []Equivalent{full, full}}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got []string
			for _, f := range tt.records.Check() {
				if f.Location != RecordsFile || f.Rule != RuleRecord || f.Fix == "" {
					t.Errorf("finding %+v, want location %q, rule %q, and a fix", f, RecordsFile, RuleRecord)
				}
				got = append(got, f.Message)
			}
			if diff := cmp.Diff(tt.want, got); diff != "" {
				t.Errorf("Records.Check() mismatch (-want +got):\n%s", diff)
			}
		})
	}
}

func TestRecordsMatch(t *testing.T) {
	records := Records{Version: 1, Equivalents: []Equivalent{
		{File: "x.go", Function: "f", Mutator: "branch/if", Line: "if a {", Mutated: "if a {}", Reason: "R."},
		{File: "x.go", Function: "g", Mutator: "branch/if", Line: "if a {", Mutated: "if a {}", Reason: "R."},
	}}
	s := Survivor{File: "x.go", Function: "g", Mutator: "branch/if", Line: "if a {", Mutated: "if a {}"}
	used := make([]bool, len(records.Equivalents))
	if got := records.match(s, used); got != 1 {
		t.Errorf("match(%+v) = %d, want 1", s, got)
	}
	used[1] = true
	if got := records.match(s, used); got != -1 {
		t.Errorf("match(%+v) after the record was used = %d, want -1", s, got)
	}
	for _, other := range []Survivor{
		{File: "y.go", Function: "g", Mutator: "branch/if", Line: "if a {", Mutated: "if a {}"},
		{File: "x.go", Function: "h", Mutator: "branch/if", Line: "if a {", Mutated: "if a {}"},
		{File: "x.go", Function: "g", Mutator: "branch/else", Line: "if a {", Mutated: "if a {}"},
		{File: "x.go", Function: "g", Mutator: "branch/if", Line: "if b {", Mutated: "if a {}"},
		{File: "x.go", Function: "g", Mutator: "branch/if", Line: "if a {", Mutated: "if b {}"},
	} {
		if got := records.match(other, make([]bool, len(records.Equivalents))); got != -1 {
			t.Errorf("match(%+v) = %d, want -1", other, got)
		}
	}
}
