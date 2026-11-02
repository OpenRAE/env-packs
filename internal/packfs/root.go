package packfs

import (
	"io/fs"
	"os"

	"golang.org/x/sys/unix"
)

// The flags that open a directory without a symlink at the last component.
const dirFlags = unix.O_RDONLY | unix.O_DIRECTORY | unix.O_NOFOLLOW | unix.O_CLOEXEC

// noMode is the mode argument of an open without O_CREAT, which ignores it.
const noMode = 0

// A Root is an open pack root directory. Its operations resolve each member
// path from the root descriptor. Close releases the descriptor.
type Root struct {
	sys  system
	path string
	dir  *os.File
}

// Open opens the pack root directory at path. It rejects an empty path, a
// symlink, and a path that is not an accessible directory.
func Open(path string) (*Root, error) {
	return open(unixSystem{}, path)
}

// open opens a pack root with the system calls of sys.
func open(sys system, path string) (*Root, error) {
	if path == "" {
		return nil, fail(ReasonRootEmpty, "pack root is empty", nil)
	}
	// An open with O_NOFOLLOW and O_DIRECTORY reports a symlink as a path
	// that is not a directory, so Lstat finds the symlink first. When Lstat
	// fails, the open fails too and reports the cause.
	if info, err := os.Lstat(path); err == nil && info.Mode()&fs.ModeSymlink != 0 {
		return nil, fail(ReasonRootSymlink, "pack root is a symlink", nil)
	}
	dir, err := os.OpenFile(path, dirFlags, noMode) //nolint:gosec // G304 false positive: the caller chooses the pack root, and each read stays below it.
	if err != nil {
		return nil, inaccessible(err)
	}
	return &Root{sys: sys, path: path, dir: dir}, nil
}

func inaccessible(err error) *Error {
	return fail(ReasonRootInaccessible, "pack root is not an accessible directory", err)
}

// Path returns the path that opened the root.
func (r *Root) Path() string {
	return r.path
}

// Close releases the root descriptor.
func (r *Root) Close() error {
	return r.dir.Close()
}
