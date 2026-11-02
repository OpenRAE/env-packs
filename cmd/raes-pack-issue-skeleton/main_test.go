package main

import (
	"bytes"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/OpenRAE/env-packs/internal/issueskeleton"
)

// mainEnv makes the test binary run the command instead of the tests.
const mainEnv = "ISSUE_SKELETON_TEST_MAIN"

// TestMain runs the command, not the tests, when TestMainProcess starts the
// test binary as a child process.
func TestMain(m *testing.M) {
	if os.Getenv(mainEnv) == "1" {
		main()
		return
	}
	m.Run()
}

// TestMainProcess runs main in a child process, to check that it passes the
// command line, the streams, and the exit status, and that nothing else
// writes to the streams.
func TestMainProcess(t *testing.T) {
	binary, err := os.Executable()
	if err != nil {
		t.Fatalf("locate the test binary: %v", err)
	}
	tests := []struct {
		args       []string
		wantStatus int
		wantStdout string
		wantStderr string
	}{
		{args: []string{"--bogus", "x"}, wantStatus: 2, wantStderr: usageLine + "\n" + name + ": error: flag provided but not defined: -bogus\n"},
		{args: []string{"-h"}, wantStdout: usageLine + "\n\nCreate standard skeleton GitHub issues for an environment pack.\n"},
		{wantStatus: 1, wantStderr: "--repo OWNER/REPOSITORY is required: name the catalog repository that will own the pack (e.g. example-org/example-packs).\n"},
	}
	for _, tt := range tests {
		//nolint:gosec // G204 false positive: the command is this test binary, and the test sets each argument.
		cmd := exec.CommandContext(t.Context(), binary, tt.args...)
		cmd.Env = append(os.Environ(), mainEnv+"=1")
		var stdout, stderr bytes.Buffer
		cmd.Stdout, cmd.Stderr = &stdout, &stderr
		status := 0
		if err := cmd.Run(); err != nil {
			exitErr, ok := errors.AsType[*exec.ExitError](err)
			if !ok {
				t.Fatalf("run the child process: %v", err)
			}
			status = exitErr.ExitCode()
		}
		if status != tt.wantStatus || stdout.String() != tt.wantStdout || stderr.String() != tt.wantStderr {
			t.Errorf("main(%q) = %d, stdout %q, stderr %q; want %d, %q, %q",
				tt.args, status, stdout.String(), stderr.String(), tt.wantStatus, tt.wantStdout, tt.wantStderr)
		}
	}
}

// fakeGH answers each run of gh by its arguments, and keeps the standard
// input of the last run.
type fakeGH map[string]string

func (f fakeGH) Run(args []string, stdin []byte) ([]byte, error) {
	answer, ok := f[strings.Join(args, " ")]
	f["last stdin"] = string(stdin)
	switch {
	case !ok:
		return nil, errors.New("unexpected run")
	case answer == "fail":
		return nil, &issueskeleton.RunError{Stderr: []byte("HTTP 404: Not Found")}
	}
	return []byte(answer), nil
}

// repoGH returns a fake gh for the repository o/r.
func repoGH() fakeGH {
	return fakeGH{
		"repo view o/r --json nameWithOwner":                                                  `{"nameWithOwner": "o/r"}`,
		"api repos/o/r/milestones --paginate":                                                 `[{"number": 7, "title": "Environment pack: Demo"}]`,
		"issue list --repo o/r --state all --limit 2000 --json number,title,milestone,labels": `[]`,
		"label list --repo o/r --limit 500 --json name":                                       `[]`,
		"api --method POST repos/o/r/issues --input -":                                        `{}`,
		"api --method POST repos/o/r/milestones --input -":                                    `{"number": 9}`,
	}
}

