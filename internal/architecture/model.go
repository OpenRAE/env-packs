package architecture

import (
	"fmt"
	"go/token"
	"go/types"
	"regexp"
	"slices"
	"strings"

	"github.com/OpenRAE/env-packs/internal/report"
	"github.com/OpenRAE/env-packs/internal/strictyaml"
	"golang.org/x/mod/module"
)

// Model is the architecture model of the repository.
type Model struct {
	// Version is the format version of the model. It is 1.
	Version int `yaml:"version"`
	// Module is the path of the Go module that the model describes.
	Module string `yaml:"module"`
	// Platforms are the release targets, each as "GOOS/GOARCH". The code
	// check reads the code that each platform builds.
	Platforms []string `yaml:"platforms"`
	// System is the software system of the repository.
	System Element `yaml:"system"`
	// People are the people who use the system.
	People []Element `yaml:"people"`
	// ExternalSystems are the systems that the system depends on.
	ExternalSystems []Element `yaml:"external_systems"`
	// Relationships connect the system, the people, and the external systems.
	Relationships []Relationship `yaml:"relationships"`
	// Containers are the deployable parts of the system.
	Containers []Container `yaml:"containers"`
	// Components are the parts of the containers. Each component owns Go packages.
	Components []Component `yaml:"components"`
	// TestModules are the external modules that any test file may import.
	TestModules []string `yaml:"test_modules"`
	// Rules forbid imports and symbols in a scope of the code.
	Rules []Rule `yaml:"rules"`
}

// An Element is the system, a person, or an external system.
type Element struct {
	ID          string `yaml:"id"`
	Name        string `yaml:"name"`
	Description string `yaml:"description"`
}

// A Relationship is a C4 relationship between two elements.
type Relationship struct {
	From        string `yaml:"from"`
	To          string `yaml:"to"`
	Description string `yaml:"description"`
}

// A Container is a deployable part of the system.
type Container struct {
	ID          string `yaml:"id"`
	Name        string `yaml:"name"`
	Technology  string `yaml:"technology"`
	Description string `yaml:"description"`
}

// A Component is a part of a container that owns Go packages.
type Component struct {
	ID          string `yaml:"id"`
	Container   string `yaml:"container"`
	Description string `yaml:"description"`
	// Packages are the import paths of the packages that the component owns.
	Packages []string `yaml:"packages"`
	// DependsOn are the components that the component may import.
	DependsOn []string `yaml:"depends_on"`
	// Modules are the external modules that the component may import.
	Modules []string `yaml:"modules"`
}

// A Rule forbids imports and symbols in a scope of the code.
type Rule struct {
	ID          string    `yaml:"id"`
	Description string    `yaml:"description"`
	Scope       RuleScope `yaml:"scope"`
	// ForbidImports are import paths. "path/..." also matches the packages
	// below path.
	ForbidImports []string `yaml:"forbid_imports"`
	// ForbidSymbols are "importpath.Name" symbols or builtin function names.
	ForbidSymbols []string `yaml:"forbid_symbols"`
	// ExceptComponents are components that the rule does not apply to.
	ExceptComponents []string `yaml:"except_components"`
	// Fix tells how to correct a finding of the rule.
	Fix string `yaml:"fix"`
}

// A RuleScope selects the code that a rule applies to.
type RuleScope struct {
	// Containers are the containers whose components the rule applies to.
	Containers []string `yaml:"containers"`
	// MainPackages makes the rule apply to main packages too.
	MainPackages bool `yaml:"main_packages"`
	// TestFiles makes the rule apply to test files too.
	TestFiles bool `yaml:"test_files"`
}

// ParseModel decodes a model. It rejects unknown fields and more than one
// YAML document.
func ParseModel(data []byte) (*Model, error) {
	var m Model
	if err := strictyaml.Decode(data, &m); err != nil {
		return nil, fmt.Errorf("decode model: %w", err)
	}
	return &m, nil
}

// Component returns the component with the given identifier.
func (m *Model) Component(id string) (*Component, bool) {
	i := slices.IndexFunc(m.Components, func(c Component) bool { return c.ID == id })
	if i < 0 {
		return nil, false
	}
	return &m.Components[i], true
}

