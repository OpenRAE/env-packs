package packfs

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"golang.org/x/sys/unix"
)

// pathOnlyFault makes the call-th Openat open a path-only descriptor of the
// directory. Linux fails fchmod on such a descriptor with EBADF, but the
// descriptor is open, so a missing close shows as a leak.
type pathOnlyFault struct {
	unixSystem

	call  int
	calls int
}

func (f *pathOnlyFault) Openat(dir *os.File, path string, flags int, mode uint32) (*os.File, error) {
	f.calls++
	if f.calls == f.call {
		flags = unix.O_PATH | unix.O_DIRECTORY | unix.O_NOFOLLOW | unix.O_CLOEXEC
	}
	return f.unixSystem.Openat(dir, path, flags, mode)
}

func TestWriteMemberDirectoryModeFault(t *testing.T) {
	root := t.TempDir()
	noLeak(t, "mode of the directory", func() {
		err := writeMember(&pathOnlyFault{call: 1}, root, "d/file", []byte("content"))
		if reasonOf(err) != ReasonWriteFailed || !wantEBADF(err) {
			t.Errorf("writeMember() with a failed directory mode = %v, want ReasonWriteFailed with EBADF", err)
		}
	})
}

func TestReplaceRollbackFault(t *testing.T) {
	staged, target := staging(t)
	f := newFault("Renameat2", 2, failCall)
	f.err = unix.EIO
	changed := errors.New("pack changed")
	err := replace(f, staged, target, func(string) error { return changed })
	e, ok := errors.AsType[*Error](err)
	if !ok || e.Reason != ReasonRecovery || e.Path != staged || !errors.Is(err, unix.EIO) {
		t.Errorf("replace() with a failed rollback = %v, want ReasonRecovery at %s", err, staged)
	}
	if got := readFile(t, filepath.Join(staged, "file")); got != "old" {
		t.Errorf("the recovery path has %q, want the original tree", got)
	}
}

// Regression test for #617: failed panic rollback must retain the recovery path.
func TestReplacePanicRecovery(t *testing.T) {
	defer func() {
		if recover() != nil {
			t.Error("replace() propagated a panic instead of returning the recovery path")
		}
	}()
	staged, target := staging(t)
	f := newFault("Renameat2", 2, failCall)
	f.err = unix.EIO
	err := replace(f, staged, target, func(string) error { panic("private defect") })
	e, ok := errors.AsType[*Error](err)
	if !ok || e.Reason != ReasonRecovery || e.Path != staged || !errors.Is(err, unix.EIO) {
		t.Fatalf("replace() = %v, want recovery path and rollback cause", err)
	}
	if got := readFile(t, filepath.Join(staged, "file")); got != "old" {
		t.Errorf("recovery path = %q, want old", got)
	}
}