func TestRun(t *testing.T) {
	base := []string{"--repo", "o/r", "--pack-id", "demo"}
	tests := []struct {
		name       string
		args       []string
		gh         fakeGH
		wantStatus int
		wantStdout string
		wantStderr string
	}{
		{name: "help", args: []string{"-h"}, wantStatus: 0, wantStdout: usageLine + "\n"},
		{name: "unknown flag", args: []string{"--bogus"}, wantStatus: 2, wantStderr: usageLine + "\n" + name + ": error: flag provided but not defined: -bogus\n"},
		{name: "positional", args: []string{"x"}, wantStatus: 2, wantStderr: name + ": error: unrecognized arguments: x\n"},
		{name: "bad number", args: []string{"--milestone-number", "x"}, wantStatus: 2, wantStderr: `invalid int value: "x"`},
		{name: "no repo", wantStatus: 1, wantStderr: "--repo OWNER/REPOSITORY is required"},
		{name: "bad repo", args: []string{"--repo", "a/b/c"}, wantStatus: 1, wantStderr: "got 'a/b/c'\n"},
		{name: "gh fails", args: []string{"--repo", "x/y"}, gh: fakeGH{"repo view x/y --json nameWithOwner": "fail"}, wantStatus: 1, wantStderr: "HTTP 404: Not Found\n"},
		{name: "no pack id", args: []string{"--repo", "o/r"}, gh: repoGH(), wantStatus: 1, wantStderr: "--pack-id is required\n"},
		{name: "bad pack id", args: []string{"--repo", "o/r", "--pack-id", "Demo"}, gh: repoGH(), wantStatus: 1, wantStderr: "pack id must be lowercase kebab-case"},
		{name: "no milestone", args: append(base, "--milestone-number", " 0 "), gh: repoGH(), wantStatus: 1, wantStderr: "pass --milestone-number or --milestone-title\n"},
		{name: "missing milestone", args: append(base, "--milestone-title", "Gone", "--apply"), gh: repoGH(), wantStatus: 1, wantStderr: "milestone not found: 'Gone'; pass --create-milestone\n"},
		{name: "dry run", args: append(base, "--milestone-title", "Environment pack: Demo", "--source", "s1", "--label", "l1"), gh: repoGH(), wantStdout: "DRY RUN: no GitHub changes will be written. Pass --apply to write.\nCREATE issue in milestone 7: demo: create scenario contract and pack skeleton\n"},
		{name: "default title", args: append(base, "--milestone-number", "7"), gh: repoGH(), wantStdout: "CREATE issue in milestone 7: demo: design topology"},
		{name: "apply", args: append(base, "--title", "Demo", "--milestone-number", "7", "--focus", "f", "--apply", "--refresh-existing", "--create-milestone"), gh: repoGH(), wantStdout: "created issue: demo: create scenario contract and pack skeleton\n"},
		{name: "dry run with a new milestone", args: append(base, "--milestone-title", "Gone"), gh: repoGH(), wantStdout: "CREATE milestone: Gone\nCREATE issue in milestone Gone: demo: create scenario contract and pack skeleton\n"},
		{name: "apply with a new milestone", args: append(base, "--milestone-title", "Gone", "--create-milestone", "--apply"), gh: repoGH(), wantStdout: "created milestone 9: Gone\ncreated issue: demo: create scenario contract and pack skeleton\n"},
		{name: "defect", args: append(base, "--milestone-number", "7"), gh: fakeGH{"repo view o/r --json nameWithOwner": `{"nameWithOwner": "o/r"}`}, wantStatus: 3, wantStderr: name + ": internal error (*errors.errorString)\n"},
	}
	for _, tt := range tests {
		var stdout, stderr strings.Builder
		status := run(tt.args, &stdout, &stderr, tt.gh)
		if status != tt.wantStatus || !strings.Contains(stdout.String(), tt.wantStdout) || !strings.Contains(stderr.String(), tt.wantStderr) ||
			tt.wantStdout == "" && stdout.Len() > 0 || tt.wantStderr == "" && stderr.Len() > 0 {
			t.Errorf("run() with %s = %d, stdout %q, stderr %q; want %d, stdout with %q, stderr with %q",
				tt.name, status, stdout.String(), stderr.String(), tt.wantStatus, tt.wantStdout, tt.wantStderr)
		}
	}
}

// fakeGHScript writes an executable gh to a new directory at the front of
// PATH.
func fakeGHScript(t *testing.T, script string) {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "gh"), []byte("#!/bin/sh\n"+script), 0o700); err != nil { //nolint:gosec // G306 false positive: the test makes an executable script in its own directory.
		t.Fatalf("write the fake gh: %v", err)
	}
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))
}