// Owners maps each package of the model to the component that owns it.
func (m *Model) Owners() map[string]*Component {
	owners := make(map[string]*Component)
	for i := range m.Components {
		for _, p := range m.Components[i].Packages {
			owners[p] = &m.Components[i]
		}
	}
	return owners
}

// ValidateModel returns the defects of the model. The findings name path as
// their location.
func ValidateModel(m *Model, path string) []report.Finding {
	v := modelValidator{path: path, model: m}
	v.checkHeader()
	v.checkIDs()
	v.checkRelationships()
	v.checkComponents()
	v.checkCycles()
	v.checkModuleList("test module", m.TestModules)
	v.checkRules()
	return v.findings
}

// modelValidator collects the defects of one model.
type modelValidator struct {
	path     string
	model    *Model
	findings []report.Finding
}

func (v *modelValidator) addf(format string, args ...any) {
	v.findings = append(v.findings, report.Finding{
		Location: v.path,
		Rule:     RuleModel,
		Message:  fmt.Sprintf(format, args...),
		Fix:      "Correct the model in a design step (docs/development/designs/README.md).",
	})
}

func (v *modelValidator) checkHeader() {
	if v.model.Version != 1 {
		v.addf("version is %d; the only supported version is 1", v.model.Version)
	}
	if err := module.CheckPath(v.model.Module); err != nil {
		v.addf("the module path is not valid: %v", err)
	}
	if v.model.System.Name == "" {
		v.addf("the system has no name")
	}
	if len(v.model.Platforms) == 0 {
		v.addf("the model names no platform")
	}
	seen := make(map[string]bool)
	for _, p := range v.model.Platforms {
		if !platformPattern.MatchString(p) || seen[p] {
			v.addf("platform %q is not GOOS/GOARCH or is listed more than once", p)
		}
		seen[p] = true
	}
}

func (v *modelValidator) checkIDs() {
	seen := make(map[string]bool)
	claim := func(kind, id string) {
		switch {
		case !validID(id):
			v.addf("%s identifier %q must be lowercase words joined by hyphens", kind, id)
		case seen[id]:
			v.addf("identifier %q is used more than once", id)
		}
		seen[id] = true
	}
	claim("system", v.model.System.ID)
	for _, e := range v.model.People {
		claim("person", e.ID)
	}
	for _, e := range v.model.ExternalSystems {
		claim("external system", e.ID)
	}
	for _, c := range v.model.Containers {
		claim("container", c.ID)
	}
	for _, c := range v.model.Components {
		claim("component", c.ID)
	}
	ruleIDs := make(map[string]bool)
	for _, r := range v.model.Rules {
		if !validID(r.ID) || ruleIDs[r.ID] {
			v.addf("rule identifier %q is not valid or is used more than once", r.ID)
		}
		ruleIDs[r.ID] = true
	}
}

func (v *modelValidator) checkRelationships() {
	context := map[string]bool{v.model.System.ID: true}
	for _, e := range slices.Concat(v.model.People, v.model.ExternalSystems) {
		context[e.ID] = true
	}
	for _, r := range v.model.Relationships {
		if !context[r.From] || !context[r.To] {
			v.addf("relationship %q -> %q must connect the system, people, or external systems", r.From, r.To)
		}
	}
}

func (v *modelValidator) checkComponents() {
	containers := make(map[string]bool)
	for _, c := range v.model.Containers {
		containers[c.ID] = true
	}
	owner := make(map[string]string)
	for _, c := range v.model.Components {
		if !containers[c.Container] {
			v.addf("component %q names unknown container %q", c.ID, c.Container)
		}
		if c.Description == "" {
			v.addf("component %q has no description", c.ID)
		}
		for _, p := range c.Packages {
			v.checkPackage(c.ID, p, owner)
		}
		v.checkDependsOn(c)
		v.checkModuleList(fmt.Sprintf("module of component %q", c.ID), c.Modules)
	}
}

func (v *modelValidator) checkPackage(component, path string, owner map[string]string) {
	if path != v.model.Module && !strings.HasPrefix(path, v.model.Module+"/") {
		v.addf("package %q of component %q is outside module %q", path, component, v.model.Module)
	}
	if prior, ok := owner[path]; ok {
		v.addf("package %q has two owners: %q and %q", path, prior, component)
	}
	owner[path] = component
}

