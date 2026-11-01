package packfs

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"golang.org/x/sys/unix"
)

// readFile reads the file at path.
func readFile(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path) //nolint:gosec // G304 false positive: the test reads files in its own temporary directory.
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	return string(data)
}

// mode returns the permission bits of the file at path.
func mode(t *testing.T, path string) os.FileMode {
	t.Helper()
	info, err := os.Lstat(path)
	if err != nil {
		t.Fatalf("stat %s: %v", path, err)
	}
	return info.Mode().Perm()
}

func TestWriteMember(t *testing.T) {
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, "a"), 0o700); err != nil {
		t.Fatalf("make a: %v", err)
	}
	if err := WriteMember(root, "a/b/c.txt", []byte("first")); err != nil {
		t.Fatalf("WriteMember() error = %v", err)
	}
	if err := WriteMember(root, "a/b/c.txt", []byte("second")); err != nil {
		t.Fatalf("WriteMember() again: error = %v", err)
	}
	if got := readFile(t, filepath.Join(root, "a", "b", "c.txt")); got != "second" {
		t.Errorf("WriteMember() wrote %q, want %q", got, "second")
	}
	for path, want := range map[string]os.FileMode{"a": 0o755, "a/b": 0o755, "a/b/c.txt": 0o600} {
		if got := mode(t, filepath.Join(root, path)); got != want {
			t.Errorf("mode of %s = %v, want %v", path, got, want)
		}
	}
}

func TestWriteMemberUnwritableDirectory(t *testing.T) {
	root := t.TempDir()
	if err := os.Chmod(root, 0o500); err != nil { //nolint:gosec // G302 false positive: the test removes the write permission from its own directory.
		t.Fatalf("make the staging root read-only: %v", err)
	}
	t.Cleanup(func() {
		if err := os.Chmod(root, 0o700); err != nil { //nolint:gosec // G302 false positive: the test restores the mode of its own directory.
			t.Errorf("restore the mode of the staging root: %v", err)
		}
	})
	err := WriteMember(root, "d/file", []byte("x"))
	if reasonOf(err) != ReasonWriteFailed || !errors.Is(err, unix.EACCES) {
		t.Errorf("WriteMember() below a read-only directory = %v, want ReasonWriteFailed with EACCES", err)
	}
}

func TestWriteMemberSizes(t *testing.T) {
	root := t.TempDir()
	for _, content := range []string{"", "x", "xy"} {
		rel := "f" + content
		if err := WriteMember(root, rel, []byte(content)); err != nil {
			t.Fatalf("WriteMember(%q) error = %v", rel, err)
		}
		if got := readFile(t, filepath.Join(root, rel)); got != content {
			t.Errorf("WriteMember(%q) wrote %q, want %q", rel, got, content)
		}
	}
}

func TestWriteMemberRejections(t *testing.T) {
	root := tree(t, entry{kind: "symlink", path: "link", target: "elsewhere"}, entry{kind: "symlink", path: "dirlink", target: "."})
	tests := []struct {
		root  string
		rel   string
		want  Reason
		cause error
	}{
		{root: root, rel: "../x", want: ReasonNameNotCanonical},
		{root: root, rel: "link", want: ReasonWriteFailed, cause: unix.ELOOP},
		{root: root, rel: "dirlink/x", want: ReasonWriteFailed},
		{root: filepath.Join(root, "missing"), rel: "x", want: ReasonWriteFailed, cause: os.ErrNotExist},
	}
	for _, tt := range tests {
		err := WriteMember(tt.root, tt.rel, []byte("x"))
		if reasonOf(err) != tt.want || tt.cause != nil && !errors.Is(err, tt.cause) {
			t.Errorf("WriteMember(%q) = %v, want reason %q with cause %v", tt.rel, err, tt.want, tt.cause)
		}
	}
	if _, err := os.Lstat(filepath.Join(root, "elsewhere")); !errors.Is(err, os.ErrNotExist) {
		t.Errorf("WriteMember() followed the symlink: %v", err)
	}
}

// staging returns a staged tree with one file and an existing target tree.
func staging(t *testing.T) (staged, target string) {
	t.Helper()
	dir := tree(t,
		entry{kind: "file", path: "staged/file", target: "new"},
		entry{kind: "file", path: "target/file", target: "old"},
	)
	return filepath.Join(dir, "staged"), filepath.Join(dir, "target")
}

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