// TestDefaultTitle checks that the title of a pack without --title comes
// from its id, in the body of each issue.
func TestDefaultTitle(t *testing.T) {
	gh := repoGH()
	var stdout, stderr strings.Builder
	status := run([]string{"--repo", "o/r", "--pack-id", "two-words", "--milestone-number", "7", "--apply"}, &stdout, &stderr, gh)
	if status != 0 || !strings.Contains(gh["last stdin"], `- Working title: Two Words\n`) {
		t.Errorf("run() = %d, stderr %q, last payload %q; want a body with the title Two Words", status, stderr.String(), gh["last stdin"])
	}
}

func TestGHRunner(t *testing.T) {
	fakeGHScript(t, `if [ "$1" = fail ]; then echo "gh says no" >&2; echo partial; exit 1; fi; printf '%s|' "$@"; cat`)
	out, err := ghRunner{}.Run([]string{"api", "x y"}, []byte("payload"))
	if err != nil || string(out) != "api|x y|payload" {
		t.Errorf("Run() = %q, %v; want the arguments and the standard input", out, err)
	}
	_, err = ghRunner{}.Run([]string{"fail"}, nil)
	runErr, ok := errors.AsType[*issueskeleton.RunError](err)
	if !ok || string(runErr.Stderr) != "gh says no\n" || string(runErr.Stdout) != "partial\n" {
		t.Errorf("Run() of a failed gh error = %#v, want a RunError with its output", err)
	}
}

func TestGHRunnerMissing(t *testing.T) {
	t.Setenv("PATH", t.TempDir())
	if _, err := (ghRunner{}).Run([]string{"x"}, nil); err == nil {
		t.Error("Run() without gh: no error")
	} else if _, ok := errors.AsType[*issueskeleton.RunError](err); ok {
		t.Errorf("Run() without gh error = %v, want an error that is not a RunError", err)
	}
}

// TestGHPathRefusesFilesOthersCanWrite checks that the command does not run a
// gh that other users can replace.
func TestGHPathRefusesFilesOthersCanWrite(t *testing.T) {
	safe := t.TempDir()
	open := t.TempDir()
	//nolint:gosec // G302 false positive: the test makes its own directory writable by others, to show that the command refuses it.
	if err := os.Chmod(open, 0o777); err != nil {
		t.Fatalf("make the directory writable: %v", err)
	}
	write := func(dir, name string, mode os.FileMode) string {
		path := filepath.Join(dir, name)
		if err := os.WriteFile(path, []byte("#!/bin/sh\n"), 0o700); err != nil { //nolint:gosec // G306 false positive: the test makes an executable script in its own directory.
			t.Fatalf("write %s: %v", path, err)
		}
		if err := os.Chmod(path, mode); err != nil {
			t.Fatalf("chmod %s: %v", path, err)
		}
		return path
	}
	target := write(open, "real-gh", 0o700)
	linkDir := t.TempDir()
	if err := os.Symlink(target, filepath.Join(linkDir, "gh")); err != nil {
		t.Fatalf("link gh: %v", err)
	}
	fileDir := t.TempDir()
	write(fileDir, "gh", 0o777)
	write(open, "gh", 0o700)
	for name, dir := range map[string]string{"directory": open, "target directory": linkDir, "file": fileDir} {
		t.Setenv("PATH", dir)
		_, err := ghPath()
		if e, ok := errors.AsType[*issueskeleton.Error](err); !ok || !strings.Contains(e.Message, "is not safe to run: other users can write") {
			t.Errorf("ghPath() with a %s that others can write error = %v", name, err)
		}
		if _, err := (ghRunner{}).Run([]string{"x"}, nil); !errors.As(err, new(*issueskeleton.Error)) {
			t.Errorf("Run() with a %s that others can write error = %v, want the refusal", name, err)
		}
	}
	write(safe, "gh", 0o700)
	t.Setenv("PATH", safe)
	if got, err := ghPath(); err != nil || got != filepath.Join(safe, "gh") {
		t.Errorf("ghPath() = %q, %v; want the gh in the safe directory", got, err)
	}
}

func TestGHPathErrors(t *testing.T) {
	t.Setenv("PATH", ".")
	if got, err := ghPath(); !errors.Is(err, exec.ErrNotFound) {
		t.Errorf("ghPath() without gh = %q, %v; want %v", got, err, exec.ErrNotFound)
	}
}
