package testgate

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestExecStatus(t *testing.T) {
	tests := []struct {
		name   string
		output string
		want   int
	}{
		{name: "build failure", output: buildFailOutput, want: 2},
		{name: "test failure", output: testFailOutput, want: 0},
		{name: "pass", output: passOutput, want: 1},
		{name: "no test files", output: noTestsOutput, want: 1},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := execStatus(Result{Stdout: []byte(tt.output)}, "/tree/x")
			if err != nil || got != tt.want {
				t.Errorf("execStatus() = %d, %v, want %d, nil", got, err, tt.want)
			}
		})
	}
	_, err := execStatus(Result{Stdout: []byte(`{"Action":"start","Package":"p"}`), Stderr: []byte("setup failed\n"), ExitCode: 1}, "p")
	if err == nil || err.Error() != "go test reported no result for p: exit status 1: setup failed" {
		t.Errorf("execStatus() without a result: error = %v, want the status and the stderr", err)
	}
	if _, err := execStatus(Result{Stdout: []byte("not json")}, "p"); err == nil || !strings.Contains(err.Error(), "decode the output of go test -json") {
		t.Errorf("execStatus() of text that is not JSON: error = %v, want a decode error", err)
	}
}

// mutantFiles writes an original file and a mutated file in a new directory,
// and returns their paths.
func mutantFiles(t *testing.T) (original, mutated string) {
	t.Helper()
	dir := t.TempDir()
	original, mutated = filepath.Join(dir, "x.go"), filepath.Join(dir, "x.go.0")
	if err := os.WriteFile(original, []byte("original"), 0o600); err != nil {
		t.Fatalf("write the original file: %v", err)
	}
	if err := os.WriteFile(mutated, []byte("mutated"), 0o600); err != nil {
		t.Fatalf("write the mutated file: %v", err)
	}
	return original, mutated
}

func TestExecMutant(t *testing.T) {
	original, mutated := mutantFiles(t)
	var during []byte
	r := &fakeRunner{answer: func(Command) (Result, error) {
		data, err := readFile(original)
		if err != nil {
			t.Fatalf("read the original file during the test: %v", err)
		}
		during = data
		return ok(testFailOutput)
	}}
	m := Mutant{Original: original, Mutated: mutated, Package: "/tree/x", Timeout: 90 * time.Second}
	status, err := ExecMutant(context.Background(), r, "/tree", m)
	if err != nil || status != ExecKilled {
		t.Fatalf("ExecMutant() = %d, %v, want %d, nil", status, err, ExecKilled)
	}
	if string(during) != "mutated" {
		t.Errorf("ExecMutant() ran the tests with %q in place, want the mutant", during)
	}
	if data, err := readFile(original); err != nil || string(data) != "original" {
		t.Errorf("ExecMutant() left %q, %v in place, want the original file", data, err)
	}
	want := "go test -json -count=1 -timeout=1m30s /tree/x"
	if len(r.commands) != 1 || r.commands[0].String() != want || r.commands[0].Dir != "/tree" {
		t.Errorf("ExecMutant() commands = %+v, want %q in /tree", r.commands, want)
	}
}

func TestExecMutantErrors(t *testing.T) {
	original, mutated := mutantFiles(t)
	failure := errors.New("cannot start")
	failing := &fakeRunner{answer: func(Command) (Result, error) { return Result{}, failure }}
	tests := []struct {
		name    string
		mutant  Mutant
		wantErr string
	}{
		{name: "flag as package", mutant: Mutant{Original: original, Mutated: mutated, Package: "-x"}, wantErr: `package "-x" is not a package path`},
		{name: "missing original", mutant: Mutant{Original: original + ".none", Mutated: mutated, Package: "p"}, wantErr: "read the original file"},
		{name: "missing mutant", mutant: Mutant{Original: original, Mutated: mutated + ".none", Package: "p"}, wantErr: "read the mutant"},
		{name: "runner failure", mutant: Mutant{Original: original, Mutated: mutated, Package: "p"}, wantErr: "cannot start"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, err := ExecMutant(context.Background(), failing, ".", tt.mutant)
			if status != 3 || err == nil || !strings.Contains(err.Error(), tt.wantErr) {
				t.Errorf("ExecMutant() = %d, %v; want 3 and an error with %q", status, err, tt.wantErr)
			}
			if data, err := readFile(original); err != nil || string(data) != "original" {
				t.Errorf("ExecMutant() left %q, %v in place, want the original file", data, err)
			}
		})
	}
}

func TestExecMutantPlacementFailure(t *testing.T) {
	original, mutated := mutantFiles(t)
	if err := os.Chmod(original, 0o400); err != nil {
		t.Fatalf("make the original file read-only: %v", err)
	}
	_, err := ExecMutant(context.Background(), &fakeRunner{}, ".", Mutant{Original: original, Mutated: mutated, Package: "p"})
	if err == nil || !strings.Contains(err.Error(), "put the mutant in place") {
		t.Errorf("ExecMutant() with a read-only original: error = %v, want a placement error", err)
	}
}

