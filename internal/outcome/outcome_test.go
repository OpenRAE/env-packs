package outcome

import (
	"errors"
	"fmt"
	"io"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestStatuses(t *testing.T) {
	got := []int{OK, Blocking, Usage, ToolFailure}
	if diff := cmp.Diff([]int{0, 1, 2, 3}, got); diff != "" {
		t.Errorf("statuses mismatch (-want +got):\n%s", diff)
	}
}

// failingWriter fails each write.
type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) {
	return 0, errors.New("write failed")
}

func TestStreamsFlush(t *testing.T) {
	var ok strings.Builder
	tests := []struct {
		name           string
		stdout, stderr io.Writer
		want           int
	}{
		{name: "both", stdout: &ok, stderr: &ok, want: Blocking},
		{name: "stdout fails", stdout: failingWriter{}, stderr: &ok, want: ToolFailure},
		{name: "stderr fails", stdout: &ok, stderr: failingWriter{}, want: ToolFailure},
	}
	for _, tt := range tests {
		s := NewStreams(tt.stdout, tt.stderr)
		fmt.Fprintf(s.Stdout, "out")
		fmt.Fprintf(s.Stderr, "err")
		if got := s.Flush(Blocking); got != tt.want {
			t.Errorf("Flush() with %s = %d, want %d", tt.name, got, tt.want)
		}
	}
}

func TestRun(t *testing.T) {
	private := "/home/user/pack/private.yaml"
	tests := []struct {
		name       string
		body       func(Streams) (int, error)
		wantStatus int
		wantStdout string
		wantStderr string
	}{
		{
			name: "status",
			body: func(s Streams) (int, error) {
				fmt.Fprintf(s.Stdout, "report\n")
				return Blocking, nil
			},
			wantStatus: Blocking,
			wantStdout: "report\n",
		},
		{
			name: "error",
			body: func(s Streams) (int, error) {
				fmt.Fprintf(s.Stdout, "partial")
				return OK, errors.New(private)
			},
			wantStatus: ToolFailure,
			wantStderr: "cmd: internal error (*errors.errorString)\n",
		},
		{
			name: "panic",
			body: func(s Streams) (int, error) {
				fmt.Fprintf(s.Stdout, "partial")
				panic(private)
			},
			wantStatus: ToolFailure,
			wantStderr: "cmd: internal error (string)\n",
		},
	}
	for _, tt := range tests {
		var stdout, stderr strings.Builder
		status := Run("cmd", NewStreams(&stdout, &stderr), tt.body)
		if status != tt.wantStatus || stdout.String() != tt.wantStdout || stderr.String() != tt.wantStderr {
			t.Errorf("Run() with %s = %d, stdout %q, stderr %q; want %d, %q, %q",
				tt.name, status, stdout.String(), stderr.String(), tt.wantStatus, tt.wantStdout, tt.wantStderr)
		}
	}
}

func TestRunDefectWriteFails(t *testing.T) {
	var stdout strings.Builder
	status := Run("cmd", NewStreams(&stdout, failingWriter{}), func(Streams) (int, error) {
		return OK, errors.New("defect")
	})
	if status != ToolFailure {
		t.Errorf("Run() with a defect and a failed stderr = %d, want %d", status, ToolFailure)
	}
}
