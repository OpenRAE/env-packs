package packfs

import (
	"strings"
	"unicode/utf8"

	"golang.org/x/text/unicode/norm"
)

// NormalizeRelpath checks that rel is a canonical path relative to a pack
// root, and returns it. A canonical path has slash-separated components that
// are valid UTF-8 in NFC, and no component is empty, ".", or "..". It has no
// leading slash and no backslash.
func NormalizeRelpath(rel string) (string, error) {
	if rel == "" || strings.HasPrefix(rel, "/") || strings.Contains(rel, `\`) {
		return "", fail(ReasonPathNotCanonical, "pack-relative path is not canonical", nil)
	}
	for part := range strings.SplitSeq(rel, "/") {
		if err := checkName(part); err != nil {
			return "", err
		}
	}
	return rel, nil
}

// checkName checks that name is one canonical path component. As in the
// Python code, the NFC check comes before the UTF-8 check. The NFC check
// treats each invalid byte as a character without a composition.
func checkName(name string) error {
	if name == "" || name == "." || name == ".." || strings.ContainsAny(name, `/\`) ||
		!norm.NFC.IsNormalString(name) {
		return fail(ReasonNameNotCanonical, "pack member name is not canonical", nil)
	}
	if !utf8.ValidString(name) {
		return fail(ReasonNameNotUTF8, "pack member name is not valid UTF-8", nil)
	}
	return nil
}
