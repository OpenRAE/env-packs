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
		switch spec[0] % 4 {
		case 0:
			_ = os.WriteFile(path, nil, 0o600) //nolint:errcheck // A member that the system cannot make is not part of the tree.
		case 1:
			_ = os.Mkdir(path, 0o750) //nolint:errcheck // A member that the system cannot make is not part of the tree.
		case 2:
			_ = os.Symlink("target", path) //nolint:errcheck // A member that the system cannot make is not part of the tree.
		default:
			_ = unix.Mkfifo(path, 0o600) //nolint:errcheck // A member that the system cannot make is not part of the tree.
		}
	}
	return root
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
