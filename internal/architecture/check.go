package architecture

import (
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/OpenRAE/env-packs/internal/report"
)

// CheckCode compares the code with the model. The findings about the model
// itself name modelPath as their location.
func CheckCode(m *Model, modelPath string, g Graph) []report.Finding {
	c := codeChecker{model: m, owners: m.Owners(), graph: g}
	c.checkModule(modelPath)
	c.checkOwnership(modelPath)
	for _, name := range g.Unread {
		c.add(report.Finding{
			Location: name,
			Rule:     RuleUnreadPath,
			Message:  "the check cannot read this path, so the rules of the model do not apply to it",
			Fix:      "Remove the build constraint or the cgo code, or make the directory readable. If the code needs them, change tools/archcheck in a design step so that the check reads the path.",
		})
	}
	for _, p := range g.Packages {
		owner, ok := c.owners[p.Path]
		if !ok {
			continue
		}
		for _, f := range p.Files {
			c.checkFile(owner, p, f)
		}
	}
	return c.findings
}

// codeChecker collects the findings of one comparison of the code with the
// model.
type codeChecker struct {
	model    *Model
	owners   map[string]*Component
	graph    Graph
	findings []report.Finding
}

func (c *codeChecker) add(f report.Finding) {
	c.findings = append(c.findings, f)
}

func (c *codeChecker) checkModule(modelPath string) {
	if c.graph.Module != c.model.Module {
		c.add(report.Finding{
			Location: modelPath,
			Rule:     RuleModel,
			Message:  fmt.Sprintf("the model describes module %q, but the code is module %q", c.model.Module, c.graph.Module),
			Fix:      "Set the module of the model to the module path in go.mod, in a design step.",
		})
	}
}

func (c *codeChecker) checkOwnership(modelPath string) {
	inCode := make(map[string]bool)
	for _, p := range c.graph.Packages {
		inCode[p.Path] = true
		if _, ok := c.owners[p.Path]; !ok {
			c.add(report.Finding{
				Location: p.Dir,
				Rule:     RulePackageOwner,
				Message:  fmt.Sprintf("package %q has no component", p.Path),
				Fix:      "Add the package to the packages of a component in architecture/model.yaml, in a design step (docs/development/designs/README.md).",
			})
		}
	}
	for _, comp := range c.model.Components {
		for _, p := range comp.Packages {
			if !inCode[p] {
				c.add(report.Finding{
					Location: modelPath,
					Rule:     RuleUnknownPackage,
					Message:  fmt.Sprintf("component %q owns package %q, but the code has no such package", comp.ID, p),
					Fix:      "Write the package, or remove it from the model in a design step.",
				})
			}
		}
	}
}

func (c *codeChecker) checkFile(owner *Component, p Package, f File) {
	rules := c.applicableRules(owner, p.Main, f.Test)
	for _, imp := range f.Imports {
		switch {
		case imp.Module == c.graph.Module:
			c.checkComponentImport(owner, f, imp)
		case imp.Module != "":
			c.checkModuleImport(owner, f, imp)
		}
		for _, r := range rules {
			if slices.ContainsFunc(r.ForbidImports, func(pattern string) bool { return matchImport(pattern, imp.Path) }) {
				c.add(ruleFinding(r, owner, f, imp.Line, "import of "+strconv.Quote(imp.Path)))
			}
		}
	}
	for _, s := range f.Symbols {
		for _, r := range rules {
			if slices.Contains(r.ForbidSymbols, s.Name) {
				c.add(ruleFinding(r, owner, f, s.Line, "use of "+s.Name))
			}
		}
	}
}

func (c *codeChecker) checkComponentImport(owner *Component, f File, imp Import) {
	target, ok := c.owners[imp.Path]
	if !ok || target.ID == owner.ID || slices.Contains(owner.DependsOn, target.ID) {
		return
	}
	allowed := "no other component"
	if len(owner.DependsOn) > 0 {
		allowed = strings.Join(slices.Sorted(slices.Values(owner.DependsOn)), ", ")
	}
	c.add(report.Finding{
		Location: location(f, imp.Line),
		Rule:     RuleComponentDependency,
		Message:  fmt.Sprintf("component %q imports %q of component %q, but the model does not permit this dependency", owner.ID, imp.Path, target.ID),
		Fix:      fmt.Sprintf("Use a component that %q may depend on (%s), or add the dependency %q -> %q to the model in a design step.", owner.ID, allowed, owner.ID, target.ID),
	})
}

func (c *codeChecker) checkModuleImport(owner *Component, f File, imp Import) {
	if slices.Contains(owner.Modules, imp.Module) || f.Test && slices.Contains(c.model.TestModules, imp.Module) {
		return
	}
	fix := fmt.Sprintf("Add module %q to the modules of component %q in a design step, and give the reason in the design record.", imp.Module, owner.ID)
	if f.Test {
		fix = fmt.Sprintf("Add module %q to the test modules or to the modules of component %q in a design step, and give the reason in the design record.", imp.Module, owner.ID)
	}
	c.add(report.Finding{
		Location: location(f, imp.Line),
		Rule:     RuleExternalModule,
		Message:  fmt.Sprintf("component %q imports %q from module %q, but the model does not permit this module", owner.ID, imp.Path, imp.Module),
		Fix:      fix,
	})
}

// applicableRules returns the rules that apply to a file of a component.
func (c *codeChecker) applicableRules(owner *Component, mainPackage, testFile bool) []Rule {
	var rules []Rule
	for _, r := range c.model.Rules {
		if slices.Contains(r.Scope.Containers, owner.Container) &&
			!slices.Contains(r.ExceptComponents, owner.ID) &&
			(!mainPackage || r.Scope.MainPackages) &&
			(!testFile || r.Scope.TestFiles) {
			rules = append(rules, r)
		}
	}
	return rules
}

func ruleFinding(r Rule, owner *Component, f File, line int, what string) report.Finding {
	return report.Finding{
		Location: location(f, line),
		Rule:     r.ID,
		Message:  fmt.Sprintf("%s in component %q breaks the rule: %s", what, owner.ID, r.Description),
		Fix:      r.Fix,
	}
}

// matchImport reports whether an import path matches a pattern. A pattern
// that ends in "/..." matches its base path and every path below it.
func matchImport(pattern, path string) bool {
	if base, ok := strings.CutSuffix(pattern, "/..."); ok {
		return path == base || strings.HasPrefix(path, base+"/")
	}
	return path == pattern
}

func location(f File, line int) string {
	return f.Name + ":" + strconv.Itoa(line)
}
