package packfs

import (
	"errors"
	"math"
	"os"
	"path/filepath"
	"testing"

	"golang.org/x/sys/unix"
)

// errFault is the default error of a failed call.
var errFault = errors.New("injected fault")

// The ways in which faultSystem fails a call. With failCall, the call returns
// its error. With badFile, Openat returns a file whose descriptor is not open,
// so that each operation on the file fails with EBADF. With writeOnlyFile,
// Openat opens the file for writing only, so that fstat succeeds and a read
// fails with EBADF.
const (
	failCall = iota
	badFile
	writeOnlyFile
)

// badFD is a descriptor number that cannot be open: the kernel limits
// descriptors to values below it.
const badFD = math.MaxInt32

// faultSystem calls the operating system, and fails the call-th call of
// method in the way that mode names.
type faultSystem struct {
	unixSystem

	method string
	call   int
	mode   int
	// err is the error of a failCall fault.
	err   error
	calls map[string]int
}

func newFault(method string, call, mode int) *faultSystem {
	return &faultSystem{method: method, call: call, mode: mode, err: errFault, calls: map[string]int{}}
}

// hit counts a call of method and reports whether it fails.
func (f *faultSystem) hit(method string) bool {
	f.calls[method]++
	return method == f.method && f.calls[method] == f.call
}

func (f *faultSystem) Openat(dir *os.File, path string, flags int, mode uint32) (*os.File, error) {
	if !f.hit("Openat") {
		return f.unixSystem.Openat(dir, path, flags, mode)
	}
	switch f.mode {
	case badFile:
		return os.NewFile(badFD, path), nil
	case writeOnlyFile:
		return f.unixSystem.Openat(dir, path, unix.O_WRONLY|unix.O_NOFOLLOW|unix.O_CLOEXEC, noMode)
	}
	return nil, f.err
}

func (f *faultSystem) Lstatat(dir *os.File, path string) (unix.Stat_t, error) {
	if f.hit("Lstatat") {
		return unix.Stat_t{}, f.err
	}
	return f.unixSystem.Lstatat(dir, path)
}

func (f *faultSystem) Renameat2(oldpath, newpath string, flags uint) error {
	if f.hit("Renameat2") {
		return f.err
	}
	return f.unixSystem.Renameat2(oldpath, newpath, flags)
}

// wantFault reports whether err carries the error of the fault f.
func wantFault(f *faultSystem, err error) bool {
	if f.mode == failCall {
		return errors.Is(err, f.err)
	}
	return wantEBADF(err)
}

// wantEBADF reports whether err carries EBADF, the error of an operation on a
// descriptor that does not allow it.
func wantEBADF(err error) bool {
	return errors.Is(err, unix.EBADF)
}

// openFault opens the pack root dir with the fault system f.
func openFault(t *testing.T, f *faultSystem, dir string) *Root {
	t.Helper()
	r, err := open(f, dir)
	if err != nil {
		t.Fatalf("open(%s) error = %v", dir, err)
	}
	t.Cleanup(func() {
		if err := r.Close(); err != nil {
			t.Errorf("close the root: %v", err)
		}
	})
	return r
}

// openDescriptors returns the number of open descriptors of the process. The
// first call starts the poller of the runtime, which keeps its descriptors.
func openDescriptors(t *testing.T) int {
	t.Helper()
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("start the poller: %v", err)
	}
	if closeErr := errors.Join(r.Close(), w.Close()); closeErr != nil {
		t.Fatalf("close the pipe: %v", closeErr)
	}
	entries, err := os.ReadDir("/dev/fd")
	if err != nil {
		t.Fatalf("list the open descriptors: %v", err)
	}
	return len(entries)
}

// noLeak fails the test when op leaves a descriptor open.
func noLeak(t *testing.T, name string, op func()) {
	t.Helper()
	before := openDescriptors(t)
	op()
	if after := openDescriptors(t); after != before {
		t.Errorf("%s: %d open descriptors after the operation, want %d", name, after, before)
	}
}

