package diagnostic

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"regexp"
	"slices"
	"strings"
	"testing"
)

func TestNew(t *testing.T) {
	d := New("pack.missing", "docs/pack.yaml", "$.pack.name")
	if d.Code() != "pack.missing" || d.File() != "docs/pack.yaml" || d.Field() != "$.pack.name" {
		t.Errorf("New() = %q, %q, %q; want the code, the file, and the field", d.Code(), d.File(), d.Field())
	}
	if d := New("pack.missing", "", ""); d.File() != "" {
		t.Errorf("New() without a file = %q, want no file", d.File())
	}
	for _, file := range []string{"a", "C:", "a:b"} {
		if d := New("pack.missing", file, ""); d.File() != file {
			t.Errorf("New() with relative file %q = %q, want unchanged", file, d.File())
		}
	}
}

// TestNewFile checks that no absolute or escaping path can enter a
// diagnostic, and that the panic does not show the path.
// Regression test for #617.
func TestNewFile(t *testing.T) {
	for _, file := range []string{"/etc/passwd", "../secret", "a/../b", "a/", "./a", ".", "a//b", `C:\Users\private.txt`, "C:/Users/private.txt", "C:/", `\\server\private.txt`, `docs\pack.yaml`} {
		func() {
			defer func() {
				message := fmt.Sprint(recover())
				if message == "<nil>" || strings.Contains(message, file) {
					t.Errorf("New() with file %q panicked with %q, want a panic without the file", file, message)
				}
			}()
			New("pack.missing", file, "")
		}()
	}
}

func TestLocation(t *testing.T) {
	tests := []struct {
		file, field, want string
	}{
		{file: "pack.yaml", field: "$.name", want: "pack.yaml:$.name"},
		{file: "pack.yaml", want: "pack.yaml"},
		{field: "$.name", want: "$.name"},
		{},
	}
	for _, tt := range tests {
		if got := New("code", tt.file, tt.field).Location(); got != tt.want {
			t.Errorf("Location() of %q and %q = %q, want %q", tt.file, tt.field, got, tt.want)
		}
	}
}

func TestPresentation(t *testing.T) {
	missing := Presentation{
		Severity:    "error",
		Domain:      "pack",
		Owner:       "env-packs",
		Explanation: "pack.yaml is missing from the pack root.",
		Reason:      "Every pack must declare its identity in pack.yaml.",
		Suggestion:  "Add a pack.yaml at the top of the pack directory (see the template).",
		Doc:         "docs/public/checking.md#pack-layout",
	}
	c := NewCatalog()
	family := c.Presentation(New("pack", "", ""))
	tests := []struct {
		code string
		want Presentation
	}{
		{code: "pack.missing", want: missing},
		{code: "pack.missing.more", want: missing},
		{code: "pack.other", want: family},
		{code: "unknown.code", want: c.generic},
		{code: "", want: c.generic},
	}
	for _, tt := range tests {
		if got := c.Presentation(New(tt.code, "", "")); got != tt.want {
			t.Errorf("Presentation() of %q = %+v, want %+v", tt.code, got, tt.want)
		}
	}
}

// TestPresentationsMatchPython checks the presentation of each code in
// testdata/presentations.json. The Python code made the file with
// check.presentation_for, so it holds the text of each catalog entry.
func TestPresentationsMatchPython(t *testing.T) {
	data, err := os.ReadFile("testdata/presentations.json")
	if err != nil {
		t.Fatalf("read the presentations: %v", err)
	}
	var rows []struct {
		Code        string `json:"code"`
		Severity    string `json:"severity"`
		Domain      string `json:"domain"`
		Owner       string `json:"owner"`
		Explanation string `json:"explanation"`
		Reason      string `json:"reason"`
		Suggestion  string `json:"suggestion"`
		Doc         string `json:"doc"`
	}
	if err := json.Unmarshal(data, &rows); err != nil {
		t.Fatalf("decode the presentations: %v", err)
	}
	c := NewCatalog()
	for _, r := range rows {
		want := Presentation{
			Severity: r.Severity, Domain: r.Domain, Owner: r.Owner, Explanation: r.Explanation,
			Reason: r.Reason, Suggestion: r.Suggestion, Doc: r.Doc,
		}
		if got := c.Presentation(New(r.Code, "", "")); got != want {
			t.Errorf("Presentation() of %q = %+v, want %+v", r.Code, got, want)
		}
	}
}

func TestNewCatalog(t *testing.T) {
	if c := NewCatalog(); len(c.families) != 65 || len(c.hints) != 13 {
		t.Errorf("NewCatalog() has %d families and %d hints, want 65 and 13", len(c.families), len(c.hints))
	}
}

func TestNewCatalogPanicsOnABadCatalog(t *testing.T) {
	saved := catalogJSON
	t.Cleanup(func() { catalogJSON = saved })
	catalogJSON = []byte("{")
	defer func() {
		if recover() == nil {
			t.Error("NewCatalog() with a bad catalog did not panic")
		}
	}()
	NewCatalog()
}

func TestParseCatalogErrors(t *testing.T) {
	const domains = `"domains": {"pack": {"owner": "env-packs", "anchor": "pack-layout"}}`
	tests := []struct {
		name string
		data string
		want error
	}{
		{name: "syntax", data: `{`, want: errDecode},
		{name: "unknown field", data: `{` + domains + `, "generic": {"domain": "pack"}, "extra": 1}`, want: errDecode},
		{name: "generic domain", data: `{` + domains + `, "generic": {"domain": "none"}}`, want: errUnknownDomain},
		{name: "family domain", data: `{` + domains + `, "generic": {"domain": "pack"}, "families": {"x": {"domain": "none"}}}`, want: errUnknownDomain},
	}
	for _, tt := range tests {
		c, err := parseCatalog([]byte(tt.data))
		if c != nil || !errors.Is(err, tt.want) {
			t.Errorf("parseCatalog() with a bad %s = %v, %v; want error %v", tt.name, c, err, tt.want)
		}
	}
}

