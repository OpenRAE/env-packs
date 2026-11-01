package architecture

import (
	_ "embed" // The go:embed directive below needs the embed package.
	"strings"
	"text/template"
)

// workspaceTemplate is the Structurizr DSL template of the C4 view.
//
//go:embed workspace.dsl.tmpl
var workspaceTemplate string

// RenderDSL renders the model as a Structurizr DSL workspace. The output
// depends only on the model, so a check can compare it with a committed file.
func RenderDSL(m *Model) []byte {
	t := template.Must(template.New("workspace").Funcs(template.FuncMap{"q": quote, "id": dslID}).Parse(workspaceTemplate))
	var b strings.Builder
	err := t.Execute(&b, workspace{
		System:          m.System,
		People:          m.People,
		ExternalSystems: m.ExternalSystems,
		Containers:      containersOf(m),
		Edges:           edgesOf(m),
	})
	// Execute fails only for a defect in the fixed template, as Parse does,
	// so the defect panics as it does in template.Must.
	if err != nil {
		panic(err)
	}
	return []byte(b.String())
}

// workspace is the data of the template.
type workspace struct {
	System          Element
	People          []Element
	ExternalSystems []Element
	Containers      []containerView
	Edges           []edge
}

// containerView is a container with its components, in the order of the
// model.
type containerView struct {
	Container
	Components []Component
}

// An edge is one relationship of the workspace.
type edge struct {
	From, To, Description string
}

func containersOf(m *Model) []containerView {
	views := make([]containerView, 0, len(m.Containers))
	for _, c := range m.Containers {
		v := containerView{Container: c}
		for _, comp := range m.Components {
			if comp.Container == c.ID {
				v.Components = append(v.Components, comp)
			}
		}
		views = append(views, v)
	}
	return views
}

// edgesOf returns the relationships of the model and the dependencies between
// known components, in the order of the model.
func edgesOf(m *Model) []edge {
	var edges []edge
	for _, r := range m.Relationships {
		edges = append(edges, edge{From: dslID(r.From), To: dslID(r.To), Description: r.Description})
	}
	for _, c := range m.Components {
		for _, d := range c.DependsOn {
			if to, ok := m.Component(d); ok {
				edges = append(edges, edge{From: componentRef(m, c), To: componentRef(m, *to), Description: "Depends on"})
			}
		}
	}
	return edges
}

// componentRef returns the hierarchical DSL identifier of a component.
func componentRef(m *Model, c Component) string {
	return dslID(m.System.ID) + "." + dslID(c.Container) + "." + dslID(c.ID)
}

// dslID turns a model identifier into a DSL identifier.
func dslID(id string) string {
	return strings.ReplaceAll(id, "-", "_")
}

// quote returns s as a DSL string literal.
func quote(s string) string {
	return `"` + strings.NewReplacer(`\`, `\\`, `"`, `\"`).Replace(s) + `"`
}
