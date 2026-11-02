package packfs

import (
	"bytes"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"golang.org/x/sys/unix"
)

// inventoryReasons are the reasons of a failed inventory of a fuzz tree.
var inventoryReasons = []Reason{
	ReasonSymlink, ReasonSpecialFile, ReasonHardlink, ReasonNameNotCanonical,
	ReasonNameNotUTF8, ReasonCaseCollision, ReasonMemberBudget,
}

// FuzzInventory builds a tree from the input and checks that the inventory
// either lists canonical paths of regular files once each, or fails with an
// inventory reason.
//
// The input is a list of members, separated by NUL bytes. The first byte of
// a member selects a file, a directory, a symlink, or a FIFO, and the other
// bytes are its path.
func FuzzInventory(f *testing.F) {
	f.Add([]byte("fa\x00db\x00fb/c\x00"))
	f.Add([]byte("fA\x00fa\x00"))
	f.Add([]byte("lx\x00"))
	f.Add([]byte("pq\x00"))
	f.Add([]byte("fa\x00hb\x00"))
	f.Add([]byte("px\x00fx"))
	f.Add([]byte("f" + strings.Repeat("d/", 65) + "file\x00"))
	f.Add([]byte("fcafé\x00"))
	f.Fuzz(func(t *testing.T, data []byte) {
		root := fuzzTree(t, data)
		r := openRoot(t, root)
		got, err := r.Inventory(InventoryOptions{MaxMembers: 64})
		if err != nil {
			if !slices.Contains(inventoryReasons, reasonOf(err)) {
				t.Fatalf("Inventory() error = %v, want an inventory reason", err)
			}
			return
		}
		checkListing(t, root, got)
	})
}

// fuzzTree builds the tree of a fuzz input in a new directory. It ignores a
// member that the system cannot make or that is outside the directory.
func fuzzTree(t *testing.T, data []byte) string {
	t.Helper()
	root := t.TempDir()
	for i, spec := range bytes.Split(data, []byte{0}) {
		if i == 16 {
			break
		}
		name := string(spec[min(1, len(spec)):])
		path := filepath.Join(root, name)
		if len(spec) < 2 || !strings.HasPrefix(path, root+string(filepath.Separator)) ||
			os.MkdirAll(filepath.Dir(path), 0o750) != nil {
			continue
		}
		switch spec[0] {
		case 'f':
			// O_EXCL never opens an existing member, such as a FIFO, which
			// would block the open for writing.
			//nolint:gosec // G304 false positive: the path stays inside the test directory, as checked above.
			if f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600); err == nil {
				if err := f.Close(); err != nil {
					t.Fatalf("close %s: %v", name, err)
				}
			}
		case 'd':
			_ = os.Mkdir(path, 0o750) //nolint:errcheck // A member that the system cannot make is not part of the tree.
		case 'l':
			_ = os.Symlink("target", path) //nolint:errcheck // A member that the system cannot make is not part of the tree.
		case 'p':
			_ = unix.Mkfifo(path, 0o600) //nolint:errcheck // A member that the system cannot make is not part of the tree.
		case 'h':
			_ = os.Link(filepath.Join(root, "a"), path) //nolint:errcheck // A missing link source is not part of the tree.
		}
	}
	return root
}

// FuzzReadMember checks byte budgets against the exact content of a member.
func FuzzReadMember(f *testing.F) {
	f.Add([]byte("content"), uint16(7))
	f.Add([]byte("content"), uint16(6))
	f.Add([]byte{}, uint16(0))
	f.Fuzz(func(t *testing.T, data []byte, budget uint16) {
		if len(data) > 4096 {
			t.Skip("keep filesystem fuzz inputs bounded")
		}
		root := t.TempDir()
		if err := os.WriteFile(filepath.Join(root, "member"), data, 0o600); err != nil {
			t.Fatal(err)
		}
		r := openRoot(t, root)
		got, err := r.ReadMember("member", int(budget))
		if len(data) > int(budget) {
			if got != nil || reasonOf(err) != ReasonByteBudget {
				t.Fatalf("ReadMember() = %q, %v; want byte-budget refusal", got, err)
			}
		} else if err != nil || !bytes.Equal(got, data) {
			t.Fatalf("ReadMember() = %q, %v; want %q", got, err, data)
		}
	})
}

// checkListing checks that each path of an inventory of root is canonical,
// is a regular file, and occurs once.
func checkListing(t *testing.T, root string, listing []string) {
	t.Helper()
	seen := make(map[string]bool)
	for _, rel := range listing {
		info, statErr := os.Lstat(filepath.Join(root, rel))
		if _, err := NormalizeRelpath(rel); err != nil || seen[rel] || statErr != nil || !info.Mode().IsRegular() {
			t.Fatalf("Inventory() listed %q: canonical error %v, seen %v, stat %v", rel, err, seen[rel], statErr)
		}
		seen[rel] = true
	}
}
