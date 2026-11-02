package raes

import "testing"

func TestErrorMessage(t *testing.T) {
	err := &Error{Code: "import-phase-refused", Diagnostics: []Diagnostic{{Code: "c", Pointer: "/imports/0"}}}
	if got := err.Error(); got != "raes: import-phase-refused" {
		t.Errorf("Error() = %q, want %q", got, "raes: import-phase-refused")
	}
}
