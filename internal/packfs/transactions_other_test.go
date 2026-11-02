//go:build !linux

package packfs

import (
	"errors"
	"testing"
)

// TestTransactionsUnsupported checks that each transaction reports an
// unsupported platform without renameat2.
func TestTransactionsUnsupported(t *testing.T) {
	staged, target := staging(t)
	results := map[string]error{
		"PublishNew": PublishNew(staged, target+".new"),
		"Exchange":   Exchange(staged, target),
		"Replace":    Replace(staged, target, func(string) error { return nil }),
	}
	for name, err := range results {
		if reasonOf(err) != ReasonUnsupportedPlatform || !errors.Is(err, errUnsupported) {
			t.Errorf("%s() = %v, want ReasonUnsupportedPlatform", name, err)
		}
	}
}
