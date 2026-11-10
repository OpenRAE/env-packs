package main

import (
	"fmt"
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

// FuzzDecodeInput checks that decodeInput gives the same result for the same
// input, and that invalid input gives no document and one stable error.
func FuzzDecodeInput(f *testing.F) {
	for _, seed := range []struct{ name, data string }{
		{"x.yaml", "a: 1\n"}, {"x.yaml", "a: 1\na: 2\n"}, {"x.yaml", "- 1\n"}, {"x.yaml", "null\n"},
		{"x.yml", "jobs: {a: {steps: [{run: echo}]}}\n"}, {"x.json", `{"a": [1, 2]}`}, {"x.json", `{"a": }`},
		{"x.toml", "[tools]\nconftest = '0.71.1'\n"}, {"x.toml", "a = nan\n"}, {"x.toml", "["}, {"x", ""},
	} {
		f.Add(seed.name, []byte(seed.data))
	}
	f.Fuzz(func(t *testing.T, name string, data []byte) {
		got, err := decodeInput(name, data)
		again, againErr := decodeInput(name, data)
		if !cmp.Equal(got, again, cmpopts.EquateNaNs()) || (err == nil) != (againErr == nil) {
			t.Fatalf("decodeInput(%q, %q) = %v, %v, then %v, %v; want the same result", name, data, got, err, again, againErr)
		}
		if err != nil && (got != nil || err.Error() != fmt.Sprintf("invalid structured input %q", name)) {
			t.Fatalf("decodeInput(%q, %q) = %v, %v; want no document and the stable error", name, data, got, err)
		}
		if err == nil && got == nil {
			t.Fatalf("decodeInput(%q, %q) gave neither a document nor an error", name, data)
		}
	})
}

// FuzzShellCommands checks that shellCommands gives the same result for the
// same script, and at most one command for each byte of the script.
func FuzzShellCommands(f *testing.F) {
	for _, seed := range []string{
		"echo hi", "make prose BASE=\"$BASE\"", "a && b | c; d", "x=$(git diff -z) || exit 1",
		"if [ -z \"$x\" ]; then exit 0; fi", "for f in *; do echo \"$f\"; done", "echo 'unterminated",
		"cat <<EOF\nbody\nEOF\n", "",
	} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, script string) {
		got, err := shellCommands(script)
		again, againErr := shellCommands(script)
		if !cmp.Equal(got, again) || (err == nil) != (againErr == nil) {
			t.Fatalf("shellCommands(%q) = %q, %v, then %q, %v; want the same result", script, got, err, again, againErr)
		}
		if len(got) > len(script) {
			t.Fatalf("shellCommands(%q) gave %d commands; want at most one for each byte", script, len(got))
		}
	})
}
