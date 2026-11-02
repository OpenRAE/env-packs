package main

import (
	"bytes"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// mainEnv is the environment variable that makes the test binary run the
// command instead of the tests.
const mainEnv = "ARCHCHECK_TEST_MAIN"

// TestMain runs the command, not the tests, when TestMainProcess starts the
// test binary as a child process.
func TestMain(m *testing.M) {
	if os.Getenv(mainEnv) == "1" {
		main()
		return
	}
	m.Run()
}

// TestMainProcess runs the main function in a child process, to check that
// it passes the command line, the streams, and the exit status.
func TestMainProcess(t *testing.T) {
	dir := fixtureRepo(t)
	binary, err := os.Executable()
	if err != nil {
		t.Fatalf("locate the test binary: %v", err)
	}
	tests := []struct {
		args       []string
		wantStatus int
		wantStderr string
	}{
		{args: []string{"-root", dir, "design"}, wantStatus: 0, wantStderr: "archcheck: 0 findings\n"},
		{args: []string{"lint"}, wantStatus: 2, wantStderr: "archcheck: unknown mode \"lint\"; give design, check, dsl, or platforms\n"},
	}
	for _, tt := range tests {
		//nolint:gosec // G204 false positive: the command is this test binary, and the test sets each argument.
		cmd := exec.CommandContext(t.Context(), binary, tt.args...)
		cmd.Env = append(os.Environ(), mainEnv+"=1")
		var stdout, stderr bytes.Buffer
		cmd.Stdout, cmd.Stderr = &stdout, &stderr
		err := cmd.Run()
		status := 0
		if exitErr := (*exec.ExitError)(nil); errors.As(err, &exitErr) {
			status = exitErr.ExitCode()
		} else if err != nil {
			t.Fatalf("run the child process: %v", err)
		}
		if status != tt.wantStatus || stdout.String() != "" || stderr.String() != tt.wantStderr {
			t.Errorf("main(%q) = %d, stdout %q, stderr %q; want %d, no stdout, and stderr %q",
				tt.args, status, stdout.String(), stderr.String(), tt.wantStatus, tt.wantStderr)
		}
	}
}

// fixtureRepo copies the fixture repository to a new temporary directory and
// returns that directory.
func fixtureRepo(t *testing.T) string {
	t.Helper()
	dir := filepath.Join(t.TempDir(), "repo")
	if err := os.CopyFS(dir, os.DirFS("testdata/repo")); err != nil {
		t.Fatalf("copy the fixture repository: %v", err)
	}
	return dir
}

// runCommand runs the command with args after the program name, and returns
// the exit status and the output streams.
func runCommand(args ...string) (status int, stdout, stderr string) {
	var out, errOut bytes.Buffer
	status = run(append([]string{"archcheck"}, args...), os.Environ(), &out, &errOut)
	return status, out.String(), errOut.String()
}

func TestRunUsage(t *testing.T) {
	tests := []struct {
		name       string
		args       []string
		wantStderr string
	}{
		{name: "no mode", args: nil, wantStderr: "archcheck: give a mode: design, check, dsl, or platforms\n"},
		{name: "unknown mode", args: []string{"lint"}, wantStderr: "archcheck: unknown mode \"lint\"; give design, check, dsl, or platforms\n"},
		{name: "platforms with an argument", args: []string{"-root", "testdata/repo", "platforms", "x"}, wantStderr: "archcheck: platforms takes no arguments\n"},
		{name: "unknown flag", args: []string{"-color", "check"}, wantStderr: "flag provided but not defined: -color"},
		{name: "unknown dsl flag", args: []string{"-root", "testdata/repo", "dsl", "-force"}, wantStderr: "flag provided but not defined: -force"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, stdout, stderr := runCommand(tt.args...)
			if status != 2 {
				t.Errorf("run(%q) status = %d, want 2", tt.args, status)
			}
			if stdout != "" || !strings.Contains(stderr, tt.wantStderr) {
				t.Errorf("run(%q) stdout = %q, stderr = %q, want no stdout and stderr with %q", tt.args, stdout, stderr, tt.wantStderr)
			}
		})
	}
}

