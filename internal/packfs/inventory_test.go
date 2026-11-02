package packfs

import (
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestInventory(t *testing.T) {
	dir := tree(t,
		entry{kind: "file", path: "b.txt"},
		entry{kind: "file", path: "B.md"},
		entry{kind: "file", path: "a/z.txt"},
		entry{kind: "file", path: "a/y/x.txt"},
		entry{kind: "file", path: "c/skip.txt"},
		entry{kind: "symlink", path: "excluded/link", target: "x"},
		entry{kind: "dir", path: "empty"},
	)
	r := openRoot(t, dir)
	opts := InventoryOptions{MaxMembers: 100, Exclude: []string{"c/skip.txt"}, ExcludeDirs: []string{"excluded"}}
	want := []string{"B.md", "a/y/x.txt", "a/z.txt", "b.txt"}
	for range 2 {
		got, err := r.Inventory(opts)
		if err != nil {
			t.Fatalf("Inventory() error = %v", err)
		}
		if diff := cmp.Diff(want, got); diff != "" {
			t.Errorf("Inventory() mismatch (-want +got):\n%s", diff)
		}
	}
}

func TestInventoryRejections(t *testing.T) {
	tests := []struct {
		name    string
		entries []entry
		opts    InventoryOptions
		want    Reason
	}{
		{name: "symlink", entries: []entry{{kind: "symlink", path: "docs/link", target: "../pack.yaml"}}, want: ReasonSymlink},
		{
			name:    "excluded symlink",
			entries: []entry{{kind: "symlink", path: "link", target: "x"}},
			opts:    InventoryOptions{Exclude: []string{"link"}},
			want:    ReasonSymlink,
		},
		{
			name:    "hardlink",
			entries: []entry{{kind: "file", path: "a"}, {kind: "hardlink", path: "b", target: "a"}},
			want:    ReasonHardlink,
		},
		{
			name:    "excluded hardlink",
			entries: []entry{{kind: "file", path: "a"}, {kind: "hardlink", path: "b", target: "a"}},
			opts:    InventoryOptions{Exclude: []string{"a", "b"}},
			want:    ReasonHardlink,
		},
		{name: "fifo", entries: []entry{{kind: "fifo", path: "pipe"}}, want: ReasonSpecialFile},
		{name: "name not NFC", entries: []entry{{kind: "file", path: "café"}}, want: ReasonNameNotCanonical},
		{name: "name not UTF-8", entries: []entry{{kind: "file", path: "a\xff"}}, want: ReasonNameNotUTF8},
		{name: "name with a backslash", entries: []entry{{kind: "file", path: `a\b`}}, want: ReasonNameNotCanonical},
		{name: "case collision", entries: []entry{{kind: "file", path: "A"}, {kind: "file", path: "a"}}, want: ReasonCaseCollision},
		{
			name:    "case collision across directories",
			entries: []entry{{kind: "file", path: "Docs/x"}, {kind: "file", path: "docs/x"}},
			want:    ReasonCaseCollision,
		},
		{name: "full case folding", entries: []entry{{kind: "file", path: "straße"}, {kind: "file", path: "strasse"}}, want: ReasonCaseCollision},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			dir := tree(t, tt.entries...)
			if tt.want == ReasonCaseCollision && regularFiles(t, dir) < len(tt.entries) {
				t.Skip("the file system holds one file for names that differ only in case")
			}
			r := openRoot(t, dir)
			if tt.opts.MaxMembers == 0 {
				tt.opts.MaxMembers = 100
			}
			got, err := r.Inventory(tt.opts)
			if got != nil {
				t.Errorf("Inventory() = %q, want nil", got)
			}
			wantReason(t, err, tt.want)
		})
	}
}

func TestInventoryMemberBudget(t *testing.T) {
	var entries []entry
	for i := range 4 {
		entries = append(entries, entry{kind: "file", path: "d/f" + strconv.Itoa(i)})
	}
	r := openRoot(t, tree(t, entries...))
	// The tree has 5 entries: the directory d and its 4 files.
	if _, err := r.Inventory(InventoryOptions{MaxMembers: 5}); err != nil {
		t.Errorf("Inventory() with the exact budget: error = %v", err)
	}
	_, err := r.Inventory(InventoryOptions{MaxMembers: 4})
	wantReason(t, err, ReasonMemberBudget)
}

func TestInventoryInaccessibleDirectories(t *testing.T) {
	dir := tree(t, entry{kind: "file", path: "locked/x"}, entry{kind: "file", path: "listonly/y"})
	r := openRoot(t, dir)
	for path, mode := range map[string]os.FileMode{"locked": 0o000, "listonly": 0o400} {
		if err := os.Chmod(filepath.Join(dir, path), mode); err != nil {
			t.Fatalf("chmod %s: %v", path, err)
		}
	}
	t.Cleanup(func() {
		for _, path := range []string{"locked", "listonly"} {
			//nolint:gosec // G302 false positive: the path is a directory, and 0700 is within the 0750 limit of G301 for directories.
			if err := os.Chmod(filepath.Join(dir, path), 0o700); err != nil {
				t.Errorf("restore %s: %v", path, err)
			}
		}
	})
	_, err := r.Inventory(InventoryOptions{MaxMembers: 100, ExcludeDirs: []string{"locked"}})
	wantReason(t, err, ReasonUninspectable)
	_, err = r.Inventory(InventoryOptions{MaxMembers: 100, ExcludeDirs: []string{"listonly"}})
	wantReason(t, err, ReasonDirectoryUnopenable)
}

// regularFiles returns the number of regular files below dir.
func regularFiles(t *testing.T, dir string) int {
	t.Helper()
	n := 0
	err := filepath.WalkDir(dir, func(_ string, d fs.DirEntry, err error) error {
		if err == nil && d.Type().IsRegular() {
			n++
		}
		return err
	})
	if err != nil {
		t.Fatalf("count the files of %s: %v", dir, err)
	}
	return n
}
