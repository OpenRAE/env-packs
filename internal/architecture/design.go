package architecture

import (
	"bytes"
	"cmp"
	"errors"
	"fmt"
	"io/fs"
	"path"
	"slices"
	"strconv"
	"strings"
)

// DesignReadme is the file in the design directory that is not a record.
const DesignReadme = "README.md"

// A Design is one design record.
type Design struct {
	// Path is the file of the record. LoadDesigns sets it.
	Path string `yaml:"-"`
	// Number is the number of the record. It is also the prefix of the file name.
	Number int `yaml:"design"`
	// Issue is the GitHub issue of the work.
	Issue int `yaml:"issue"`
	// Title names the design.
	Title string `yaml:"title"`
	// Changes lists the changes to the structure of the model.
	Changes Changes `yaml:"changes"`
}

// Changes lists the changes that a design record makes to the structure of the
// model.
type Changes struct {
	Containers   Change[string]        `yaml:"containers"`
	Components   Change[ComponentRef]  `yaml:"components"`
	Packages     Change[PackageRef]    `yaml:"packages"`
	Dependencies Change[DependencyRef] `yaml:"dependencies"`
	Modules      Change[ModuleRef]     `yaml:"modules"`
	TestModules  Change[string]        `yaml:"test_modules"`
	Rules        Change[string]        `yaml:"rules"`
}

// A Change adds and removes elements of one kind.
type Change[T comparable] struct {
	Add    []T `yaml:"add"`
	Remove []T `yaml:"remove"`
}

// A ComponentRef identifies a component and its container.
type ComponentRef struct {
	ID        string `yaml:"id"`
	Container string `yaml:"container"`
}

// A PackageRef identifies a package and the component that owns it.
type PackageRef struct {
	Path      string `yaml:"path"`
	Component string `yaml:"component"`
}

// A DependencyRef is a permitted dependency of one component on another.
type DependencyRef struct {
	From string `yaml:"from"`
	To   string `yaml:"to"`
}

// A ModuleRef is an external module that a component may import.
type ModuleRef struct {
	Component string `yaml:"component"`
	Module    string `yaml:"module"`
}

// LoadDesigns reads the design records in directory dir of fsys, sorted by
// number. The findings report files that are not well-formed records.
func LoadDesigns(fsys fs.FS, dir string) ([]Design, []Finding, error) {
	entries, err := fs.ReadDir(fsys, dir)
	if err != nil {
		return nil, nil, fmt.Errorf("read design records: %w", err)
	}
	var designs []Design
	var findings []Finding
	for _, e := range entries {
		if e.Name() == DesignReadme {
			continue
		}
		file := path.Join(dir, e.Name())
		number, ok := designNumber(e.Name())
		if !ok || !e.Type().IsRegular() {
			findings = append(findings, designFinding(file, "is not a design record file named NNNN-slug.md"))
			continue
		}
		data, err := fs.ReadFile(fsys, file)
		if err != nil {
			return nil, nil, fmt.Errorf("read design record: %w", err)
		}
		d, err := ParseDesign(data)
		if err != nil {
			findings = append(findings, designFinding(file, err.Error()))
			continue
		}
		d.Path = file
		findings = append(findings, checkDesignHeader(d, number)...)
		designs = append(designs, d)
	}
	slices.SortFunc(designs, func(a, b Design) int { return cmp.Compare(a.Number, b.Number) })
	return designs, findings, nil
}

// ParseDesign decodes the YAML front matter of a design record. The front
// matter starts at the first line, "---", and ends at the next line, "---".
func ParseDesign(data []byte) (Design, error) {
	rest, ok := bytes.CutPrefix(data, []byte("---\n"))
	if !ok {
		return Design{}, errors.New("has no YAML front matter at the first line")
	}
	front, _, ok := bytes.Cut(rest, []byte("\n---\n"))
	if !ok {
		return Design{}, errors.New("has no line that ends the YAML front matter")
	}
	var d Design
	if err := decodeStrict(front, &d); err != nil {
		return Design{}, fmt.Errorf("has invalid front matter: %w", err)
	}
	return d, nil
}

// designNumber returns the number of a design record file named NNNN-slug.md.
func designNumber(name string) (int, bool) {
	stem, ok := strings.CutSuffix(name, ".md")
	if !ok || len(stem) < 6 || stem[4] != '-' || !validID(stem[5:]) {
		return 0, false
	}
	n, err := strconv.Atoi(stem[:4])
	if err != nil || n < 1 || strings.Trim(stem[:4], "0123456789") != "" {
		return 0, false
	}
	return n, true
}

func checkDesignHeader(d Design, number int) []Finding {
	var findings []Finding
	if d.Number != number {
		findings = append(findings, designFinding(d.Path, fmt.Sprintf("has design number %d, but its file name has %d", d.Number, number)))
	}
	if d.Issue <= 0 {
		findings = append(findings, designFinding(d.Path, "names no GitHub issue"))
	}
	if d.Title == "" {
		findings = append(findings, designFinding(d.Path, "has no title"))
	}
	return findings
}

func designFinding(file, message string) Finding {
	return Finding{
		Location: file,
		Rule:     RuleDesign,
		Message:  "the design record " + message,
		Fix:      "Correct the record as docs/development/designs/README.md describes.",
	}
}

// structure is the part of the model that design records change.
type structure struct {
	containers   set[string]
	components   set[ComponentRef]
	packages     set[PackageRef]
	dependencies set[DependencyRef]
	modules      set[ModuleRef]
	testModules  set[string]
	rules        set[string]
}