func TestRunCleanRepository(t *testing.T) {
	dir := fixtureRepo(t)
	for _, mode := range []string{"design", "check"} {
		status, stdout, stderr := runCommand("-root", dir, mode)
		if status != 0 || stdout != "" || stderr != "archcheck: 0 findings\n" {
			t.Errorf("run(%s) = %d, stdout %q, stderr %q; want 0, no stdout, and a zero count", mode, status, stdout, stderr)
		}
	}
}

func TestRunFindings(t *testing.T) {
	tests := []struct {
		name       string
		mode       string
		change     func(t *testing.T, dir string)
		wantStdout string
	}{
		{
			name:       "model that does not decode",
			mode:       "design",
			change:     writeFile("architecture/model.yaml", "version: 1\nmodul: x\n"),
			wantStdout: "architecture/model.yaml: model: decode model: yaml: unmarshal errors:\n  line 2: field modul not found in type architecture.Model\n\tfix: Correct the YAML of the model.",
		},
		{
			name:       "model that does not decode, in the check mode",
			mode:       "check",
			change:     writeFile("architecture/model.yaml", "version: 1\nmodul: x\n"),
			wantStdout: "architecture/model.yaml: model: decode model: yaml: unmarshal errors:\n  line 2: field modul not found in type architecture.Model\n\tfix: Correct the YAML of the model.",
		},
		{
			name:       "model that does not decode, in the dsl mode",
			mode:       "dsl",
			change:     writeFile("architecture/model.yaml", "version: 1\nmodul: x\n"),
			wantStdout: "architecture/model.yaml: model: decode model: yaml: unmarshal errors:\n  line 2: field modul not found in type architecture.Model\n\tfix: Correct the YAML of the model.",
		},
		{
			name:       "invalid model",
			mode:       "design",
			change:     replaceInModel("version: 1", "version: 2"),
			wantStdout: "architecture/model.yaml: model: version is 2; the only supported version is 1\n",
		},
		{
			name:       "model change without a design record",
			mode:       "design",
			change:     replaceInModel("components:", "test_modules: [example.com/mock]\ncomponents:"),
			wantStdout: "architecture/model.yaml: design: the model has test module \"example.com/mock\", but no design record adds it\n",
		},
		{
			name:       "design record that does not parse",
			mode:       "design",
			change:     writeFile("docs/development/designs/0002-bad.md", "no front matter\n"),
			wantStdout: "docs/development/designs/0002-bad.md: design: the design record has no YAML front matter at the first line\n",
		},
		{
			name:       "stale C4 view",
			mode:       "check",
			change:     writeFile("architecture/workspace.dsl", "workspace {}\n"),
			wantStdout: "architecture/workspace.dsl: c4-view: the C4 view differs from the rendered architecture model\n",
		},
		{
			name:       "missing C4 view",
			mode:       "check",
			change:     removeFile("architecture/workspace.dsl"),
			wantStdout: "architecture/workspace.dsl: c4-view: the C4 view differs from the rendered architecture model\n",
		},
		{
			name:       "package without an owner",
			mode:       "check",
			change:     writeFile("extra/extra.go", "// Package extra has no owner.\npackage extra\n"),
			wantStdout: "extra: package-owner: package \"example.com/repo/extra\" has no component\n",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := fixtureRepo(t)
			tt.change(t, dir)
			status, stdout, stderr := runCommand("-root", dir, tt.mode)
			if status != 1 {
				t.Errorf("run(%s) status = %d, want 1; stdout %q, stderr %q", tt.mode, status, stdout, stderr)
			}
			if !strings.Contains(stdout, tt.wantStdout) {
				t.Errorf("run(%s) stdout = %q, want it to contain %q", tt.mode, stdout, tt.wantStdout)
			}
		})
	}
}

