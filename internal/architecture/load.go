package architecture

import (
	"cmp"
	"errors"
	"fmt"
	"go/ast"
	"go/types"
	"maps"
	"path"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"golang.org/x/tools/go/packages"
)

// maxLoadErrors bounds the package errors that LoadGraph reports.
const maxLoadErrors = 10

// LoadGraph loads every package of the Go module in dir, with its test files.
func LoadGraph(dir string) (Graph, error) {
	// go/packages reports absolute file names, so the root must be absolute
	// for the names to become relative to it.
	dir, err := filepath.Abs(dir)
	if err != nil {
		return Graph{}, fmt.Errorf("locate the module root: %w", err)
	}
	modules, err := loadModules(dir)
	if err != nil {
		return Graph{}, err
	}
	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedFiles | packages.NeedCompiledGoFiles |
			packages.NeedImports | packages.NeedTypes | packages.NeedSyntax |
			packages.NeedTypesInfo | packages.NeedModule | packages.NeedForTest,
		Dir:   dir,
		Tests: true,
	}
	roots, err := packages.Load(cfg, "./...")
	if err != nil {
		return Graph{}, fmt.Errorf("load packages: %w", err)
	}
	if err := packageErrors(roots); err != nil {
		return Graph{}, err
	}
	return buildGraph(dir, roots, modules)
}

// loadModules maps the import path of each package in the build graph of the
// module to the path of its module. A package of the standard library maps to
// the empty string.
func loadModules(dir string) (map[string]string, error) {
	cfg := &packages.Config{
		Mode:  packages.NeedName | packages.NeedImports | packages.NeedDeps | packages.NeedModule,
		Dir:   dir,
		Tests: true,
	}
	roots, err := packages.Load(cfg, "./...")
	if err != nil {
		return nil, fmt.Errorf("load the package graph: %w", err)
	}
	if err := packageErrors(roots); err != nil {
		return nil, err
	}
	modules := make(map[string]string)
	packages.Visit(roots, nil, func(p *packages.Package) {
		if p.Module != nil {
			modules[p.PkgPath] = p.Module.Path
		} else {
			modules[p.PkgPath] = ""
		}
	})
	return modules, nil
}

// packageErrors joins the load and type errors of the packages, up to
// maxLoadErrors of them.
func packageErrors(roots []*packages.Package) error {
	var errs []error
	packages.Visit(roots, nil, func(p *packages.Package) {
		for _, e := range p.Errors {
			if len(errs) < maxLoadErrors {
				errs = append(errs, errors.New(e.Error()))
			}
		}
	})
	if len(errs) > 0 {
		return fmt.Errorf("load packages: %w", errors.Join(errs...))
	}
	return nil
}

// buildGraph merges the package variants that go/packages returns for tests
// into one Package for each import path.
func buildGraph(dir string, roots []*packages.Package, modules map[string]string) (Graph, error) {
	b := graphBuilder{
		dir:     dir,
		modules: modules,
		byPath:  make(map[string]*Package),
		seen:    make(map[string]bool),
	}
	for _, p := range roots {
		if err := b.addVariant(p); err != nil {
			return Graph{}, err
		}
	}
	return b.graph(), nil
}

// graphBuilder collects the files of the package variants.
type graphBuilder struct {
	dir     string
	modules map[string]string
	module  string
	byPath  map[string]*Package
	seen    map[string]bool
}

// addVariant adds the files of one package variant. A test variant belongs to
// the package that it tests (ForTest).
func (b *graphBuilder) addVariant(p *packages.Package) error {
	if b.module == "" && p.Module != nil {
		b.module = p.Module.Path
	}
	owner := p.PkgPath
	if p.ForTest != "" {
		owner = p.ForTest
	}
	for i, syntax := range p.Syntax {
		gp, err := b.addFile(owner, p, syntax, p.CompiledGoFiles[i])
		if err != nil {
			return err
		}
		if gp != nil && p.ForTest == "" && p.Name == "main" {
			gp.Main = true
		}
	}
	return nil
}

// addFile adds one file to the package at path, and returns that package. It
// skips a file that another variant added, and a file outside the module
// directory, such as the generated main file of a test binary.
func (b *graphBuilder) addFile(owner string, p *packages.Package, syntax *ast.File, name string) (*Package, error) {
	rel, err := filepath.Rel(b.dir, name)
	if err != nil {
		return nil, fmt.Errorf("locate %s: %w", name, err)
	}
	rel = filepath.ToSlash(rel)
	if b.seen[rel] || rel == ".." || strings.HasPrefix(rel, "../") {
		return b.byPath[owner], nil
	}
	b.seen[rel] = true
	gp, ok := b.byPath[owner]
	if !ok {
		gp = &Package{Path: owner, Dir: path.Dir(rel)}
		b.byPath[owner] = gp
	}
	gp.Files = append(gp.Files, fileOf(p, syntax, rel, b.modules))
	return gp, nil
}

// graph returns the packages sorted by import path, each with its files
// sorted by name, so the result does not depend on the order of the variants.
func (b *graphBuilder) graph() Graph {
	g := Graph{Module: b.module}
	for _, owner := range slices.Sorted(maps.Keys(b.byPath)) {
		gp := *b.byPath[owner]
		slices.SortFunc(gp.Files, func(x, y File) int { return cmp.Compare(x.Name, y.Name) })
		g.Packages = append(g.Packages, gp)
	}
	return g
}

func fileOf(p *packages.Package, syntax *ast.File, name string, modules map[string]string) File {
	f := File{Name: name, Test: strings.HasSuffix(name, "_test.go")}
	for _, spec := range syntax.Imports {
		importPath, err := strconv.Unquote(spec.Path.Value)
		if err != nil || importPath == "C" {
			continue
		}
		f.Imports = append(f.Imports, Import{
			Path:   importPath,
			Module: modules[importPath],
			Line:   p.Fset.Position(spec.Pos()).Line,
		})
	}
	ast.Inspect(syntax, func(n ast.Node) bool {
		ident, ok := n.(*ast.Ident)
		if !ok {
			return true
		}
		if name := symbolName(p.TypesInfo.Uses[ident], p.Types); name != "" {
			f.Symbols = append(f.Symbols, Symbol{Name: name, Line: p.Fset.Position(ident.Pos()).Line})
		}
		return true
	})
	return f
}

// symbolName returns the name of a builtin function, or the "importpath.Name"
// of a package-level function or variable of another package. It returns the
// empty string for every other object.
func symbolName(obj types.Object, self *types.Package) string {
	switch o := obj.(type) {
	case *types.Builtin:
		return o.Name()
	case *types.Func, *types.Var:
		pkg := o.Pkg()
		if pkg == nil || pkg == self || pkg.Scope().Lookup(o.Name()) != o {
			return ""
		}
		return pkg.Path() + "." + o.Name()
	}
	return ""
}
