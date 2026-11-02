// Package diagnostic holds the one diagnostic type of the product, its
// presentation catalog, and the list of the diagnostics of one operation
// (design 0006, ADR 0031).
//
// A diagnostic holds a stable code and a safe location, and never a message.
// A [Catalog] gives its presentation, by code.
package diagnostic

import (
	"io/fs"
	"slices"
	"strings"
)

// DocPage is the documentation page of the diagnostics. The documentation
// target of a diagnostic is an anchor of this page.
const DocPage = "docs/public/checking.md"

// A Diagnostic is one problem that an operation found. Its location is a
// pack-relative file and a field pointer into that file, such as
// "$.pack.name". Both are optional.
type Diagnostic struct {
	code  string
	file  string
	field string
}

// New returns a diagnostic with code, file, and field. The file is empty or a
// pack-relative member path that is valid for io/fs: relative,
// slash-separated, and without "." or ".." elements, backslashes, or a drive-root
// path. Any other file is a
// defect, and New panics without the file in the message. So no absolute
// path can enter a diagnostic.
func New(code, file, field string) Diagnostic {
	if file != "" && (file == "." || !fs.ValidPath(file) || strings.Contains(file, `\`) || len(file) > 2 && file[1] == ':' && file[2] == '/') {
		panic("diagnostic: the file is not a pack-relative path")
	}
	return Diagnostic{code: code, file: file, field: field}
}

// Code returns the stable code of d, such as "pack.missing".
func (d Diagnostic) Code() string {
	return d.code
}

// File returns the pack-relative file of d, or "".
func (d Diagnostic) File() string {
	return d.file
}

// Field returns the field pointer of d, or "".
func (d Diagnostic) Field() string {
	return d.field
}

// Location returns "file:field", the file, or the field of d, or "" when d
// has no location.
func (d Diagnostic) Location() string {
	if d.file != "" && d.field != "" {
		return d.file + ":" + d.field
	}
	return d.file + d.field
}

// A List collects the diagnostics of one operation within two limits, as the
// Python code does: at most a number of diagnostics, and at most a number of
// characters in the file, the field, and the message of each one.
type List struct {
	maxItems, maxChars int
	items              []item
}

// An item is a diagnostic in a list, with its message.
type item struct {
	message    string
	diagnostic Diagnostic
}

// NewList returns an empty list that keeps at most maxItems diagnostics and
// at most maxChars characters in each part. The pack checks use 100 and 240.
func NewList(maxItems, maxChars int) *List {
	return &List{maxItems: maxItems, maxChars: maxChars}
}

// Add adds the diagnostic with code, file, and field, as New makes it. When
// the list is full, Add drops it. Add cuts the file and the field to the
// character limit, and it makes the message "code: file:field" within that
// limit.
func (l *List) Add(code, file, field string) {
	d := New(code, file, field)
	if len(l.items) >= l.maxItems {
		return
	}
	d.file, d.field = cut(d.file, l.maxChars), cut(d.field, l.maxChars)
	message := d.code
	if d.file != "" {
		message += ": " + d.file
	}
	if d.field != "" {
		message += ":" + d.field
	}
	l.items = append(l.items, item{message: cut(message, l.maxChars), diagnostic: d})
}

// Diagnostics returns the diagnostics of l, sorted by message. It drops a
// diagnostic with the same message as an earlier one.
func (l *List) Diagnostics() []Diagnostic {
	seen := make(map[string]bool, len(l.items))
	var unique []item
	for _, it := range l.items {
		if !seen[it.message] {
			seen[it.message] = true
			unique = append(unique, it)
		}
	}
	slices.SortFunc(unique, func(a, b item) int {
		return strings.Compare(a.message, b.message)
	})
	diagnostics := make([]Diagnostic, len(unique))
	for i, it := range unique {
		diagnostics[i] = it.diagnostic
	}
	return diagnostics
}

// cut returns the first n characters of s.
func cut(s string, n int) string {
	count := 0
	for i := range s {
		if count == n {
			return s[:i]
		}
		count++
	}
	return s
}