// TestRunPlatforms checks that the code check reads the code of each platform
// of the model.
func TestRunPlatforms(t *testing.T) {
	dir := fixtureRepo(t)
	writeFile("doc_linux.go", "//go:build linux\n\npackage repo\n")(t, dir)
	writeFile("doc_darwin.go", "//go:build darwin\n\npackage repo\n")(t, dir)
	if status, stdout, stderr := runCommand("-root", dir, "check"); status != 0 || stdout != "" {
		t.Errorf("run(check) = %d, stdout %q, stderr %q; want 0 and no finding", status, stdout, stderr)
	}
	replaceInModel("platforms: [linux/amd64, darwin/arm64]", "platforms: [linux/amd64]")(t, dir)
	status, stdout, _ := runCommand("-root", dir, "check")
	want := "doc_darwin.go: unread-path: the check cannot read this path, so the rules of the model do not apply to it\n"
	if status != 1 || !strings.Contains(stdout, want) {
		t.Errorf("run(check) for linux only = %d, stdout %q; want 1 and %q", status, stdout, want)
	}
}

func TestRunPlatformsMode(t *testing.T) {
	dir := fixtureRepo(t)
	status, stdout, stderr := runCommand("-root", dir, "platforms")
	if status != 0 || stdout != "linux/amd64\ndarwin/arm64\n" || stderr != "" {
		t.Errorf("run(platforms) = %d, stdout %q, stderr %q; want 0 and the two platforms", status, stdout, stderr)
	}
	replaceInModel("version: 1", "version: 3")(t, dir)
	status, stdout, _ = runCommand("-root", dir, "platforms")
	if status != 1 || !strings.Contains(stdout, "version is 3") {
		t.Errorf("run(platforms) with an invalid model = %d, stdout %q; want 1 and the version finding", status, stdout)
	}
}

func TestRunFailures(t *testing.T) {
	tests := []struct {
		name       string
		args       func(dir string) []string
		change     func(t *testing.T, dir string)
		wantStderr string
	}{
		{
			name:       "missing root",
			args:       func(dir string) []string { return []string{"-root", filepath.Join(dir, "missing"), "design"} },
			wantStderr: "archcheck: read the model:",
		},
		{
			name:       "C4 view that cannot be read",
			args:       func(dir string) []string { return []string{"-root", dir, "check"} },
			change:     both(removeFile(dslFile), writeFile(dslFile+"/x", "x")),
			wantStderr: "archcheck: read the C4 view:",
		},
		{
			name:       "missing model",
			args:       func(dir string) []string { return []string{"-root", dir, "design"} },
			change:     removeFile("architecture/model.yaml"),
			wantStderr: "archcheck: read the model:",
		},
		{
			name:       "missing design directory",
			args:       func(dir string) []string { return []string{"-root", dir, "design"} },
			change:     removeFile("docs/development/designs"),
			wantStderr: "archcheck: read design records:",
		},
		{
			name:       "code that does not compile",
			args:       func(dir string) []string { return []string{"-root", dir, "check"} },
			change:     writeFile("doc.go", "package repo\n\nvar x int = \"text\"\n"),
			wantStderr: "archcheck: build linux/amd64: load the packages in ",
		},
		{
			name:       "missing model for dsl",
			args:       func(dir string) []string { return []string{"-root", dir, "dsl"} },
			change:     removeFile("architecture/model.yaml"),
			wantStderr: "archcheck: read the model:",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := fixtureRepo(t)
			if tt.change != nil {
				tt.change(t, dir)
			}
			status, _, stderr := runCommand(tt.args(dir)...)
			if status != 3 || !strings.Contains(stderr, tt.wantStderr) {
				t.Errorf("run() = %d, stderr %q; want 3 and stderr with %q", status, stderr, tt.wantStderr)
			}
		})
	}
}

func TestRunDSL(t *testing.T) {
	dir := fixtureRepo(t)
	root := openRoot(t, dir)
	want, err := root.ReadFile(dslFile)
	if err != nil {
		t.Fatalf("read the fixture view: %v", err)
	}
	status, stdout, _ := runCommand("-root", dir, "dsl")
	if status != 0 || stdout != string(want) {
		t.Errorf("run(dsl) = %d, stdout %q; want 0 and the committed view", status, stdout)
	}
	removeFile(dslFile)(t, dir)
	if status, _, stderr := runCommand("-root", dir, "dsl", "-write"); status != 0 {
		t.Fatalf("run(dsl -write) = %d, stderr %q; want 0", status, stderr)
	}
	got, err := root.ReadFile(dslFile)
	if err != nil || !bytes.Equal(got, want) {
		t.Errorf("run(dsl -write) wrote %q, %v; want the committed view", got, err)
	}
}

