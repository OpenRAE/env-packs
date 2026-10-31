package testgate

import (
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestSortFindings(t *testing.T) {
	a := Finding{Location: "a.go:1", Rule: "r", Message: "m", Fix: "f"}
	b := Finding{Location: "a.go:1", Rule: "s", Message: "m", Fix: "f"}
	c := Finding{Location: "a.go:1", Rule: "s", Message: "n", Fix: "f"}
	d := Finding{Location: "a.go:1", Rule: "s", Message: "n", Fix: "g"}
	e := Finding{Location: "b.go:1", Rule: "r", Message: "m", Fix: "f"}
	got := SortFindings([]Finding{e, d, c, b, a, e, a})
	if diff := cmp.Diff([]Finding{a, b, c, d, e}, got); diff != "" {
		t.Errorf("SortFindings() mismatch (-want +got):\n%s", diff)
	}
}

func TestFindingString(t *testing.T) {
	f := Finding{Location: "a.go:3", Rule: "mutant", Message: "no test kills it", Fix: "Add a test."}
	want := "a.go:3: mutant: no test kills it\n\tfix: Add a test."
	if got := f.String(); got != want {
		t.Errorf("Finding.String() = %q, want %q", got, want)
	}
}
