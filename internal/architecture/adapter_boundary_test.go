package architecture

import (
	"io/fs"
	"os"
	"strings"
	"testing"
)

func TestRepositoryRAESImportBoundary(t *testing.T) {
	root, err := os.OpenRoot("../..")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if closeErr := root.Close(); closeErr != nil {
			t.Error(closeErr)
		}
	})
	data, err := fs.ReadFile(root.FS(), "architecture/model.yaml")
	if err != nil {
		t.Fatal(err)
	}
	model, err := ParseModel(data)
	if err != nil {
		t.Fatal(err)
	}
	for _, tc := range []struct {
		component string
		forbidden bool
	}{{"raes-adapter", false}, {"repository-policy", true}, {"contract-alignment", true}} {
		t.Run(tc.component, func(t *testing.T) {
			graph := raesImportGraph(model, tc.component)
			found := hasRAESImportFinding(model, graph)
			if found != tc.forbidden {
				t.Errorf("RAES import forbidden = %t, want %t", found, tc.forbidden)
			}
		})
	}
}

func hasRAESImportFinding(model *Model, graph Graph) bool {
	for _, finding := range CheckCode(model, "architecture/model.yaml", graph) {
		if finding.Rule == "raes-through-adapter" {
			return true
		}
	}
	return false
}

func raesImportGraph(model *Model, importing string) Graph {
	graph := Graph{Module: model.Module}
	for _, component := range model.Components {
		for _, name := range component.Packages {
			p := Package{Path: name, Dir: strings.TrimPrefix(name, model.Module+"/")}
			if component.ID == importing {
				p.Files = []File{{Name: p.Dir + "/fixture.go", Imports: []Import{{Path: "github.com/OpenRAE/rae/implementations/go/contract/concept", Module: "github.com/OpenRAE/rae/implementations/go", Line: 3}}}}
			}
			graph.Packages = append(graph.Packages, p)
		}
	}
	return graph
}