func TestPresentationDomains(t *testing.T) {
	tests := map[string][3]string{
		"pack.missing":            {"pack", "env-packs", "docs/public/checking.md#pack-layout"},
		"provenance.missing":      {"trust", "env-packs", "docs/public/checking.md#trust-and-provenance"},
		"compatibility.type":      {"compatibility", "env-packs", "docs/public/checking.md#compatibility"},
		"sdl.missing":             {"sdl", "raes", "docs/public/checking.md#sdl-and-raes"},
		"provenance.schema.extra": {"trust", "env-packs", "docs/public/checking.md#trust-and-provenance"},
	}
	c := NewCatalog()
	for code, want := range tests {
		p := c.Presentation(New(code, "", ""))
		if got := [3]string{p.Domain, p.Owner, p.Doc}; got != want {
			t.Errorf("Presentation() of %q = %q, want %q", code, got, want)
		}
	}
}

func TestPresentationSchemaHint(t *testing.T) {
	c := NewCatalog()
	base := c.Presentation(New("provenance.schema", "", "")).Suggestion
	tests := map[string]string{
		"provenance.schema.required":     base + " A required field is missing — add it.",
		"provenance.schema.ref":          base + " An internal schema reference did not resolve — please report this upstream.",
		"provenance.schema.min-length":   base + " The text is too short — make it longer.",
		"provenance.schema.max-length":   base + " The text is too long — make it shorter.",
		"provenance.schema.minimum":      base + " The number is less than the minimum — use a larger number.",
		"provenance.schema.unique-items": base + " The list has an entry more than once — remove the repeated entries.",
		"provenance.schema.format":       base + " The value does not have the format that the schema requires — correct it.",
		"provenance.schema.schema":       base,
	}
	for code, want := range tests {
		if got := c.Presentation(New(code, "", "")).Suggestion; got != want {
			t.Errorf("Presentation() of %q has suggestion %q, want %q", code, got, want)
		}
	}
}

// headingAnchor matches a Markdown heading and gives its text.
var headingAnchor = regexp.MustCompile(`(?m)^#{1,6}\s+(.*?)\s*$`)

// TestDocAnchors checks that each documentation target of the catalog is a
// heading of the documentation page, so that a moved heading fails the test.
func TestDocAnchors(t *testing.T) {
	data, err := os.ReadFile("../../" + DocPage)
	if err != nil {
		t.Fatalf("read the documentation page: %v", err)
	}
	var anchors []string
	notAnchor := regexp.MustCompile(`[^a-z0-9 -]`)
	for _, m := range headingAnchor.FindAllStringSubmatch(string(data), -1) {
		anchors = append(anchors, strings.ReplaceAll(notAnchor.ReplaceAllString(strings.ToLower(m[1]), ""), " ", "-"))
	}
	c := NewCatalog()
	targets := []string{c.generic.Doc}
	for _, p := range c.families {
		targets = append(targets, p.Doc)
	}
	for _, target := range targets {
		page, anchor, _ := strings.Cut(target, "#")
		if page != DocPage || !slices.Contains(anchors, anchor) {
			t.Errorf("the documentation target %q is not a heading of %s", target, DocPage)
		}
	}
}

func TestList(t *testing.T) {
	l := NewList(4, 12)
	l.Add("a.b", "pack.yaml", "")
	l.Add("a.b.c", "pack.yaml", "")
	l.Add("a.b", "pack.yaml", "")
	l.Add("a", "", "$.field")
	l.Add("z", "", "")
	got := l.Diagnostics()
	// "." sorts before ":", as in the Python results.
	want := []Diagnostic{New("a.b.c", "pack.yaml", ""), New("a.b", "pack.yaml", ""), New("a", "", "$.field")}
	if !slices.Equal(got, want) {
		t.Errorf("Diagnostics() = %v, want %v", got, want)
	}
}

func TestListCuts(t *testing.T) {
	l := NewList(10, 5)
	l.Add("c", "ééééééé", "fffffff")
	l.Add("c", "ééééééx", "")
	l.Add("c", "abc", "d")
	l.Add("d", "abcde", "x")
	got := l.Diagnostics()
	// The messages are "c: ab", "c: éé" twice, and "d: ab". The second
	// message "c: éé" repeats the first, so the list drops it.
	want := []Diagnostic{
		{code: "c", file: "abc", field: "d"},
		{code: "c", file: "ééééé", field: "fffff"},
		{code: "d", file: "abcde", field: "x"},
	}
	if !slices.Equal(got, want) {
		t.Errorf("Diagnostics() = %v, want %v", got, want)
	}
}

func TestListEmpty(t *testing.T) {
	if got := NewList(1, 1).Diagnostics(); got == nil || len(got) != 0 {
		t.Errorf("Diagnostics() of an empty list = %#v, want an empty slice", got)
	}
}

func TestListFullStillChecksTheFile(t *testing.T) {
	l := NewList(0, 10)
	defer func() {
		if recover() == nil {
			t.Error("Add() of an absolute file to a full list did not panic")
		}
	}()
	l.Add("c", "/abs", "")
}
