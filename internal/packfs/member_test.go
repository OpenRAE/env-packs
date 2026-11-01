package packfs

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestOpenMember(t *testing.T) {
	dir := tree(t, entry{kind: "file", path: "a/b/c.txt", target: "content"})
	r := openRoot(t, dir)
	f, err := r.OpenMember("a/b/c.txt")
	if err != nil {
		t.Fatalf("OpenMember() error = %v", err)
	}
	data, err := io.ReadAll(f)
	if closeErr := f.Close(); closeErr != nil {
		t.Errorf("close the member: %v", closeErr)
	}
	if err != nil || string(data) != "content" || f.Name() != filepath.Join(dir, "a", "b", "c.txt") {
		t.Errorf("OpenMember() read %q, %v from %q; want the content of a/b/c.txt", data, err, f.Name())
	}
}

func TestOpenMemberRejections(t *testing.T) {
	r := openRoot(t, tree(t,
		entry{kind: "file", path: "real/file", target: "x"},
		entry{kind: "symlink", path: "linkdir", target: "real"},
		entry{kind: "symlink", path: "link", target: "real/file"},
		entry{kind: "file", path: "a"},
		entry{kind: "hardlink", path: "b", target: "a"},
		entry{kind: "fifo", path: "pipe"},
	))
	tests := []struct {
		rel  string
		want Reason
	}{
		{rel: "linkdir/file", want: ReasonMemberUnopenable},
		{rel: "link", want: ReasonMemberUnopenable},
		{rel: "missing", want: ReasonMemberUnopenable},
		{rel: "real/missing", want: ReasonMemberUnopenable},
		{rel: "b", want: ReasonNotSingleRegular},
		{rel: "pipe", want: ReasonNotSingleRegular},
		{rel: "real", want: ReasonNotSingleRegular},
		{rel: "../a", want: ReasonNameNotCanonical},
		{rel: "/a", want: ReasonPathNotCanonical},
	}
	for _, tt := range tests {
		var f *os.File
		var err error
		noLeak(t, tt.rel, func() { f, err = r.OpenMember(tt.rel) })
		if f != nil {
			t.Errorf("OpenMember(%q) = %v, want nil", tt.rel, f)
		}
		if got := reasonOf(err); got != tt.want {
			t.Errorf("OpenMember(%q) error = %v, want reason %q", tt.rel, err, tt.want)
		}
	}
}

func TestReadMember(t *testing.T) {
	big := strings.Repeat("x", 100_000)
	r := openRoot(t, tree(t,
		entry{kind: "file", path: "small", target: "12345"},
		entry{kind: "file", path: "empty"},
		entry{kind: "file", path: "big", target: big},
	))
	tests := []struct {
		rel      string
		maxBytes int
		want     string
		reason   Reason
	}{
		{rel: "small", maxBytes: 5, want: "12345"},
		{rel: "small", maxBytes: 4, reason: ReasonByteBudget},
		{rel: "empty", maxBytes: 0, want: ""},
		{rel: "big", maxBytes: len(big), want: big},
		{rel: "big", maxBytes: len(big) - 1, reason: ReasonByteBudget},
		{rel: "missing", maxBytes: 10, reason: ReasonMemberUnopenable},
	}
	for _, tt := range tests {
		got, err := r.ReadMember(tt.rel, tt.maxBytes)
		if tt.reason != "" {
			if got != nil || reasonOf(err) != tt.reason {
				t.Errorf("ReadMember(%q, %d) = %d bytes, %v; want reason %q", tt.rel, tt.maxBytes, len(got), err, tt.reason)
			}
			continue
		}
		if err != nil || string(got) != tt.want {
			t.Errorf("ReadMember(%q, %d) = %d bytes, %v; want %d bytes", tt.rel, tt.maxBytes, len(got), err, len(tt.want))
		}
	}
}
