package architecture

import (
	"flag"
	"os"
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

func TestRenderDSLSmallModels(t *testing.T) {
	system := Element{ID: "system", Name: "System", Description: "The system."}
	app := Container{ID: "app", Name: "App", Technology: "Go", Description: "The app."}
	tests := []struct {
		name  string
		model *Model
		want  string
	}{
		{
			name: "no relationships",
			model: &Model{
				System: system,
				Containers: []Container{
					{ID: "docs", Name: "Docs", Technology: "Markdown", Description: "The docs."},
					app,
				},
				Components: []Component{{ID: "core", Container: "app", Description: "The core."}},
			},
			want: `workspace "System" "The system." {
    !identifiers hierarchical

    model {
        system = softwareSystem "System" "The system." {
            docs = container "Docs" "The docs." "Markdown"
            app = container "App" "The app." "Go" {
                core = component "core" "The core." "Go"
            }
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
        component system.app "components-app" {
            include *
            autoLayout lr
        }
    }
}
`,
		},
		{
			name: "dependencies only",
			model: &Model{
				System:     system,
				Containers: []Container{app},
				Components: []Component{
					{ID: "a", Container: "app", Description: "A.", DependsOn: []string{"missing", "b"}},
					{ID: "b", Container: "app", Description: "B."},
				},
			},
			want: `workspace "System" "The system." {
    !identifiers hierarchical

    model {
        system = softwareSystem "System" "The system." {
            app = container "App" "The app." "Go" {
                a = component "a" "A." "Go"
                b = component "b" "B." "Go"
            }
        }

        system.app.a -> system.app.b "Depends on"
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
        component system.app "components-app" {
            include *
            autoLayout lr
        }
    }
}
`,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if diff := cmp.Diff(tt.want, string(RenderDSL(tt.model))); diff != "" {
				t.Errorf("RenderDSL() mismatch (-want +got):\n%s", diff)
			}
		})
	}
}
