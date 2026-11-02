package packfs

import "golang.org/x/sys/unix"

// Renameat2 calls renameat2 with paths relative to the working directory.
func (unixSystem) Renameat2(oldpath, newpath string, flags uint) error {
	return unix.Renameat2(unix.AT_FDCWD, oldpath, unix.AT_FDCWD, newpath, flags)
}
