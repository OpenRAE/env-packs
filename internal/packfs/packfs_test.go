package packfs

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"golang.org/x/sys/unix"
)

// entry is one member of a test tree.
type entry struct {
	// kind is "file", "dir", "symlink", "hardlink", or "fifo".
	kind string
	// path is the path of the member, relative to the root.
	path string
	// target is the content of a file, the target of a symlink, or the
	// existing file of a hardlink.
	target string
}

// tree makes a test tree in a new directory and returns the directory.
func tree(t *testing.T, entries ...entry) string {
	t.Helper()
	root := t.TempDir()
	for _, e := range entries {
		path := filepath.Join(root, filepath.FromSlash(e.path))
		if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
			t.Fatalf("make the directory of %s: %v", e.path, err)
		}
		var err error
		switch e.kind {
		case "file":
			err = os.WriteFile(path, []byte(e.target), 0o600)
		case "dir":
			err = os.Mkdir(path, 0o750)
		case "symlink":
			err = os.Symlink(e.target, path)
		case "hardlink":
			err = os.Link(filepath.Join(root, filepath.FromSlash(e.target)), path)
		case "fifo":
			err = unix.Mkfifo(path, 0o600)
		default:
			t.Fatalf("unknown kind %q", e.kind)
		}
		if err != nil {
			t.Fatalf("make %s %s: %v", e.kind, e.path, err)
		}
	}
	return root
}

// openRoot opens the pack root dir, and closes it at the end of the test.
func openRoot(t *testing.T, dir string) *Root {
	t.Helper()
	r, err := Open(dir)
	if err != nil {
		t.Fatalf("Open(%s) error = %v", dir, err)
	}
	t.Cleanup(func() {
		if err := r.Close(); err != nil {
			t.Errorf("close the root: %v", err)
		}
	})
	return r
}

// reasonOf returns the reason of err, or the empty string when err is not an
// *Error.
func reasonOf(err error) Reason {
	if e, ok := errors.AsType[*Error](err); ok {
		return e.Reason
	}
	return ""
}

// wantReason checks that err is an *Error with the reason want.
func wantReason(t *testing.T, err error, want Reason) {
	t.Helper()
	if got := reasonOf(err); got != want {
		t.Errorf("error = %v (reason %q), want reason %q", err, got, want)
	}
}
