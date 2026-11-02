package architecture

import (
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/google/go-cmp/cmp"
	"golang.org/x/tools/go/packages"
)

func TestLoadGraph(t *testing.T) {
	got, err := LoadGraph("testdata/fixture", []Build{{Name: "host"}})
	if err != nil {
		t.Fatalf("LoadGraph() error = %v", err)
	}
	const fixture = "example.com/fixture"
	want := Graph{
		Module: fixture,
		Packages: []Package{
			{
				Path: fixture + "/a",
				Dir:  "a",
				Files: []File{
					{
						Name: "a/a.go",
						Imports: []Import{
							{Path: "os", Module: "", Line: 5},
							{Path: "example.com/dep", Module: "example.com/dep", Line: 7},
							{Path: fixture + "/b", Module: fixture, Line: 8},
						},
						Symbols: []Symbol{
							{Name: "println", Line: 13},
							{Name: "os.Getenv", Line: 14},
							{Name: fixture + "/b.B", Line: 14},
							{Name: "example.com/dep.Value", Line: 14},
							{Name: "os.Stdout", Line: 24},
							{Name: "os.Stderr", Line: 26},
							{Name: "os.Stdin", Line: 27},
						},
					},
					{
						Name:    "a/a_test.go",
						Test:    true,
						Imports: []Import{{Path: "testing", Module: "", Line: 3}},
					},
					{
						Name: "a/ext_test.go",
						Test: true,
						Imports: []Import{
							{Path: "testing", Module: "", Line: 4},
							{Path: fixture + "/a", Module: fixture, Line: 6},
						},
						Symbols: []Symbol{{Name: fixture + "/a.A", Line: 10}},
					},
				},
			},
			{
				Path:  fixture + "/b",
				Dir:   "b",
				Files: []File{{Name: "b/b.go", Imports: []Import{{Path: "embed", Module: "", Line: 4}}}},
			},
			{
				Path:  fixture + "/cmd/tool",
				Dir:   "cmd/tool",
				Main:  true,
				Files: []File{{Name: "cmd/tool/main.go"}},
			},
		},
		Unread: []string{"b/gen.go", "d/d.go"},
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("LoadGraph() mismatch (-want +got):\n%s", diff)
	}
}

// TestProcessStreamBoundary checks the actual repository policy on Go source,
// including an alias of stdout and direct methods of stderr and stdin.
func TestProcessStreamBoundary(t *testing.T) {
	data, err := os.ReadFile("../../architecture/model.yaml")
	if err != nil {
		t.Fatal(err)
	}
	m, err := ParseModel(data)
	if err != nil {
		t.Fatal(err)
	}
	g, err := LoadGraph("testdata/fixture", []Build{{Name: "host"}})
	if err != nil {
		t.Fatal(err)
	}
	m.Module = g.Module
	m.Components = []Component{{ID: "fixture", Container: "library", Packages: []string{g.Module + "/a"}}}
	var got []string
	for _, finding := range CheckCode(m, "model.yaml", g) {
		if finding.Rule == "silent-libraries" && strings.Contains(finding.Message, "use of os.Std") {
			got = append(got, finding.Location)
		}
	}
	want := []string{"a/a.go:24", "a/a.go:26", "a/a.go:27"}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("process stream findings (-want +got):\n%s", diff)
	}
}

func TestLoadGraphErrors(t *testing.T) {
	tests := []struct {
		dir     string
		wantErr string
	}{
		{dir: "testdata/missing", wantErr: "build host: load the packages in testdata/missing: "},
		{dir: "testdata/broken", wantErr: "undefined: missing"},
		{dir: "testdata/empty", wantErr: "no Go package in testdata/empty"},
	}
	for _, tt := range tests {
		_, err := LoadGraph(tt.dir, []Build{{Name: "host"}})
		if err == nil || !strings.Contains(err.Error(), tt.wantErr) {
			t.Errorf("LoadGraph(%q) error = %v, want an error with %q", tt.dir, err, tt.wantErr)
		}
	}
}

func TestPackageErrors(t *testing.T) {
	// withErrors returns a package with n errors, named e1 to en.
	withErrors := func(n int) *packages.Package {
		p := &packages.Package{ID: "p"}
		for i := 1; i <= n; i++ {
			p.Errors = append(p.Errors, packages.Error{Msg: "e" + strconv.Itoa(i)})
		}
		return p
	}
	// lines returns the messages e1 to en, one on each line, as
	// packages.Error formats them without a position.
	lines := func(n int) []string {
		var l []string
		for i := 1; i <= n; i++ {
			l = append(l, "-: e"+strconv.Itoa(i))
		}
		return l
	}
	tests := []struct {
		name   string
		errors int
		want   []string
	}{
		{name: "no error", errors: 0},
		{name: "one error", errors: 1, want: lines(1)},
		{name: "ten errors", errors: 10, want: lines(10)},
		{name: "twelve errors", errors: 12, want: append(lines(10), "and 2 more errors")},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got []string
			if err := packageErrors([]*packages.Package{withErrors(tt.errors)}); err != nil {
				got = strings.Split(err.Error(), "\n")
			}
			if diff := cmp.Diff(tt.want, got); diff != "" {
				t.Errorf("packageErrors() lines mismatch (-want +got):\n%s", diff)
			}
		})
	}
}

