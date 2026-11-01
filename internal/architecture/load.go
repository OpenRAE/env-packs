package architecture

import (
	"cmp"
	"errors"
	"fmt"
	"go/ast"
	"go/types"
	"io/fs"
	"maps"
	"os"
	"path"
	"path/filepath"
	"slices"
	"strings"

	"golang.org/x/tools/go/packages"
)

// maxLoadErrors bounds the package errors that LoadGraph reports.
const maxLoadErrors = 10

// A Build is one configuration of the go command that loads the code.
type Build struct {
	// Name names the build in error messages, for example "linux/amd64".
	Name string
	// Env is the environment of the go command, in the form of os.Environ.
	// A nil environment is the environment of the process.
	Env []string
}

// LoadGraph loads every package of the Go module in dir, with its test files,
// once for each build. A file is part of the graph when a build reads it, and
// a path is unread when no build reads it. The paths in the graph are relative
// to the module root.
func LoadGraph(dir string, builds []Build) (Graph, error) {
	if len(builds) == 0 {
		return Graph{}, errors.New("no build to load")
	}
	graphs := make([]Graph, 0, len(builds))
	for _, b := range builds {
		g, err := loadBuild(dir, b.Env)
		if err != nil {
			return Graph{}, fmt.Errorf("build %s: %w", b.Name, err)
		}
		graphs = append(graphs, g)
	}
	return mergeGraphs(graphs), nil
}

// loadBuild loads the graph of the module in dir for one environment.
func loadBuild(dir string, env []string) (Graph, error) {
	deps, err := load(dir, env, packages.NeedName|packages.NeedImports|packages.NeedDeps|packages.NeedModule)
	if err != nil {
		return Graph{}, err
	}
	roots, err := load(dir, env, packages.NeedName|packages.NeedSyntax|packages.NeedTypes|
		packages.NeedTypesInfo|packages.NeedModule|packages.NeedForTest)
	if err != nil {
		return Graph{}, err
	}
	mod := mainModule(roots)
	if mod == nil {
		return Graph{}, fmt.Errorf("no Go package in %s", dir)
	}
	return buildGraph(mod, roots, modulePaths(deps)), nil
}

// mergeGraphs merges the graphs of the builds. A package has the files of
// each graph. The graphs that read one file read the same source, so the
// merge keeps the first copy of each file. A package is a main package when
// it is a main package in one graph. A path is unread when it is unread in
// each graph.
func mergeGraphs(graphs []Graph) Graph {
	merged := Graph{Module: graphs[0].Module, Unread: graphs[0].Unread}
	byPath := make(map[string]*Package)
	seen := make(map[string]bool)
	for _, g := range graphs {
		for _, p := range g.Packages {
			mp := byPath[p.Path]
			if mp == nil {
				mp = &Package{Path: p.Path, Dir: p.Dir}
				byPath[p.Path] = mp
			}
			mp.Main = mp.Main || p.Main
			for _, f := range p.Files {
				if !seen[f.Name] {
					seen[f.Name] = true
					mp.Files = append(mp.Files, f)
				}
			}
		}
		merged.Unread = slices.DeleteFunc(merged.Unread, func(path string) bool { return !slices.Contains(g.Unread, path) })
	}
	for _, pkgPath := range slices.Sorted(maps.Keys(byPath)) {
		mp := byPath[pkgPath]
		slices.SortFunc(mp.Files, func(x, y File) int { return cmp.Compare(x.Name, y.Name) })
		merged.Packages = append(merged.Packages, *mp)
	}
	return merged
}

// load loads the packages of the module in dir that match the pattern ./...,
// with their test variants. It fails when a package has an error.
func load(dir string, env []string, mode packages.LoadMode) ([]*packages.Package, error) {
	roots, err := packages.Load(&packages.Config{Mode: mode, Dir: dir, Env: env, Tests: true}, "./...")
	if err == nil {
		err = packageErrors(roots)
	}
	if err != nil {
		return nil, fmt.Errorf("load the packages in %s: %w", dir, err)
	}
	return roots, nil
}

// packageErrors joins the errors of the packages and of their imports. It
// reports maxLoadErrors of them, and then the number of the others.
func packageErrors(roots []*packages.Package) error {
	var errs []error
	packages.Visit(roots, nil, func(p *packages.Package) {
		for _, e := range p.Errors {
			errs = append(errs, e)
		}
	})
	if len(errs) > maxLoadErrors {
		errs = append(errs[:maxLoadErrors], fmt.Errorf("and %d more errors", len(errs)-maxLoadErrors))
	}
	return errors.Join(errs...)
}

// mainModule returns the module of the first package that has a module.
// LoadGraph loads only packages of the main module.
func mainModule(pkgs []*packages.Package) *packages.Module {
	for _, p := range pkgs {
		if p.Module != nil {
			return p.Module
		}
	}
	return nil
}

