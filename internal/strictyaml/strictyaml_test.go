package strictyaml

import (
	"errors"
	"io"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

type target struct {
	Name  string   `yaml:"name"`
	Items []string `yaml:"items"`
}

func TestDecode(t *testing.T) {
	var got target
	if err := Decode([]byte("name: a\nitems: [x, y]\n"), &got); err != nil {
		t.Fatalf("Decode() error = %v, want nil", err)
	}
	if diff := cmp.Diff(target{Name: "a", Items: []string{"x", "y"}}, got); diff != "" {
		t.Errorf("Decode() mismatch (-want +got):\n%s", diff)
	}
}

func TestDecodeErrors(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		wantErr error
		errText string
	}{
		{name: "unknown field", input: "name: a\ncolor: red\n", errText: "field color not found"},
		{name: "duplicate key", input: "name: a\nname: b\n", errText: `mapping key "name" already defined`},
		{name: "two documents", input: "name: a\n---\nname: b\n", wantErr: ErrMultipleDocuments},
		{name: "second document that does not parse", input: "name: a\n---\n[\n", wantErr: ErrMultipleDocuments},
		{name: "empty", input: "", wantErr: io.EOF},
		{name: "syntax error", input: "name: [a\n", errText: "did not find expected"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got target
			err := Decode([]byte(tt.input), &got)
			if err == nil || tt.wantErr != nil && !errors.Is(err, tt.wantErr) || !strings.Contains(err.Error(), tt.errText) {
				t.Errorf("Decode(%q) error = %v, want %v with %q", tt.input, err, tt.wantErr, tt.errText)
			}
		})
	}
}