func TestRunDSLInvalidModel(t *testing.T) {
	dir := fixtureRepo(t)
	replaceInModel("version: 1", "version: 3")(t, dir)
	status, stdout, _ := runCommand("-root", dir, "dsl")
	if status != 1 || !strings.Contains(stdout, "version is 3") {
		t.Errorf("run(dsl) = %d, stdout %q; want 1 and the version finding", status, stdout)
	}
}

func TestRunDSLWriteFailure(t *testing.T) {
	dir := fixtureRepo(t)
	removeFile(dslFile)(t, dir)
	root := openRoot(t, dir)
	if err := root.Chmod("architecture", 0o500); err != nil {
		t.Fatalf("make the directory read-only: %v", err)
	}
	t.Cleanup(func() {
		if err := root.Chmod("architecture", 0o700); err != nil {
			t.Errorf("restore the directory mode: %v", err)
		}
	})
	status, _, stderr := runCommand("-root", dir, "dsl", "-write")
	if status != 3 || !strings.Contains(stderr, "archcheck: write the C4 view:") {
		t.Errorf("run(dsl -write) = %d, stderr %q; want 3 and a write error", status, stderr)
	}
}

// failingWriter fails every write.
type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) {
	return 0, errors.New("write failed")
}

func TestRunOutputFailure(t *testing.T) {
	dir := fixtureRepo(t)
	tests := []struct {
		name string
		args []string
	}{
		{name: "report", args: []string{"archcheck", "-root", dir, "design"}},
		{name: "dsl", args: []string{"archcheck", "-root", dir, "dsl"}},
		{name: "usage", args: []string{"archcheck"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if status := run(tt.args, os.Environ(), failingWriter{}, failingWriter{}); status != 3 {
				t.Errorf("run(%q) with failing output = %d, want 3", tt.args, status)
			}
		})
	}
}

// openRoot opens dir as an os.Root that the test closes at its end.
func openRoot(t *testing.T, dir string) *os.Root {
	t.Helper()
	root, err := os.OpenRoot(dir)
	if err != nil {
		t.Fatalf("open %s: %v", dir, err)
	}
	t.Cleanup(func() {
		if err := root.Close(); err != nil {
			t.Errorf("close %s: %v", dir, err)
		}
	})
	return root
}

// both applies two changes to the repository in dir, in order.
func both(first, second func(t *testing.T, dir string)) func(t *testing.T, dir string) {
	return func(t *testing.T, dir string) {
		t.Helper()
		first(t, dir)
		second(t, dir)
	}
}

func writeFile(name, content string) func(t *testing.T, dir string) {
	return func(t *testing.T, dir string) {
		t.Helper()
		root := openRoot(t, dir)
		if err := root.MkdirAll(filepath.Dir(name), 0o700); err != nil {
			t.Fatalf("create the directory of %s: %v", name, err)
		}
		if err := root.WriteFile(name, []byte(content), 0o600); err != nil {
			t.Fatalf("write %s: %v", name, err)
		}
	}
}

// replaceInModel replaces the first occurrence of old in the model of the
// repository.
func replaceInModel(old, replacement string) func(t *testing.T, dir string) {
	const name = modelFile
	return func(t *testing.T, dir string) {
		t.Helper()
		root := openRoot(t, dir)
		data, err := root.ReadFile(name)
		if err != nil {
			t.Fatalf("read %s: %v", name, err)
		}
		if !bytes.Contains(data, []byte(old)) {
			t.Fatalf("%s does not contain %q", name, old)
		}
		if err := root.WriteFile(name, bytes.Replace(data, []byte(old), []byte(replacement), 1), 0o600); err != nil {
			t.Fatalf("write %s: %v", name, err)
		}
	}
}

func removeFile(name string) func(t *testing.T, dir string) {
	return func(t *testing.T, dir string) {
		t.Helper()
		if err := openRoot(t, dir).RemoveAll(name); err != nil {
			t.Fatalf("remove %s: %v", name, err)
		}
	}
}
