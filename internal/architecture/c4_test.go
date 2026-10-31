package architecture

import (
	"flag"
	"os"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

var update = flag.Bool("update", false, "rewrite the golden files in testdata")

const goldenDSL = "testdata/workspace.golden.dsl"

func TestRenderDSL(t *testing.T) {
	m := validModel()
	m.ExternalSystems[0].Description = `An "external" system with a \ backslash.`
	got := RenderDSL(m)
	if *update {
		if err := os.WriteFile(goldenDSL, got, 0o600); err != nil {
			t.Fatalf("write golden file: %v", err)
		}
	}
	want, err := os.ReadFile(goldenDSL)
	if err != nil {
		t.Fatalf("read golden file: %v", err)
	}
	if diff := cmp.Diff(string(want), string(got)); diff != "" {
		t.Errorf("RenderDSL() mismatch (-want +got):\n%s", diff)
	}
}

func TestRenderDSLWithoutRelationships(t *testing.T) {
	m := &Model{
		System:     Element{ID: "system", Name: "System", Description: "The system."},
		Containers: []Container{{ID: "app", Name: "App", Technology: "Go", Description: "The app."}},
	}
	want := `workspace "System" "The system." {
    !identifiers hierarchical

    model {
        system = softwareSystem "System" "The system." {
            app = container "App" "The app." "Go"
        }
    }

    views {
        systemContext system "context" {
            include *
            autoLayout lr
        }
        container system "containers" {
            include *
            autoLayout lr
        }
    }
}
`
	if diff := cmp.Diff(want, string(RenderDSL(m))); diff != "" {
		t.Errorf("RenderDSL() mismatch (-want +got):\n%s", diff)
	}
}

func TestRenderDSLDependenciesOnly(t *testing.T) {
	m := &Model{
		System:     Element{ID: "system", Name: "System", Description: "The system."},
		Containers: []Container{{ID: "app", Name: "App", Technology: "Go", Description: "The app."}},
		Components: []Component{
			{ID: "a", Container: "app", Description: "A.", DependsOn: []string{"b", "missing"}},
			{ID: "b", Container: "app", Description: "B."},
		},
	}
	got := string(RenderDSL(m))
	want := "        }\n\n        system.app.a -> system.app.b \"Depends on\"\n    }\n"
	if !strings.Contains(got, want) {
		t.Errorf("RenderDSL() = %q, want it to contain %q", got, want)
	}
	if strings.Contains(got, "missing") {
		t.Errorf("RenderDSL() = %q, want no relationship to the unknown component", got)
	}
}
