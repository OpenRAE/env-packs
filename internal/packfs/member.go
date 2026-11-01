package packfs

import (
	"io"
	"os"
	"strings"

	"golang.org/x/sys/unix"
)

// memberFlags open a member file. O_NONBLOCK keeps the open of a FIFO from
// blocking, so that the type check can reject it.
const memberFlags = unix.O_RDONLY | unix.O_NOFOLLOW | unix.O_NONBLOCK | unix.O_CLOEXEC

// OpenMember opens the regular file at the canonical path rel. It opens each
// directory and the file without following a symlink. It rejects a file that
// is not a regular file with one link. The caller closes the file.
func (r *Root) OpenMember(rel string) (*os.File, error) {
	if _, err := NormalizeRelpath(rel); err != nil {
		return nil, err
	}
	parts := strings.Split(rel, "/")
	dir, err := r.openDir(parts[:len(parts)-1])
	if err != nil {
		return nil, err
	}
	defer closeReadOnly(dir)
	f, err := r.sys.Openat(dir, parts[len(parts)-1], memberFlags, noMode)
	if err != nil {
		return nil, memberUnopenable(err)
	}
	if err := checkRegular(f); err != nil {
		closeReadOnly(f)
		return nil, err
	}
	return f, nil
}

// openDir opens the directory at the path components parts below the root,
// one component at a time and without following a symlink. It returns a new
// descriptor, which the caller closes.
func (r *Root) openDir(parts []string) (*os.File, error) {
	dir, err := r.sys.Openat(r.dir, ".", dirFlags, noMode)
	if err != nil {
		return nil, memberUnopenable(err)
	}
	for _, part := range parts {
		next, err := r.sys.Openat(dir, part, dirFlags, noMode)
		closeReadOnly(dir)
		if err != nil {
			return nil, memberUnopenable(err)
		}
		dir = next
	}
	return dir, nil
}

func memberUnopenable(err error) *Error {
	return fail(ReasonMemberUnopenable, "pack member could not be opened", err)
}

// checkRegular checks that f is a regular file with one link.
func checkRegular(f *os.File) error {
	var st unix.Stat_t
	if err := unix.Fstat(int(f.Fd()), &st); err != nil {
		return fail(ReasonUninspectable, "pack member could not be inspected", err)
	}
	if st.Mode&unix.S_IFMT != unix.S_IFREG || st.Nlink > 1 {
		return fail(ReasonNotSingleRegular, "pack member is not a singly-linked regular file", nil)
	}
	return nil
}

// ReadMember reads the member at the canonical path rel, as OpenMember opens
// it. A member with more than maxBytes bytes fails with ReasonByteBudget.
func (r *Root) ReadMember(rel string, maxBytes int) ([]byte, error) {
	f, err := r.OpenMember(rel)
	if err != nil {
		return nil, err
	}
	defer closeReadOnly(f)
	data, err := io.ReadAll(io.LimitReader(f, int64(maxBytes)+1))
	if err != nil {
		return nil, fail(ReasonUnreadable, "pack member could not be read", err)
	}
	if len(data) > maxBytes {
		return nil, fail(ReasonByteBudget, "pack metadata exceeds the validation limit", nil)
	}
	return data, nil
}
