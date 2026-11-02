package issueskeleton

import (
	"embed"
	"errors"
	"io/fs"
	"maps"
	"os"
	"slices"
	"strings"
	"testing"
	"testing/fstest"
)

// testPlan is the plan of the tests of the Python code.
func testPlan() Plan {
	return Plan{
		PackID: "example-pack", Title: "Example Pack", Focus: "A focused example scenario.",
		Sources: []string{"Source: https://example.invalid/source"}, Labels: []string{"scenario:example-pack"},
		PackRoot: "environments", MilestoneNumber: new(42),
	}
}

// loadTestTemplates loads the embedded templates for a test.
func loadTestTemplates(t *testing.T) *Templates {
	t.Helper()
	return NewTemplates()
}

func TestNewTemplatesPanicsOnBadTemplates(t *testing.T) {
	saved := templateFS
	t.Cleanup(func() { templateFS = saved })
	templateFS = embed.FS{}
	defer func() {
		if recover() == nil {
			t.Error("NewTemplates() without templates did not panic")
		}
	}()
	NewTemplates()
}

func TestNewTemplates(t *testing.T) {
	var keys []string
	for _, it := range loadTestTemplates(t).Issues {
		keys = append(keys, it.Key)
	}
	want := []string{"contract", "topology", "behavior", "flags", "profiles", "build", "rehearsal", "manual", "final"}
	if !slices.Equal(keys, want) {
		t.Errorf("NewTemplates() keys = %v, want %v", keys, want)
	}
}

// TestBody checks a body against testdata/contract.golden, which the Python
// code rendered for the same plan.
func TestBody(t *testing.T) {
	want, err := os.ReadFile("testdata/contract.golden")
	if err != nil {
		t.Fatalf("read the golden body: %v", err)
	}
	got, err := loadTestTemplates(t).Body(testPlan(), "contract")
	if err != nil || got != string(want) {
		t.Errorf("Body() = %q, %v; want %q", got, err, want)
	}
}

func TestBodyNoSources(t *testing.T) {
	plan := testPlan()
	plan.Sources = nil
	got, err := loadTestTemplates(t).Body(plan, "contract")
	if err != nil || !strings.Contains(got, "\n- Source log TBD by the pack-design agent.\n") {
		t.Errorf("Body() without sources = %q, %v; want the TBD source log", got, err)
	}
	plan.Sources = []string{"one", "two"}
	if got, err = loadTestTemplates(t).Body(plan, "contract"); err != nil || !strings.Contains(got, "\n- one\n- two\n") {
		t.Errorf("Body() with two sources = %q, %v; want both entries", got, err)
	}
}

func TestBodyUnknownTemplate(t *testing.T) {
	if got, err := loadTestTemplates(t).Body(testPlan(), "missing"); err == nil {
		t.Errorf("Body() of an unknown template = %q, want an error", got)
	}
}

func TestLoadTemplatesErrors(t *testing.T) {
	good := fstest.MapFS{
		"templates/issues.json":        {Data: []byte(`[{"key": "a"}]`)},
		"templates/common-anchors.txt": {Data: []byte("anchors")},
		"templates/a.txt":              {Data: []byte("{{.PackID}}")},
	}
	if _, err := loadTemplates(good); err != nil {
		t.Fatalf("loadTemplates() of a good tree error = %v", err)
	}
	fsys := fstest.MapFS{}
	maps.Copy(fsys, good)
	delete(fsys, "templates/issues.json")
	if _, err := loadTemplates(fsys); !errors.Is(err, fs.ErrNotExist) {
		t.Errorf("loadTemplates() without the list error = %v, want %v", err, fs.ErrNotExist)
	}
	tests := map[string]func(fstest.MapFS){
		"no list":      func(m fstest.MapFS) { delete(m, "templates/issues.json") },
		"bad list":     func(m fstest.MapFS) { m["templates/issues.json"] = &fstest.MapFile{Data: []byte("{")} },
		"no anchors":   func(m fstest.MapFS) { delete(m, "templates/common-anchors.txt") },
		"bad template": func(m fstest.MapFS) { m["templates/a.txt"] = &fstest.MapFile{Data: []byte("{{")} },
	}
	for name, change := range tests {
		fsys := fstest.MapFS{}
		maps.Copy(fsys, good)
		change(fsys)
		if tmpl, err := loadTemplates(fsys); tmpl != nil || err == nil {
			t.Errorf("loadTemplates() with %s = %v, %v; want an error", name, tmpl, err)
		}
	}
}

// TestClean checks clean against the results of clean in the Python code.
func TestClean(t *testing.T) {
	tests := map[string]string{
		"":                         "\n",
		"  a\n    b\n":             "a\n  b\n",
		"\tx\n\ty":                 "x\ny\n",
		"  a\n\tb":                 "a\n\tb\n",
		"    deep\n      deeper\n": "deep\n  deeper\n",
		" \n  a\n \t\n  b":         "a\n\nb\n",
		"a\rb\r\nc\u2028d\x1ce":    "a\nb\nc\nd\ne\n",
		"  lead\x1c":               "lead\n",
		"x\n\n\ny\n":               "x\n\n\ny\n",
		"    a\n  b":               "a\nb\n",
		"\tA\n\tB\n C":             "A\n\tB\n C\n",
		"x\x1f":                    "x\n",
		"x\x01":                    "x\x01\n",
		" \ta\n  b":                "a\n b\n",
		"  x\n   y\n  z":           "x\n y\nz\n",
	}
	for body, want := range tests {
		if got := clean(body); got != want {
			t.Errorf("clean(%q) = %q, want %q", body, got, want)
		}
	}
}
