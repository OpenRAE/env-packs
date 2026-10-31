package architecture

import (
	"fmt"
	"strings"
)

// RenderDSL renders the model as a Structurizr DSL workspace. The output
// depends only on the model, so a check can compare it with a committed file.
func RenderDSL(m *Model) []byte {
	w := &dslWriter{}
	w.linef("workspace %s %s {", quote(m.System.Name), quote(m.System.Description))
	w.indent++
	w.linef("!identifiers hierarchical")
	w.blank()
	w.linef("model {")
	w.indent++
	w.writeContext(m)
	w.writeSystem(m)
	w.writeRelationships(m)
	w.indent--
	w.linef("}")
	w.blank()
	w.writeViews(m)
	w.indent--
	w.linef("}")
	return []byte(w.b.String())
}

// dslWriter writes indented DSL lines.
type dslWriter struct {
	b      strings.Builder
	indent int
}

func (w *dslWriter) linef(format string, args ...any) {
	w.b.WriteString(strings.Repeat("    ", w.indent))
	fmt.Fprintf(&w.b, format, args...)
	w.b.WriteByte('\n')
}

func (w *dslWriter) blank() {
	w.b.WriteByte('\n')
}

func (w *dslWriter) writeContext(m *Model) {
	for _, p := range m.People {
		w.linef("%s = person %s %s", dslID(p.ID), quote(p.Name), quote(p.Description))
	}
	for _, e := range m.ExternalSystems {
		w.linef("%s = softwareSystem %s %s {", dslID(e.ID), quote(e.Name), quote(e.Description))
		w.indent++
		w.linef(`tags "External"`)
		w.indent--
		w.linef("}")
	}
}

func (w *dslWriter) writeSystem(m *Model) {
	w.linef("%s = softwareSystem %s %s {", dslID(m.System.ID), quote(m.System.Name), quote(m.System.Description))
	w.indent++
	for _, c := range m.Containers {
		components := componentsOf(m, c.ID)
		if len(components) == 0 {
			w.linef("%s = container %s %s %s", dslID(c.ID), quote(c.Name), quote(c.Description), quote(c.Technology))
			continue
		}
		w.linef("%s = container %s %s %s {", dslID(c.ID), quote(c.Name), quote(c.Description), quote(c.Technology))
		w.indent++
		for _, comp := range components {
			w.linef("%s = component %s %s %s", dslID(comp.ID), quote(comp.ID), quote(comp.Description), quote("Go"))
		}
		w.indent--
		w.linef("}")
	}
	w.indent--
	w.linef("}")
}

func (w *dslWriter) writeRelationships(m *Model) {
	edges := edgesOf(m)
	if len(edges) == 0 {
		return
	}
	w.blank()
	for _, e := range edges {
		w.linef("%s -> %s %s", e.from, e.to, quote(e.description))
	}
}

// An edge is one relationship of the DSL workspace.
type edge struct {
	from, to, description string
}

// edgesOf returns the relationships of the model and the dependencies between
// known components, in the order of the model.
func edgesOf(m *Model) []edge {
	var edges []edge
	for _, r := range m.Relationships {
		edges = append(edges, edge{from: dslID(r.From), to: dslID(r.To), description: r.Description})
	}
	for _, c := range m.Components {
		for _, d := range c.DependsOn {
			if to, ok := m.Component(d); ok {
				edges = append(edges, edge{from: componentRef(m, c), to: componentRef(m, *to), description: "Depends on"})
			}
		}
	}
	return edges
}

func (w *dslWriter) writeViews(m *Model) {
	w.linef("views {")
	w.indent++
	system := dslID(m.System.ID)
	w.writeView("systemContext "+system, "context")
	w.writeView("container "+system, "containers")
	for _, c := range m.Containers {
		if len(componentsOf(m, c.ID)) > 0 {
			w.writeView("component "+system+"."+dslID(c.ID), "components-"+c.ID)
		}
	}
	w.indent--
	w.linef("}")
}

func (w *dslWriter) writeView(kind, key string) {
	w.linef("%s %s {", kind, quote(key))
	w.indent++
	w.linef("include *")
	w.linef("autoLayout lr")
	w.indent--
	w.linef("}")
}

func componentsOf(m *Model, container string) []Component {
	var components []Component
	for _, c := range m.Components {
		if c.Container == container {
			components = append(components, c)
		}
	}
	return components
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
