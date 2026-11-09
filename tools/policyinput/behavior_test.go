package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/google/go-cmp/cmp"
)

func child(t *testing.T, dir string, environment []string, name string, args ...string) ([]byte, error) {
	t.Helper()
	ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancel()
	var cmd *exec.Cmd
	switch name {
	case "make":
		cmd = exec.CommandContext(ctx, "make", args...) //nolint:gosec // Tests supply fixed recipes, fake tools, and a credential-free environment under a deadline.
	case "bash":
		cmd = exec.CommandContext(ctx, "bash", args...) //nolint:gosec // The reviewed aggregate script runs only with synthetic job results and no credentials.
	default:
		t.Fatalf("unsupported test command %q", name)
	}
	cmd.Dir = dir
	cmd.Env = append([]string{"PATH=/usr/bin:/bin", "LC_ALL=C"}, environment...)
	return cmd.CombinedOutput()
}

func executable(t *testing.T, dir, name, script string) string {
	t.Helper()
	file := filepath.Join(dir, name)
	if err := os.WriteFile(file, []byte("#!/bin/sh\n"+script), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(file, 0o700); err != nil { //nolint:gosec // A script in t.TempDir needs owner execute permission; no group or other access is granted.
		t.Fatal(err)
	}
	return file
}

func readFixture(t *testing.T, dir, name string) []byte {
	t.Helper()
	root, err := os.OpenRoot(dir)
	if err != nil {
		t.Fatal(err)
	}
	data, readErr := fs.ReadFile(root.FS(), name)
	closeErr := root.Close()
	if readErr != nil {
		t.Fatal(readErr)
	}
	if closeErr != nil {
		t.Fatal(closeErr)
	}
	return data
}

func TestPromotionBehavior(t *testing.T) {
	dir := t.TempDir()
	fake := executable(t, dir, "gh", `printf '%s\000' "$@" > "$RECORD"
exit "${RESULT:-0}"
`)
	record := filepath.Join(dir, "argv")
	environment := []string{"RECORD=" + record}
	for _, goal := range []string{"", "help"} {
		args := []string{"-f", "../../Makefile", "GH=" + fake}
		if goal != "" {
			args = append(args, goal)
		}
		if output, err := child(t, ".", environment, "make", args...); err != nil {
			t.Fatalf("make %q failed: %v: %s", goal, err, output)
		}
		if _, err := os.Stat(record); !os.IsNotExist(err) {
			t.Fatal("safe make goal invoked gh")
		}
	}
	if output, err := child(t, ".", environment, "make", "-f", "../../Makefile", "devmain", "GH="+fake); err != nil {
		t.Fatalf("make devmain failed: %v: %s", err, output)
	}
	data := readFixture(t, dir, "argv")
	checkPromotionArguments(t, data)
	if _, err := child(t, ".", append(environment, "RESULT=42"), "make", "-f", "../../Makefile", "devmain", "GH="+fake); err == nil {
		t.Error("make devmain suppressed gh failure")
	}
}

func checkPromotionArguments(t *testing.T, data []byte) {
	t.Helper()
	args := strings.Split(strings.TrimSuffix(string(data), "\x00"), "\x00")
	if len(args) < 2 || !slices.Equal(args[:2], []string{"pr", "create"}) {
		t.Fatalf("gh args = %q, want pr create", args)
	}
	flags := map[string]string{}
	for i := 2; i < len(args); i += 2 {
		if i+1 >= len(args) {
			t.Fatalf("unexpected gh args %q", args)
		}
		flags[args[i]] = args[i+1]
	}
	want := map[string]string{"--base": "main", "--head": "dev", "--title": "chore: promote dev to main"}
	for flag, value := range want {
		if flags[flag] != value {
			t.Errorf("gh %s = %q, want %q", flag, flags[flag], value)
		}
	}
	if len(flags) != 4 {
		t.Errorf("gh flags = %v, want base/head/title/body only", flags)
	}
	body := strings.ToLower(flags["--body"])
	for _, phrase := range []string{"merge commit", "do not squash", "do not rebase", "release-please"} {
		if !strings.Contains(body, phrase) {
			t.Errorf("promotion body lacks %q", phrase)
		}
	}
}

func TestGoPlatformGateBehavior(t *testing.T) {
	dir := t.TempDir()
	for _, target := range []string{"go-lint", "go-audit"} {
		fake := executable(t, dir, "go-fails", `if [ "$1" = run ]; then exit 42; fi
exit 0
`)
		if _, err := child(t, ".", nil, "make", "-f", "../../Makefile", target, "GO="+fake, "MISE=true"); err == nil {
			t.Errorf("%s ignored platform discovery failure", target)
		}
	}
	fake := executable(t, dir, "go", `if [ "$1" = run ]; then printf 'linux/amd64\nlinux/arm64\ndarwin/amd64\ndarwin/arm64\n'; fi
`)
	check := executable(t, dir, "mise", `printf '%s/%s\n' "$GOOS" "$GOARCH" >> "$RECORD"
`)
	record := filepath.Join(dir, "platforms")
	if output, err := child(t, ".", []string{"RECORD=" + record}, "make", "-f", "../../Makefile", "go-audit", "GO="+fake, "MISE="+check); err != nil {
		t.Fatalf("go-audit failed: %v: %s", err, output)
	}
	data := readFixture(t, dir, "platforms")
	if diff := cmp.Diff([]string{"linux/amd64", "linux/arm64", "darwin/amd64", "darwin/arm64"}, strings.Fields(string(data))); diff != "" {
		t.Errorf("audit platforms (-want +got):\n%s", diff)
	}
}

func TestAggregateScriptBehavior(t *testing.T) {
	input, err := collect(repository(t))
	if err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(input.Documents[".github/workflows/ci.yml"])
	if err != nil {
		t.Fatal(err)
	}
	var workflow struct {
		Jobs map[string]struct {
			Steps []struct {
				Run string            `json:"run"`
				Env map[string]string `json:"env"`
			} `json:"steps"`
		} `json:"jobs"`
	}
	if err := json.Unmarshal(data, &workflow); err != nil {
		t.Fatal(err)
	}
	var script string
	var variables map[string]string
	for _, s := range workflow.Jobs["verify"].Steps {
		if s.Run != "" && len(s.Env) > 0 {
			script = s.Run
			variables = s.Env
			break
		}
	}
	if script == "" {
		t.Fatal("verify has no executable result guard")
	}
	//nolint:misspell // GitHub's job-result spelling is part of its external contract.
	for _, bad := range []string{"success", "failure", "cancelled", "skipped", ""} {
		for failed := range variables {
			checkAggregateResult(t, script, variables, failed, bad)
		}
	}
}

func checkAggregateResult(t *testing.T, script string, variables map[string]string, failed, bad string) {
	t.Helper()
	var environment []string
	for name := range variables {
		value := "success"
		if name == failed {
			value = bad
		}
		environment = append(environment, name+"="+value)
	}
	_, err := child(t, t.TempDir(), environment, "bash", "-c", script)
	if (err == nil) != (bad == "success") {
		t.Errorf("aggregate %s=%q error=%v", failed, bad, err)
	}
}

func TestCollectorCommandStreams(t *testing.T) {
	var stdout, stderr bytes.Buffer
	if got := run(repository(t), &stdout, &stderr); got != 0 || stdout.Len() == 0 || stderr.Len() != 0 {
		t.Fatalf("run(valid) = %d, stdout=%d bytes, stderr=%q", got, stdout.Len(), stderr.String())
	}
	stdout.Reset()
	stderr.Reset()
	if got := run(hiddenFS{FS: repository(t), hidden: "Makefile"}, &stdout, &stderr); got != 3 {
		t.Errorf("run(missing) = %d, want 3", got)
	}
	if !strings.Contains(stdout.String(), "policy-input") {
		t.Error("collector failure lacks stable rule")
	}
}
