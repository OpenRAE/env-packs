package packfs

import (
	"errors"
	"os"
	"path/filepath"

	"golang.org/x/sys/unix"
)

// The flags of renameat2: RENAME_NOREPLACE and RENAME_EXCHANGE.
const (
	renameNoReplace = 1
	renameExchange  = 2
)

// errUnsupported marks a platform without renameat2.
var errUnsupported = errors.New("renameat2 is not available on this platform")

// system holds the system calls of the package that the os package does not
// have. A test replaces it to fail a call.
type system interface {
	// Openat opens path relative to the directory dir.
	Openat(dir *os.File, path string, flags int, mode uint32) (*os.File, error)
	// Lstatat inspects path relative to the directory dir. It does not
	// follow a symlink.
	Lstatat(dir *os.File, path string) (unix.Stat_t, error)
	// Renameat2 renames oldpath to newpath with the flags of renameat2.
	Renameat2(oldpath, newpath string, flags uint) error
}

// unixSystem calls the operating system.
type unixSystem struct{}

// Openat calls openat. The name of the file is path below the name of dir.
func (unixSystem) Openat(dir *os.File, path string, flags int, mode uint32) (*os.File, error) {
	fd, err := unix.Openat(int(dir.Fd()), path, flags, mode)
	if err != nil {
		return nil, err
	}
	return os.NewFile(uintptr(fd), filepath.Join(dir.Name(), path)), nil
}

// Lstatat calls fstatat with AT_SYMLINK_NOFOLLOW.
func (unixSystem) Lstatat(dir *os.File, path string) (unix.Stat_t, error) {
	var st unix.Stat_t
	err := unix.Fstatat(int(dir.Fd()), path, &st, unix.AT_SYMLINK_NOFOLLOW)
	return st, err
}

// closeReadOnly closes a descriptor that the package opened only to look up
// names or to read. As in os.ReadDir, a failed close of such a descriptor
// loses no data, so closeReadOnly does not report it.
func closeReadOnly(f *os.File) {
	_ = f.Close() //nolint:errcheck // A read-only descriptor loses no data when its close fails, as in os.ReadDir.
}
