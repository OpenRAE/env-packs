package report

import (
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"

	"github.com/OpenRAE/env-packs/internal/outcome"
)

func TestSort(t *testing.T) {
	a := Finding{Location: "a.go:1", Rule: "r", Message: "m", Fix: "f"}
	b := Finding{Location: "a.go:1", Rule: "s", Message: "m", Fix: "f"}
	c := Finding{Location: "a.go:1", Rule: "s", Message: "n", Fix: "f"}
	d := Finding{Location: "a.go:1", Rule: "s", Message: "n", Fix: "g"}
	e := Finding{Location: "b.go:1", Rule: "r", Message: "m", Fix: "f"}
	got := Sort([]Finding{e, d, c, b, a, e, a})
	if diff := cmp.Diff([]Finding{a, b, c, d, e}, got); diff != "" {
		t.Errorf("Sort() mismatch (-want +got):\n%s", diff)
	}
}

func TestFindingString(t *testing.T) {
	f := Finding{Location: "a.go:3", Rule: "mutant", Message: "no test kills it", Fix: "Add a test."}
	want := "a.go:3: mutant: no test kills it\n\tfix: Add a test."
	if got := f.String(); got != want {
		t.Errorf("Finding.String() = %q, want %q", got, want)
	}
}

func TestWrite(t *testing.T) {
	a := Finding{Location: "a.go:1", Rule: "r", Message: "m", Fix: "f"}
	b := Finding{Location: "b.go:2", Rule: "r", Message: "m", Fix: "f"}
	tests := []struct {
		name       string
		findings   []Finding
		wantStatus int
		wantStdout string
		wantStderr string
	}{
		{name: "none", wantStatus: outcome.OK, wantStderr: "tool: 0 findings\n"},
		{
			name:       "one",
			findings:   []Finding{a},
			wantStatus: outcome.Blocking,
			wantStdout: a.String() + "\n",
			wantStderr: "tool: 1 findings\n",
		},
		{
			name:       "sorted and unique",
			findings:   []Finding{b, a, b},
			wantStatus: outcome.Blocking,
			wantStdout: a.String() + "\n" + b.String() + "\n",
			wantStderr: "tool: 2 findings\n",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr strings.Builder
			s := outcome.NewStreams(&stdout, &stderr)
			status := s.Flush(Write(s, "tool", tt.findings))
			if status != tt.wantStatus || stdout.String() != tt.wantStdout || stderr.String() != tt.wantStderr {
				t.Errorf("Write() = %d, stdout %q, stderr %q; want %d, %q, %q",
					status, stdout.String(), stderr.String(), tt.wantStatus, tt.wantStdout, tt.wantStderr)
			}
		})
	}
}
