package main

import (
	"path/filepath"
	"slices"
	"strings"
	"testing"
)

func TestPolicyGateStopsAtEachFailure(t *testing.T) {
	want := []string{"verify", "collect", "test", "lint", "proof"}
	for _, failed := range append([]string{""}, want...) {
		t.Run("fail-"+failed, func(t *testing.T) {
			dir := t.TempDir()
			record := filepath.Join(dir, "phases")
			mise := executable(t, dir, "mise", `if [ "$3" = actionlint ]; then phase=lint; else phase=$4; fi
printf '%s\n' "$phase" >> "$RECORD"
if [ "$FAIL" = "$phase" ]; then exit 42; fi
`)
			goTool := executable(t, dir, "go", `if [ "$1" = run ]; then phase=collect; printf '{}\n'; else phase=proof; fi
printf '%s\n' "$phase" >> "$RECORD"
if [ "$FAIL" = "$phase" ]; then exit 42; fi
`)
			output, err := child(t, "../..", []string{"RECORD=" + record, "FAIL=" + failed}, "make", "policy", "GO="+goTool, "MISE="+mise)
			if (err == nil) != (failed == "") {
				t.Fatalf("make policy FAIL=%q error=%v: %s", failed, err, output)
			}
			data := readFixture(t, dir, "phases")
			phases := strings.Fields(string(data))
			expected := want
			if failed != "" {
				expected = want[:slices.Index(want, failed)+1]
			}
			if !slices.Equal(phases, expected) {
				t.Errorf("policy phases = %q, want %q", phases, expected)
			}
		})
	}
}