func TestMainModule(t *testing.T) {
	mod := &packages.Module{Path: "example.com/m"}
	if got := mainModule([]*packages.Package{{ID: "p.test"}, {ID: "p", Module: mod}}); got != mod {
		t.Errorf("mainModule() = %v, want the module of the second package", got)
	}
	if got := mainModule(nil); got != nil {
		t.Errorf("mainModule(nil) = %v, want nil", got)
	}
}

// unlistable is a file system with one directory that cannot be listed.
type unlistable struct {
	fstest.MapFS

	dir string
}

func (u unlistable) ReadDir(name string) ([]fs.DirEntry, error) {
	if name == u.dir {
		return nil, fs.ErrPermission
	}
	return u.MapFS.ReadDir(name)
}

func TestUnread(t *testing.T) {
	file := &fstest.MapFile{}
	fsys := unlistable{dir: "locked", MapFS: fstest.MapFS{
		"go.mod":          file,
		"doc.go":          file,
		"a/a.go":          file,
		"a/gen.go":        file,
		"a/_a.go":         file,
		"a/.a.go":         file,
		"a/notes.txt":     file,
		"d/d.go":          file,
		"locked/l.go":     file,
		"vendor/v/v.go":   file,
		"testdata/t.go":   file,
		"_skip/s.go":      file,
		".hidden/h.go":    file,
		"nested/go.mod":   file,
		"nested/n.go":     file,
		"nested/sub/s.go": file,
	}}
	read := map[string]bool{"doc.go": true, "a/a.go": true}
	got := unread(fsys, ".", read)
	want := []string{"a/gen.go", "d/d.go", "locked"}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("unread() mismatch (-want +got):\n%s", diff)
	}
}

func TestLoadGraphWithoutBuild(t *testing.T) {
	if _, err := LoadGraph("testdata/fixture", nil); err == nil || err.Error() != "no build to load" {
		t.Errorf("LoadGraph() without a build: error = %v, want %q", err, "no build to load")
	}
}

func TestMergeGraphs(t *testing.T) {
	file := func(name string, line int) File {
		return File{Name: name, Imports: []Import{{Path: "fmt", Line: line}}}
	}
	linux := Graph{
		Module: testModule,
		Packages: []Package{
			{Path: testModule + "/b", Dir: "b", Files: []File{file("b/b.go", 3), file("b/b_linux.go", 3)}},
			{Path: testModule + "/cmd/tool", Dir: "cmd/tool", Main: true, Files: []File{file("cmd/tool/main.go", 3)}},
		},
		Unread: []string{"b/b_darwin.go", "d/d.go", "e/e_linux.go"},
	}
	darwin := Graph{
		Module: testModule,
		Packages: []Package{
			{Path: testModule + "/a", Dir: "a", Files: []File{file("a/a.go", 3)}},
			{Path: testModule + "/b", Dir: "b", Files: []File{file("b/b_darwin.go", 3), file("b/b.go", 9)}},
			{Path: testModule + "/cmd/tool", Dir: "cmd/tool", Files: []File{file("cmd/tool/tool_darwin.go", 3)}},
		},
		Unread: []string{"b/b_linux.go", "d/d.go", "e/e_linux.go"},
	}
	want := Graph{
		Module: testModule,
		Packages: []Package{
			{Path: testModule + "/a", Dir: "a", Files: []File{file("a/a.go", 3)}},
			{Path: testModule + "/b", Dir: "b", Files: []File{file("b/b.go", 3), file("b/b_darwin.go", 3), file("b/b_linux.go", 3)}},
			{Path: testModule + "/cmd/tool", Dir: "cmd/tool", Main: true, Files: []File{file("cmd/tool/main.go", 3), file("cmd/tool/tool_darwin.go", 3)}},
		},
		Unread: []string{"d/d.go", "e/e_linux.go"},
	}
	if diff := cmp.Diff(want, mergeGraphs([]Graph{linux, darwin})); diff != "" {
		t.Errorf("mergeGraphs() mismatch (-want +got):\n%s", diff)
	}
}

// TestBuildGraphSkipsFilesOutsideTheModule checks that a file outside the
// module root, such as a generated file in the build cache, does not stop the
// files of the package after it.
func TestBuildGraphSkipsFilesOutsideTheModule(t *testing.T) {
	dir := t.TempDir()
	fset := token.NewFileSet()
	var files []*ast.File
	for _, name := range []string{"/elsewhere/gen.go", filepath.Join(dir, "a", "a.go")} {
		f, err := parser.ParseFile(fset, name, "package a\n", 0)
		if err != nil {
			t.Fatalf("parse %s: %v", name, err)
		}
		files = append(files, f)
	}
	p := &packages.Package{
		PkgPath:   testModule + "/a",
		Name:      "a",
		Fset:      fset,
		Syntax:    files,
		Types:     types.NewPackage(testModule+"/a", "a"),
		TypesInfo: &types.Info{Uses: map[*ast.Ident]types.Object{}},
	}
	got := buildGraph(&packages.Module{Path: testModule, Dir: dir}, []*packages.Package{p}, nil)
	want := Graph{
		Module:   testModule,
		Packages: []Package{{Path: testModule + "/a", Dir: "a", Files: []File{{Name: "a/a.go"}}}},
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("buildGraph() mismatch (-want +got):\n%s", diff)
	}
}