type set[T comparable] map[T]struct{}

func newStructure() structure {
	return structure{
		containers:   set[string]{},
		components:   set[ComponentRef]{},
		packages:     set[PackageRef]{},
		dependencies: set[DependencyRef]{},
		modules:      set[ModuleRef]{},
		testModules:  set[string]{},
		rules:        set[string]{},
	}
}

func structureOf(m *Model) structure {
	s := newStructure()
	for _, c := range m.Containers {
		s.containers[c.ID] = struct{}{}
	}
	for _, c := range m.Components {
		s.components[ComponentRef{ID: c.ID, Container: c.Container}] = struct{}{}
		for _, p := range c.Packages {
			s.packages[PackageRef{Path: p, Component: c.ID}] = struct{}{}
		}
		for _, d := range c.DependsOn {
			s.dependencies[DependencyRef{From: c.ID, To: d}] = struct{}{}
		}
		for _, mod := range c.Modules {
			s.modules[ModuleRef{Component: c.ID, Module: mod}] = struct{}{}
		}
	}
	for _, mod := range m.TestModules {
		s.testModules[mod] = struct{}{}
	}
	for _, r := range m.Rules {
		s.rules[r.ID] = struct{}{}
	}
	return s
}

// CheckDesigns applies the design records, in number order, to an empty
// structure and compares the result with the structure of the model. The
// findings about the model name modelPath as their location.
func CheckDesigns(m *Model, modelPath string, designs []Design) []Finding {
	var findings []Finding
	built := newStructure()
	for i, d := range designs {
		if d.Number != i+1 {
			findings = append(findings, designFinding(d.Path, fmt.Sprintf("has number %d, but the records must be numbered from 1 with no gap, and this is record %d", d.Number, i+1)))
		}
		findings = append(findings, applyDesign(built, d)...)
	}
	return append(findings, compareStructures(structureOf(m), built, modelPath)...)
}

func applyDesign(s structure, d Design) []Finding {
	a := applier{design: d}
	applyChange(&a, s.containers, d.Changes.Containers, "container", showString)
	applyChange(&a, s.components, d.Changes.Components, "component", showComponent)
	applyChange(&a, s.packages, d.Changes.Packages, "package", showPackage)
	applyChange(&a, s.dependencies, d.Changes.Dependencies, "dependency", showDependency)
	applyChange(&a, s.modules, d.Changes.Modules, "module", showModule)
	applyChange(&a, s.testModules, d.Changes.TestModules, "test module", showString)
	applyChange(&a, s.rules, d.Changes.Rules, "rule", showString)
	return a.findings
}

// applier collects the findings of one design record while it is applied.
type applier struct {
	design   Design
	findings []Finding
}

func applyChange[T comparable](a *applier, s set[T], c Change[T], kind string, show func(T) string) {
	for _, x := range c.Remove {
		if _, ok := s[x]; !ok {
			a.findings = append(a.findings, designFinding(a.design.Path, fmt.Sprintf("removes %s %s, which does not exist at that point", kind, show(x))))
		}
		delete(s, x)
	}
	for _, x := range c.Add {
		if _, ok := s[x]; ok {
			a.findings = append(a.findings, designFinding(a.design.Path, fmt.Sprintf("adds %s %s, which already exists at that point", kind, show(x))))
		}
		s[x] = struct{}{}
	}
}

func compareStructures(model, built structure, modelPath string) []Finding {
	return slices.Concat(
		diffSets(model.containers, built.containers, "container", showString, modelPath),
		diffSets(model.components, built.components, "component", showComponent, modelPath),
		diffSets(model.packages, built.packages, "package", showPackage, modelPath),
		diffSets(model.dependencies, built.dependencies, "dependency", showDependency, modelPath),
		diffSets(model.modules, built.modules, "module", showModule, modelPath),
		diffSets(model.testModules, built.testModules, "test module", showString, modelPath),
		diffSets(model.rules, built.rules, "rule", showString, modelPath),
	)
}

func diffSets[T comparable](model, built set[T], kind string, show func(T) string, modelPath string) []Finding {
	var findings []Finding
	for x := range model {
		if _, ok := built[x]; !ok {
			findings = append(findings, Finding{
				Location: modelPath,
				Rule:     RuleDesign,
				Message:  fmt.Sprintf("the model has %s %s, but no design record adds it", kind, show(x)),
				Fix:      "Add it to the changes of a design record (docs/development/designs/README.md), or remove it from the model.",
			})
		}
	}
	for x := range built {
		if _, ok := model[x]; !ok {
			findings = append(findings, Finding{
				Location: modelPath,
				Rule:     RuleDesign,
				Message:  fmt.Sprintf("the design records add %s %s, but the model does not have it", kind, show(x)),
				Fix:      "Add it to the model, or remove it from the design record.",
			})
		}
	}
	return findings
}

func showString(s string) string { return strconv.Quote(s) }

func showComponent(c ComponentRef) string {
	return fmt.Sprintf("%q in container %q", c.ID, c.Container)
}

func showPackage(p PackageRef) string {
	return fmt.Sprintf("%q of component %q", p.Path, p.Component)
}

func showDependency(d DependencyRef) string {
	return fmt.Sprintf("%q -> %q", d.From, d.To)
}

func showModule(m ModuleRef) string {
	return fmt.Sprintf("%q of component %q", m.Module, m.Component)
}
