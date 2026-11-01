package packfs

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

// The transactions need renameat2, which only Linux has. On the other
// platforms, transactions_other_test.go checks the unsupported result.

func TestPublishNew(t *testing.T) {
	staged, target := staging(t)
	fresh := filepath.Join(filepath.Dir(target), "fresh")
	if err := PublishNew(staged, fresh); err != nil {
		t.Fatalf("PublishNew() error = %v", err)
	}
	if got := readFile(t, filepath.Join(fresh, "file")); got != "new" {
		t.Errorf("PublishNew() target has %q, want %q", got, "new")
	}
	staged, target = staging(t)
	wantReason(t, PublishNew(staged, target), ReasonTargetExists)
	wantReason(t, PublishNew(filepath.Join(staged, "missing"), fresh+"2"), ReasonPublishFailed)
}

func TestExchange(t *testing.T) {
	staged, target := staging(t)
	if err := Exchange(staged, target); err != nil {
		t.Fatalf("Exchange() error = %v", err)
	}
	if readFile(t, filepath.Join(target, "file")) != "new" || readFile(t, filepath.Join(staged, "file")) != "old" {
		t.Error("Exchange() did not swap the trees")
	}
	wantReason(t, Exchange(staged, filepath.Join(target, "missing")), ReasonExchangeFailed)
}

func TestReplace(t *testing.T) {
	staged, target := staging(t)
	var previous string
	err := Replace(staged, target, func(p string) error {
		previous = readFile(t, filepath.Join(p, "file"))
		return nil
	})
	if err != nil || previous != "old" || readFile(t, filepath.Join(target, "file")) != "new" {
		t.Errorf("Replace() = %v, previous %q; want nil, the old tree, and the new target", err, previous)
	}
}

func TestReplaceRollback(t *testing.T) {
	staged, target := staging(t)
	changed := errors.New("pack changed")
	err := Replace(staged, target, func(string) error { return changed })
	if !errors.Is(err, changed) || readFile(t, filepath.Join(target, "file")) != "old" {
		t.Errorf("Replace() = %v; want the check error and the old target", err)
	}
}

func TestReplaceRecovery(t *testing.T) {
	staged, target := staging(t)
	changed := errors.New("pack changed")
	err := Replace(staged, target, func(string) error {
		if err := os.Rename(target, target+".moved"); err != nil {
			t.Fatalf("move the target: %v", err)
		}
		return changed
	})
	e, ok := errors.AsType[*Error](err)
	if !ok || e.Reason != ReasonRecovery || e.Path != staged || !errors.Is(err, changed) {
		t.Fatalf("Replace() = %v, want ReasonRecovery at %s with the check error", err, staged)
	}
	if got := readFile(t, filepath.Join(staged, "file")); got != "old" {
		t.Errorf("the recovery path has %q, want the original tree", got)
	}
}

func TestReplaceExchangeFailure(t *testing.T) {
	staged, target := staging(t)
	called := false
	err := Replace(staged, filepath.Join(target, "missing"), func(string) error {
		called = true
		return nil
	})
	if reasonOf(err) != ReasonExchangeFailed || called {
		t.Errorf("Replace() = %v, check called %v; want ReasonExchangeFailed and no check", err, called)
	}
}
