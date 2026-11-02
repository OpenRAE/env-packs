package packfs

import (
	"os"
	"path/filepath"
	"testing"
)

func TestOpen(t *testing.T) {
	dir := tree(t, entry{kind: "file", path: "file"}, entry{kind: "symlink", path: "link", target: "."})
	tests := []struct {
		name string
		path string
		want Reason
	}{
		{name: "empty", path: "", want: ReasonRootEmpty},
		{name: "symlink", path: filepath.Join(dir, "link"), want: ReasonRootSymlink},
		{name: "missing", path: filepath.Join(dir, "missing"), want: ReasonRootInaccessible},
		{name: "file", path: filepath.Join(dir, "file"), want: ReasonRootInaccessible},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			r, err := Open(tt.path)
			if r != nil {
				t.Errorf("Open(%q) = %v, want nil", tt.path, r)
			}
			wantReason(t, err, tt.want)
		})
	}
	r := openRoot(t, dir)
	if r.Path() != dir {
		t.Errorf("Root.Path() = %q, want %q", r.Path(), dir)
	}
}

func TestOpenUnreadableRoot(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "locked")
	if err := os.Mkdir(dir, 0o000); err != nil {
		t.Fatalf("make the directory: %v", err)
	}
	_, err := Open(dir)
	wantReason(t, err, ReasonRootInaccessible)
}
