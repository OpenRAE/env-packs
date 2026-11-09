package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"
)

func TestCollectorProcess(t *testing.T) {
	if runTestProcess(t) {
		return
	}
	program, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		dir   string
		valid bool
	}{{"../..", true}, {t.TempDir(), false}} {
		ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
		//nolint:gosec // G204: execute this test binary with fixed arguments and a credential-free environment.
		cmd := exec.CommandContext(ctx, program, "-test.run=^TestCollectorProcess$")
		cmd.Dir = tc.dir
		cmd.Env = []string{"PATH=/usr/bin:/bin", "POLICYINPUT_TEST_PROCESS=1"}
		output, runErr := cmd.Output()
		cancel()
		if (runErr == nil) != tc.valid {
			t.Fatalf("collector valid=%t: %v", tc.valid, runErr)
		}
		if !tc.valid {
			checkProcessFailure(t, runErr, output)
			continue
		}
		var value map[string]any
		if err := json.Unmarshal(output, &value); err != nil {
			t.Fatalf("collector JSON: %v", err)
		}
		if tc.valid && value["documents"] == nil {
			t.Error("successful collector omitted documents")
		}
	}
}

func runTestProcess(t *testing.T) bool {
	t.Helper()
	mode := os.Getenv("POLICYINPUT_TEST_PROCESS")
	if mode == "" {
		return false
	}
	if mode == "deny" {
		if err := os.Chmod(".", 0); err != nil {
			t.Fatal(err)
		}
	}
	main()
	return true
}

func TestCollectorRootFailure(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("root bypasses the directory permission refusal")
	}
	dir := t.TempDir()
	t.Cleanup(func() {
		//nolint:gosec // G302: restore owner access to this test's temporary directory.
		if err := os.Chmod(dir, 0o700); err != nil {
			t.Error(err)
		}
	})
	program, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithTimeout(t.Context(), 5*time.Second)
	defer cancel()
	//nolint:gosec // G204: execute this test binary with fixed arguments and no credentials.
	cmd := exec.CommandContext(ctx, program, "-test.run=^TestCollectorProcess$")
	cmd.Dir = dir
	cmd.Env = []string{"PATH=/usr/bin:/bin", "POLICYINPUT_TEST_PROCESS=deny"}
	output, err := cmd.Output()
	var exit *exec.ExitError
	if !errors.As(err, &exit) || exit.ExitCode() != 3 || len(output) != 0 {
		t.Fatalf("inaccessible root = %v, %q, want status 3 and no output", err, output)
	}
}

func checkProcessFailure(t *testing.T, err error, output []byte) {
	t.Helper()
	var exit *exec.ExitError
	if !errors.As(err, &exit) || exit.ExitCode() != 3 || !strings.Contains(string(output), "policy-input") {
		t.Fatalf("collector failure = %v, %q, want policy-input and status 3", err, output)
	}
}
