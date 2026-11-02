package packfs

import (
	"slices"
	"strings"
	"testing"
	"unicode/utf8"

	"golang.org/x/text/unicode/norm"
)

func TestNormalizeRelpath(t *testing.T) {
	tests := []struct {
		rel  string
		want Reason
	}{
		{rel: "a"},
		{rel: "a/b.txt"},
		{rel: "docs/caf\u00e9.md"},
		{rel: "", want: ReasonPathNotCanonical},
		{rel: "/a", want: ReasonPathNotCanonical},
		{rel: `a\b`, want: ReasonPathNotCanonical},
		{rel: "a//b", want: ReasonNameNotCanonical},
		{rel: "a/", want: ReasonNameNotCanonical},
		{rel: "./a", want: ReasonNameNotCanonical},
		{rel: "a/..", want: ReasonNameNotCanonical},
		{rel: "../a", want: ReasonNameNotCanonical},
		{rel: "docs/cafe\u0301.md", want: ReasonNameNotCanonical},
		{rel: "a\xff", want: ReasonNameNotUTF8},
		{rel: "\xff\u0301", want: ReasonNameNotUTF8},
		{rel: "e\u0301\xff", want: ReasonNameNotCanonical},
	}
	for _, tt := range tests {
		got, err := NormalizeRelpath(tt.rel)
		if tt.want == "" {
			if err != nil || got != tt.rel {
				t.Errorf("NormalizeRelpath(%q) = %q, %v, want %q, nil", tt.rel, got, err, tt.rel)
			}
			continue
		}
		if got != "" || reasonOf(err) != tt.want {
			t.Errorf("NormalizeRelpath(%q) = %q, %v, want reason %q", tt.rel, got, err, tt.want)
		}
	}
}

func TestErrorMessage(t *testing.T) {
	_, err := NormalizeRelpath("")
	if err == nil || err.Error() != "pack-relative path is not canonical" {
		t.Errorf("NormalizeRelpath(\"\") error = %v, want the message of the Python implementation", err)
	}
}

// FuzzNormalizeRelpath checks that an accepted path is returned unchanged and
// is canonical, and that a rejected path has a path reason.
func FuzzNormalizeRelpath(f *testing.F) {
	for _, seed := range []string{"a", "a/b", "", "/a", "a//b", "../a", "café", "a\xff", `a\b`} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, rel string) {
		got, err := NormalizeRelpath(rel)
		if err != nil {
			if !slices.Contains([]Reason{ReasonPathNotCanonical, ReasonNameNotCanonical, ReasonNameNotUTF8}, reasonOf(err)) {
				t.Fatalf("NormalizeRelpath(%q) error = %v, want a path reason", rel, err)
			}
			return
		}
		if got != rel {
			t.Fatalf("NormalizeRelpath(%q) = %q, want the input", rel, got)
		}
		for part := range strings.SplitSeq(rel, "/") {
			if part == "" || part == "." || part == ".." || strings.Contains(part, `\`) ||
				!utf8.ValidString(part) || !norm.NFC.IsNormalString(part) {
				t.Fatalf("NormalizeRelpath(%q) accepted the component %q", rel, part)
			}
		}
	})
}
