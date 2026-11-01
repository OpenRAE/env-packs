package report

import (
	"errors"
	"io"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

// TestStatuses pins the exit statuses, which are a contract of the tools.
func TestStatuses(t *testing.T) {
	got := []int{StatusOK, StatusFindings, StatusUsage, StatusFailure}
	if diff := cmp.Diff([]int{0, 1, 2, 3}, got); diff != "" {
		t.Errorf("statuses mismatch (-want +got):\n%s", diff)
	}
}

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

func TestStreamsFindings(t *testing.T) {
	a := Finding{Location: "a.go:1", Rule: "r", Message: "m", Fix: "f"}
	b := Finding{Location: "b.go:2", Rule: "r", Message: "m", Fix: "f"}
	tests := []struct {
		name       string
		findings   []Finding
		wantStatus int
		wantStdout string
		wantStderr string
	}{
		{name: "none", wantStatus: StatusOK, wantStderr: "tool: 0 findings\n"},
		{
			name:       "one",
			findings:   []Finding{a},
			wantStatus: StatusFindings,
			wantStdout: a.String() + "\n",
			wantStderr: "tool: 1 findings\n",
		},
		{
			name:       "sorted and unique",
			findings:   []Finding{b, a, b},
			wantStatus: StatusFindings,
			wantStdout: a.String() + "\n" + b.String() + "\n",
			wantStderr: "tool: 2 findings\n",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var stdout, stderr strings.Builder
			s := NewStreams(&stdout, &stderr)
			status := s.Flush(s.Findings("tool", tt.findings))
			if status != tt.wantStatus || stdout.String() != tt.wantStdout || stderr.String() != tt.wantStderr {
				t.Errorf("Findings() = %d, stdout %q, stderr %q; want %d, %q, %q",
					status, stdout.String(), stderr.String(), tt.wantStatus, tt.wantStdout, tt.wantStderr)
			}
		})
	}
}

// failingWriter fails each write.
type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) {
	return 0, errors.New("write failed")
}

func TestStreamsFlushFailure(t *testing.T) {
	var ok strings.Builder
	tests := []struct {
		name           string
		stdout, stderr io.Writer
	}{
		{name: "stdout", stdout: failingWriter{}, stderr: &ok},
		{name: "stderr", stdout: &ok, stderr: failingWriter{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			s := NewStreams(tt.stdout, tt.stderr)
			s.Findings("tool", []Finding{{Location: "a.go:1"}})
			if got := s.Flush(StatusFindings); got != StatusFailure {
				t.Errorf("Flush() after a failed write = %d, want %d", got, StatusFailure)
			}
		})
	}
}
