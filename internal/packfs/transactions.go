package packfs

import (
	"errors"
	"os"
	"strings"

	"golang.org/x/sys/unix"
)

// The modes of the files and the directories that WriteMember creates.
const (
	fileMode = 0o600
	dirMode  = 0o755
)

// writeFlags create or truncate a staged file, without following a symlink.
const writeFlags = unix.O_WRONLY | unix.O_CREAT | unix.O_TRUNC | unix.O_NOFOLLOW | unix.O_CLOEXEC

// WriteMember writes content to the file at the canonical path rel below the
// staging root directory. It creates each missing directory with the mode
// 0755 and the file with the mode 0600, through descriptors and without
// following a symlink. It does not copy ownership, access control lists,
// extended attributes, or set-id bits.
func WriteMember(root, rel string, content []byte) error {
	return writeMember(unixSystem{}, root, rel, content)
}

// writeMember writes one staged file with the system calls of sys.
func writeMember(sys system, root, rel string, content []byte) error {
	if _, err := NormalizeRelpath(rel); err != nil {
		return err
	}
	dir, err := os.OpenFile(root, dirFlags, noMode) //nolint:gosec // G304 false positive: the caller chooses the staging root, and each write stays below it.
	if err != nil {
		return writeFailed(err)
	}
	parts := strings.Split(rel, "/")
	for _, part := range parts[:len(parts)-1] {
		next, enterErr := enterDir(sys, dir, part)
		closeReadOnly(dir)
		if enterErr != nil {
			return writeFailed(enterErr)
		}
		dir = next
	}
	defer closeReadOnly(dir)
	f, err := sys.Openat(dir, parts[len(parts)-1], writeFlags, fileMode)
	if err != nil {
		return writeFailed(err)
	}
	// The close of a written file can report a failed write, so it counts.
	if err := errors.Join(f.Chmod(fileMode), write(f, content), f.Close()); err != nil {
		return writeFailed(err)
	}
	return nil
}

// write writes content to f.
func write(f *os.File, content []byte) error {
	_, err := f.Write(content)
	return err
}

// enterDir creates the directory name in the directory dir when it is
// missing, opens it, and sets its mode to 0755.
func enterDir(sys system, dir *os.File, name string) (*os.File, error) {
	if err := unix.Mkdirat(int(dir.Fd()), name, dirMode); err != nil && !errors.Is(err, unix.EEXIST) {
		return nil, err
	}
	next, err := sys.Openat(dir, name, dirFlags, noMode)
	if err != nil {
		return nil, err
	}
	if err := next.Chmod(dirMode); err != nil {
		closeReadOnly(next)
		return nil, err
	}
	return next, nil
}

func writeFailed(err error) *Error {
	return fail(ReasonWriteFailed, "staged member could not be written safely", err)
}

// PublishNew moves the complete staged tree to target in one atomic step.
// The target must not exist.
func PublishNew(staged, target string) error {
	return publishNew(unixSystem{}, staged, target)
}

func publishNew(sys system, staged, target string) error {
	err := sys.Renameat2(staged, target, renameNoReplace)
	switch {
	case err == nil:
		return nil
	case unsupported(err):
		return unsupportedPlatform(err)
	case errors.Is(err, unix.EEXIST):
		return fail(ReasonTargetExists, "transaction target already exists", err)
	}
	return fail(ReasonPublishFailed, "staged tree could not be published", err)
}

// Exchange swaps the complete staged tree and the existing target in one
// atomic step.
func Exchange(staged, target string) error {
	return exchange(unixSystem{}, staged, target)
}

func exchange(sys system, staged, target string) error {
	err := sys.Renameat2(staged, target, renameExchange)
	switch {
	case err == nil:
		return nil
	case unsupported(err):
		return unsupportedPlatform(err)
	}
	return fail(ReasonExchangeFailed, "staged tree could not replace the target", err)
}

// Replace exchanges the staged tree and the target, and then calls check
// with the path of the tree that it replaced, which is now at staged. When
// check fails, Replace exchanges the trees back and returns the error of
// check. When that exchange fails, Replace returns ReasonRecovery, and the
// path of the error keeps the original tree (ADR 0035).
func Replace(staged, target string, check func(previous string) error) error {
	return replace(unixSystem{}, staged, target, check)
}

func replace(sys system, staged, target string, check func(previous string) error) error {
	if err := exchange(sys, staged, target); err != nil {
		return err
	}
	checkErr := check(staged)
	if checkErr == nil {
		return nil
	}
	if err := exchange(sys, staged, target); err != nil {
		return &Error{
			Reason: ReasonRecovery,
			Path:   staged,
			msg:    "the trees could not be exchanged back; the original tree is kept for recovery",
			err:    errors.Join(checkErr, err),
		}
	}
	return checkErr
}

// unsupported reports whether err means that the platform has no renameat2.
func unsupported(err error) bool {
	return errors.Is(err, errUnsupported) || errors.Is(err, unix.ENOSYS)
}

func unsupportedPlatform(err error) *Error {
	return fail(ReasonUnsupportedPlatform,
		"atomic directory transactions are unsupported on this platform: they need the Linux renameat2 system call", err)
}
