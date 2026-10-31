package architecture

import (
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestLoadGraph(t *testing.T) {
	got, err := LoadGraph("testdata/fixture")
	if err != nil {
		t.Fatalf("LoadGraph() error = %v", err)
	}
	const fixture = "example.com/fixture"
	want := Graph{
		Module: fixture,
		Packages: []Package{
			{
				Path: fixture + "/a",
				Dir:  "a",
				Files: []File{
					{
						Name: "a/a.go",
						Imports: []Import{
							{Path: "os", Module: "", Line: 5},
							{Path: "example.com/dep", Module: "example.com/dep", Line: 7},
							{Path: fixture + "/b", Module: fixture, Line: 8},
						},
						Symbols: []Symbol{
							{Name: "println", Line: 13},
							{Name: "os.Getenv", Line: 14},
							{Name: fixture + "/b.B", Line: 14},
							{Name: "example.com/dep.Value", Line: 14},
						},
					},
					{
						Name:    "a/a_test.go",
						Test:    true,
						Imports: []Import{{Path: "testing", Module: "", Line: 3}},
					},
					{
						Name: "a/ext_test.go",
						Test: true,
						Imports: []Import{
							{Path: "testing", Module: "", Line: 4},
							{Path: fixture + "/a", Module: fixture, Line: 6},
						},
						Symbols: []Symbol{{Name: fixture + "/a.A", Line: 10}},
					},
				},
			},
			{
				Path:  fixture + "/b",
				Dir:   "b",
				Files: []File{{Name: "b/b.go"}},
			},
			{
				Path:  fixture + "/cmd/tool",
				Dir:   "cmd/tool",
				Main:  true,
				Files: []File{{Name: "cmd/tool/main.go"}},
			},
		},
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("LoadGraph() mismatch (-want +got):\n%s", diff)
	}
}

func TestLoadGraphErrors(t *testing.T) {
	for _, dir := range []string{"testdata/missing", "testdata/broken"} {
		if _, err := LoadGraph(dir); err == nil {
			t.Errorf("LoadGraph(%q) error = nil, want an error", dir)
		}
	}
}