func TestInventoryFaults(t *testing.T) {
	dir := tree(t, entry{kind: "file", path: "a"}, entry{kind: "file", path: "d/b"})
	tests := []struct {
		name   string
		method string
		call   int
		mode   int
		want   Reason
	}{
		{name: "open of the root", method: "Openat", call: 1, want: ReasonUntraversable},
		{name: "listing of the root", method: "Openat", call: 1, mode: badFile, want: ReasonUntraversable},
		{name: "open of a directory", method: "Openat", call: 2, want: ReasonDirectoryUnopenable},
		{name: "listing of a directory", method: "Openat", call: 2, mode: badFile, want: ReasonUntraversable},
		{name: "inspection", method: "Lstatat", call: 1, want: ReasonUninspectable},
	}
	for _, tt := range tests {
		f := newFault(tt.method, tt.call, tt.mode)
		r := openFault(t, f, dir)
		noLeak(t, tt.name, func() {
			got, err := r.Inventory(InventoryOptions{MaxMembers: 10})
			if got != nil || !wantFault(f, err) || reasonOf(err) != tt.want {
				t.Errorf("Inventory() with a failed %s = %q, %v; want the fault with reason %q", tt.name, got, err, tt.want)
			}
		})
	}
}

func TestOpenMemberFaults(t *testing.T) {
	dir := tree(t, entry{kind: "file", path: "a/b/c", target: "x"})
	tests := []struct {
		name string
		call int
		mode int
		want Reason
	}{
		{name: "open of the root", call: 1, want: ReasonMemberUnopenable},
		{name: "open of the first directory", call: 2, want: ReasonMemberUnopenable},
		{name: "open of the second directory", call: 3, want: ReasonMemberUnopenable},
		{name: "open of the file", call: 4, want: ReasonMemberUnopenable},
		{name: "inspection of the file", call: 4, mode: badFile, want: ReasonUninspectable},
	}
	for _, tt := range tests {
		f := newFault("Openat", tt.call, tt.mode)
		r := openFault(t, f, dir)
		noLeak(t, tt.name, func() {
			file, err := r.OpenMember("a/b/c")
			if file != nil || !wantFault(f, err) || reasonOf(err) != tt.want {
				t.Errorf("OpenMember() with a failed %s = %v, %v; want the fault with reason %q", tt.name, file, err, tt.want)
			}
		})
	}
}

func TestReadMemberFault(t *testing.T) {
	dir := tree(t, entry{kind: "file", path: "a", target: "content"})
	f := newFault("Openat", 2, writeOnlyFile)
	r := openFault(t, f, dir)
	noLeak(t, "failed read", func() {
		if data, err := r.ReadMember("a", 100); data != nil || reasonOf(err) != ReasonUnreadable || !errors.Is(err, unix.EBADF) {
			t.Errorf("ReadMember() with a failed read = %q, %v; want ReasonUnreadable", data, err)
		}
	})
}

func TestWriteMemberFaults(t *testing.T) {
	tests := []struct {
		name string
		call int
		mode int
	}{
		{name: "open of the directory", call: 1},
		{name: "mode of the directory", call: 1, mode: badFile},
		{name: "open of the file", call: 2},
		{name: "write of the file", call: 2, mode: badFile},
	}
	for _, tt := range tests {
		root := t.TempDir()
		f := newFault("Openat", tt.call, tt.mode)
		noLeak(t, tt.name, func() {
			err := writeMember(f, root, "d/file", []byte("content"))
			if reasonOf(err) != ReasonWriteFailed || !wantFault(f, err) {
				t.Errorf("writeMember() with a failed %s = %v, want ReasonWriteFailed with the fault", tt.name, err)
			}
		})
	}
}

func TestTransactionFaults(t *testing.T) {
	tests := []struct {
		name string
		err  error
		run  func(sys system, staged, target string) error
		want Reason
	}{
		{name: "publish unsupported", err: errUnsupported, run: publishNew, want: ReasonUnsupportedPlatform},
		{name: "publish without the system call", err: unix.ENOSYS, run: publishNew, want: ReasonUnsupportedPlatform},
		{name: "publish exists", err: unix.EEXIST, run: publishNew, want: ReasonTargetExists},
		{name: "publish other", err: unix.EIO, run: publishNew, want: ReasonPublishFailed},
		{name: "exchange unsupported", err: errUnsupported, run: exchange, want: ReasonUnsupportedPlatform},
		{name: "exchange other", err: unix.EIO, run: exchange, want: ReasonExchangeFailed},
	}
	for _, tt := range tests {
		f := newFault("Renameat2", 1, failCall)
		f.err = tt.err
		staged, target := staging(t)
		err := tt.run(f, staged, target)
		if reasonOf(err) != tt.want || !errors.Is(err, tt.err) {
			t.Errorf("%s: error = %v, want reason %q", tt.name, err, tt.want)
		}
	}
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
