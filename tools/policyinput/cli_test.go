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
	if os.Getenv("POLICYINPUT_TEST_PROCESS") == "1" {
		main()
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

func checkProcessFailure(t *testing.T, err error, output []byte) {
	t.Helper()
	var exit *exec.ExitError
	if !errors.As(err, &exit) || exit.ExitCode() != 3 || !strings.Contains(string(output), "policy-input") {
		t.Fatalf("collector failure = %v, %q, want policy-input and status 3", err, output)
	}
}