// modulePaths maps the import path of each package in the import graph of the
// roots to the path of its module. A package of the standard library has no
// module, so it has no entry.
func modulePaths(roots []*packages.Package) map[string]string {
	modules := make(map[string]string)
	packages.Visit(roots, nil, func(p *packages.Package) {
		if p.Module != nil {
			modules[p.PkgPath] = p.Module.Path
		}
	})
	return modules
}

// buildGraph merges the package variants that go/packages returns for tests
// into one Package for each import path. A test variant belongs to the
// package that it tests (ForTest), so a file of a package with tests occurs
// once for each variant, and mergeGraphs keeps one copy. A file outside the
// module root, such as the generated main file of a test binary, is not part
// of the graph.
func buildGraph(mod *packages.Module, roots []*packages.Package, modules map[string]string) Graph {
	byPath := make(map[string]*Package)
	read := make(map[string]bool)
	for _, p := range roots {
		owner := cmp.Or(p.ForTest, p.PkgPath)
		for _, syntax := range p.Syntax {
			name, ok := strings.CutPrefix(p.Fset.File(syntax.FileStart).Name(), mod.Dir+string(filepath.Separator))
			if !ok {
				continue
			}
			read[name] = true
			gp := byPath[owner]
			if gp == nil {
				gp = &Package{Path: owner, Dir: path.Dir(name)}
				byPath[owner] = gp
			}
			if p.Name == "main" {
				gp.Main = true
			}
			gp.Files = append(gp.Files, fileOf(p, syntax, name, modules))
		}
	}
	g := Graph{Module: mod.Path, Unread: unread(os.DirFS(mod.Dir), ".", read)}
	for _, owner := range slices.Sorted(maps.Keys(byPath)) {
		gp := byPath[owner]
		slices.SortFunc(gp.Files, func(x, y File) int { return cmp.Compare(x.Name, y.Name) })
		g.Packages = append(g.Packages, *gp)
	}
	return g
}

// unread returns the paths under dir that match the pattern ./..., but that
// are not in read: the Go files that build constraints exclude or that use
// cgo, and each directory that fsys cannot list. Like the go command, it
// skips the directories named vendor or testdata, the files and directories
// whose names begin with "." or "_", and the directories of other modules.
func unread(fsys fs.FS, dir string, read map[string]bool) []string {
	entries, err := fs.ReadDir(fsys, dir)
	if err != nil {
		return []string{dir}
	}
	var paths []string
	for _, e := range entries {
		if strings.HasPrefix(e.Name(), ".") || strings.HasPrefix(e.Name(), "_") {
			continue
		}
		name := path.Join(dir, e.Name())
		switch {
		case e.IsDir():
			if e.Name() != "vendor" && e.Name() != "testdata" && !isModule(fsys, name) {
				paths = append(paths, unread(fsys, name, read)...)
			}
		case strings.HasSuffix(e.Name(), ".go") && !read[name]:
			paths = append(paths, name)
		}
	}
	return paths
}

// isModule reports whether directory dir of fsys holds a go.mod file.
func isModule(fsys fs.FS, dir string) bool {
	_, err := fs.Stat(fsys, path.Join(dir, "go.mod"))
	return err == nil
}

func fileOf(p *packages.Package, syntax *ast.File, name string, modules map[string]string) File {
	f := File{Name: name, Test: strings.HasSuffix(name, "_test.go")}
	for _, spec := range syntax.Imports {
		importPath := p.TypesInfo.PkgNameOf(spec).Imported().Path()
		f.Imports = append(f.Imports, Import{
			Path:   importPath,
			Module: modules[importPath],
			Line:   p.Fset.Position(spec.Pos()).Line,
		})
	}
	ast.Inspect(syntax, func(n ast.Node) bool {
		if ident, ok := n.(*ast.Ident); ok {
			if symbol := symbolName(p.TypesInfo.Uses[ident], p.Types); symbol != "" {
				f.Symbols = append(f.Symbols, Symbol{Name: symbol, Line: p.Fset.Position(ident.Pos()).Line})
			}
		}
		return true
	})
	return f
}

// symbolName returns the name of a builtin function, or the "importpath.Name"
// of a package-level function or variable of another package. It returns the
// empty string for every other object. A method of a predeclared type, such
// as error.Error, has no package. For a nil package, Scope returns the
// universe scope, which does not hold the method.
func symbolName(obj types.Object, self *types.Package) string {
	switch o := obj.(type) {
	case *types.Builtin:
		return o.Name()
	case *types.Func, *types.Var:
		if pkg := o.Pkg(); pkg != self && pkg.Scope().Lookup(o.Name()) == o {
			return pkg.Path() + "." + o.Name()
		}
	}
	return ""
}