func (v *modelValidator) checkDependsOn(c Component) {
	seen := make(map[string]bool)
	for _, d := range c.DependsOn {
		_, known := v.model.Component(d)
		switch {
		case !known:
			v.addf("component %q depends on unknown component %q", c.ID, d)
		case d == c.ID:
			v.addf("component %q depends on itself", c.ID)
		case seen[d]:
			v.addf("component %q lists dependency %q more than once", c.ID, d)
		}
		seen[d] = true
	}
}

func (v *modelValidator) checkModuleList(kind string, modules []string) {
	seen := make(map[string]bool)
	for _, mod := range modules {
		if err := module.CheckPath(mod); err != nil {
			v.addf("%s is not valid: %v", kind, err)
		}
		if seen[mod] {
			v.addf("%s %q is listed more than once", kind, mod)
		}
		seen[mod] = true
	}
}

// checkCycles reports each component that can reach itself through the
// dependencies. The model keeps the components in layers.
func (v *modelValidator) checkCycles() {
	for _, c := range v.model.Components {
		if v.reaches(c.ID, c.ID, make(map[string]bool)) {
			v.addf("the dependencies of component %q form a cycle", c.ID)
		}
	}
}

// reaches reports whether component target is reachable from component from
// through one or more dependencies. The seen map stops a second visit.
func (v *modelValidator) reaches(from, target string, seen map[string]bool) bool {
	c, ok := v.model.Component(from)
	if !ok {
		return false
	}
	for _, d := range c.DependsOn {
		if d == target {
			return true
		}
		if !seen[d] {
			seen[d] = true
			if v.reaches(d, target, seen) {
				return true
			}
		}
	}
	return false
}

func (v *modelValidator) checkRules() {
	for _, r := range v.model.Rules {
		v.checkRuleScope(r)
		v.checkRuleBody(r)
	}
}

func (v *modelValidator) checkRuleBody(r Rule) {
	if len(r.ForbidImports) == 0 && len(r.ForbidSymbols) == 0 {
		v.addf("rule %q forbids nothing", r.ID)
	}
	for _, p := range r.ForbidImports {
		if err := module.CheckImportPath(strings.TrimSuffix(p, "/...")); err != nil {
			v.addf("rule %q has an invalid import pattern: %v", r.ID, err)
		}
	}
	for _, s := range r.ForbidSymbols {
		if !validSymbol(s) {
			v.addf("rule %q has invalid symbol %q", r.ID, s)
		}
	}
	if r.Description == "" || r.Fix == "" {
		v.addf("rule %q needs a description and a fix", r.ID)
	}
}

func (v *modelValidator) checkRuleScope(r Rule) {
	if len(r.Scope.Containers) == 0 {
		v.addf("rule %q applies to no container", r.ID)
	}
	for _, id := range r.Scope.Containers {
		if !slices.ContainsFunc(v.model.Containers, func(c Container) bool { return c.ID == id }) {
			v.addf("rule %q names unknown container %q", r.ID, id)
		}
	}
	for _, id := range r.ExceptComponents {
		if _, ok := v.model.Component(id); !ok {
			v.addf("rule %q names unknown component %q", r.ID, id)
		}
	}
}

// idExpr matches an identifier: lowercase ASCII words of letters and digits,
// joined by single hyphens. The first word starts with a letter.
const idExpr = `[a-z][a-z0-9]*(?:-[a-z0-9]+)*`

// platformPattern matches a platform, "GOOS/GOARCH".
var platformPattern = regexp.MustCompile(`^[a-z0-9]+/[a-z0-9]+$`)

// idPattern matches an identifier and nothing else.
var idPattern = regexp.MustCompile(`^` + idExpr + `$`)

// validID reports whether id is an identifier.
func validID(id string) bool {
	return idPattern.MatchString(id)
}

// validSymbol reports whether s is a builtin function, or "importpath.Name"
// with an exported Name.
func validSymbol(s string) bool {
	i := strings.LastIndex(s, ".")
	if i == -1 {
		_, ok := types.Universe.Lookup(s).(*types.Builtin)
		return ok
	}
	name := s[i+1:]
	return module.CheckImportPath(s[:i]) == nil && token.IsIdentifier(name) && token.IsExported(name)
}