func TestExecMutantRestoreFailure(t *testing.T) {
	for name, output := range map[string]string{"killed": testFailOutput, "escaped": passOutput} {
		original, mutated := mutantFiles(t)
		r := &fakeRunner{answer: func(Command) (Result, error) {
			if err := os.Chmod(original, 0o400); err != nil {
				t.Fatalf("make the original file read-only: %v", err)
			}
			return ok(output)
		}}
		status, err := ExecMutant(context.Background(), r, ".", Mutant{Original: original, Mutated: mutated, Package: "p"})
		if status != 3 || !errors.Is(err, os.ErrPermission) {
			t.Errorf("ExecMutant() of a %s mutant with a failed restore = %d, %v; want 3 and a permission error", name, status, err)
		}
	}
}

// TestExecMutantGoTest runs the exec step with the real go command.
func TestExecMutantGoTest(t *testing.T) {
	dir := t.TempDir()
	files := map[string]string{
		"go.mod":    "module example.com/m\n\ngo 1.26.0\n",
		"m.go":      "package m\n\n// Two returns 2.\nfunc Two() int { return 2 }\n",
		"m_test.go": "package m\n\nimport \"testing\"\n\nfunc TestTwo(t *testing.T) {\n\tif Two() != 2 {\n\t\tt.Fatal(\"not 2\")\n\t}\n}\n",
	}
	for name, content := range files {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o600); err != nil {
			t.Fatalf("write %s: %v", name, err)
		}
	}
	tests := []struct {
		name    string
		mutated string
		want    int
	}{
		{name: "killed", mutated: "package m\n\nfunc Two() int { return 3 }\n", want: 0},
		{name: "escaped", mutated: "package m\n\nfunc Two() int { return 1 + 1 }\n", want: 1},
		{name: "not compiled", mutated: "package m\n\nfunc Two() int { return \"2\" }\n", want: 2},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mutated := filepath.Join(t.TempDir(), "m.go.0")
			if err := os.WriteFile(mutated, []byte(tt.mutated), 0o600); err != nil {
				t.Fatalf("write the mutant: %v", err)
			}
			m := Mutant{Original: filepath.Join(dir, "m.go"), Mutated: mutated, Package: dir, Timeout: time.Minute}
			got, err := ExecMutant(context.Background(), ExecRunner{}, dir, m)
			if err != nil || got != tt.want {
				t.Errorf("ExecMutant() = %d, %v, want %d, nil", got, err, tt.want)
			}
		})
	}
}

func TestInScope(t *testing.T) {
	const original, mutated = "a\nb\nc\n", "a\nB\nc\n"
	tests := []struct {
		name    string
		lines   string
		file    string
		mutated string
		want    bool
		wantErr string
	}{
		{name: "no lines file", file: "x.go", mutated: mutated, want: true},
		{name: "unchanged source", file: "x.go", mutated: original},
		{name: "changed line", lines: `{"x.go":{"2":true}}`, file: "x.go", mutated: mutated, want: true},
		{name: "another file", lines: `{"x.go":{"2":true}}`, file: "y.go", mutated: mutated},
		{name: "outside the changed lines", lines: `{"x.go":{"3":true}}`, file: "x.go", mutated: mutated},
		{name: "invalid lines file", lines: "{", file: "x.go", mutated: mutated, wantErr: "decode the changed lines"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := t.TempDir()
			if tt.lines != "" {
				if err := os.WriteFile(filepath.Join(dir, linesFile), []byte(tt.lines), 0o600); err != nil {
					t.Fatalf("write the lines file: %v", err)
				}
			}
			got, err := inScope(dir, tt.file, original, tt.mutated)
			if got != tt.want || (err == nil) != (tt.wantErr == "") || err != nil && !strings.Contains(err.Error(), tt.wantErr) {
				t.Errorf("inScope() = %v, %v, want %v and an error with %q", got, err, tt.want, tt.wantErr)
			}
		})
	}
}

func TestInScopeUnreadableLines(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, linesFile), []byte("{}"), 0o200); err != nil {
		t.Fatalf("write the lines file: %v", err)
	}
	if _, err := inScope(dir, "x.go", "a\n", "b\n"); err == nil || !strings.Contains(err.Error(), "read the changed lines") {
		t.Errorf("inScope() with an unreadable lines file: error = %v, want a read error", err)
	}
}

func TestExecMutantOutOfScope(t *testing.T) {
	original, mutated := mutantFiles(t)
	dir := filepath.Dir(original)
	if err := os.WriteFile(filepath.Join(dir, linesFile), []byte(`{"other.go":{"1":true}}`), 0o600); err != nil {
		t.Fatalf("write the lines file: %v", err)
	}
	r := &fakeRunner{}
	status, err := ExecMutant(context.Background(), r, dir, Mutant{Original: original, Mutated: mutated, Package: "p"})
	if err != nil || status != ExecKilled || len(r.commands) != 0 {
		t.Errorf("ExecMutant() out of scope = %d, %v after %d commands; want %d, nil, and no command", status, err, len(r.commands), ExecKilled)
	}
}

func TestExecMutantInvalidLines(t *testing.T) {
	original, mutated := mutantFiles(t)
	dir := filepath.Dir(original)
	if err := os.WriteFile(filepath.Join(dir, linesFile), []byte("{"), 0o600); err != nil {
		t.Fatalf("write the lines file: %v", err)
	}
	_, err := ExecMutant(context.Background(), &fakeRunner{}, dir, Mutant{Original: original, Mutated: mutated, Package: "p"})
	if err == nil || !strings.Contains(err.Error(), "decode the changed lines") {
		t.Errorf("ExecMutant() with an invalid lines file: error = %v, want a decode error", err)
	}
}
