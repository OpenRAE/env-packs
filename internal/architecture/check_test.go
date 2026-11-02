package architecture

import (
	"testing"

	"github.com/OpenRAE/env-packs/internal/report"
	"github.com/google/go-cmp/cmp"
)

// pkg returns a package of the test module with one file.
func pkg(dir string, main bool, file File) Package {
	return Package{Path: testModule + "/" + dir, Dir: dir, Main: main, Files: []File{file}}
}

func TestCheckCode(t *testing.T) {
	core := testModule + "/internal/core"
	tests := []struct {
		name   string
		change func(m *Model)
		graph  Graph
		want   []report.Finding
	}{
		{
			name: "clean code",
			graph: Graph{Module: testModule, Packages: []Package{
				pkg("internal/core", false, File{Name: "internal/core/core.go", Imports: []Import{{Path: "fmt", Line: 3}}}),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go", Imports: []Import{
					{Path: core, Module: testModule, Line: 4},
					{Path: "golang.org/x/text/language", Module: "golang.org/x/text", Line: 5},
				}}),
			}},
		},
		{
			name: "module mismatch, unowned package, and unknown package",
			graph: Graph{Module: "example.com/other", Packages: []Package{
				pkg("internal/core", false, File{Name: "internal/core/core.go"}),
				{Path: testModule + "/internal/stray", Dir: "internal/stray"},
			}},
			want: []report.Finding{
				{
					Location: "internal/stray", Rule: RulePackageOwner,
					Message: `package "example.com/repo/internal/stray" has no component`,
					Fix:     "Add the package to the packages of a component in architecture/model.yaml, in a design step (docs/development/designs/README.md).",
				},
				{
					Location: "model.yaml", Rule: RuleModel,
					Message: `the model describes module "example.com/repo", but the code is module "example.com/other"`,
					Fix:     "Set the module of the model to the module path in go.mod, in a design step.",
				},
				{
					Location: "model.yaml", Rule: RuleUnknownPackage,
					Message: `component "feature" owns package "example.com/repo/internal/feature", but the code has no such package`,
					Fix:     "Write the package, or remove it from the model in a design step.",
				},
			},
		},
		{
			name: "unowned package with files before an owned package",
			graph: Graph{Module: testModule, Packages: []Package{
				{Path: testModule + "/internal/aaa", Dir: "internal/aaa", Files: []File{{Name: "internal/aaa/a.go"}}},
				pkg("internal/core", false, File{Name: "internal/core/core.go", Symbols: []Symbol{{Name: "println", Line: 2}}}),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go"}),
			}},
			want: []report.Finding{
				{
					Location: "internal/aaa", Rule: RulePackageOwner,
					Message: `package "example.com/repo/internal/aaa" has no component`,
					Fix:     "Add the package to the packages of a component in architecture/model.yaml, in a design step (docs/development/designs/README.md).",
				},
				quietFinding("internal/core/core.go:2", "use of println"),
			},
		},
		{
			name: "unread paths",
			graph: Graph{
				Module: testModule,
				Packages: []Package{
					pkg("internal/core", false, File{Name: "internal/core/core.go"}),
					pkg("internal/feature", false, File{Name: "internal/feature/f.go"}),
				},
				Unread: []string{"internal/core/gen.go", "locked"},
			},
			want: []report.Finding{unreadFinding("internal/core/gen.go"), unreadFinding("locked")},
		},
		{
			name: "import inside one component",
			change: func(m *Model) {
				m.Components[0].Packages = append(m.Components[0].Packages, testModule+"/internal/core/sub")
			},
			graph: Graph{Module: testModule, Packages: []Package{
				pkg("internal/core", false, File{Name: "internal/core/core.go", Imports: []Import{
					{Path: testModule + "/internal/core/sub", Module: testModule, Line: 3},
				}}),
				pkg("internal/core/sub", false, File{Name: "internal/core/sub/sub.go"}),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go"}),
			}},
		},
		{
			name: "dependency of a component with one permitted dependency",
			change: func(m *Model) {
				m.Components = append(m.Components, Component{
					ID: "extra", Container: "library", Description: "Extra.",
					Packages: []string{testModule + "/internal/extra"},
				})
			},
			graph: Graph{Module: testModule, Packages: []Package{
				pkg("internal/core", false, File{Name: "internal/core/core.go"}),
				pkg("internal/extra", false, File{Name: "internal/extra/e.go"}),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go", Imports: []Import{
					{Path: testModule + "/internal/extra", Module: testModule, Line: 5},
				}}),
			}},
			want: []report.Finding{{
				Location: "internal/feature/f.go:5", Rule: RuleComponentDependency,
				Message: `component "feature" imports "example.com/repo/internal/extra" of component "extra", but the model does not permit this dependency`,
				Fix:     `Use a component that "feature" may depend on (core), or add the dependency "feature" -> "extra" to the model in a design step.`,
			}},
		},
		{
			name: "import of a package without an owner",
			graph: Graph{Module: testModule, Packages: []Package{
				pkg("internal/core", false, File{Name: "internal/core/core.go", Imports: []Import{
					{Path: testModule + "/internal/stray", Module: testModule, Line: 6},
				}}),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go"}),
				{Path: testModule + "/internal/stray", Dir: "internal/stray"},
			}},
			want: []report.Finding{{
				Location: "internal/stray", Rule: RulePackageOwner,
				Message: `package "example.com/repo/internal/stray" has no component`,
				Fix:     "Add the package to the packages of a component in architecture/model.yaml, in a design step (docs/development/designs/README.md).",
			}},
		},
		{
			name: "dependency that the model does not permit",
			graph: Graph{Module: testModule, Packages: []Package{
				pkg("internal/core", false, File{Name: "internal/core/core.go", Imports: []Import{
					{Path: testModule + "/internal/feature", Module: testModule, Line: 7},
				}}),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go"}),
			}},
			want: []report.Finding{{
				Location: "internal/core/core.go:7", Rule: RuleComponentDependency,
				Message: `component "core" imports "example.com/repo/internal/feature" of component "feature", but the model does not permit this dependency`,
				Fix:     `Use a component that "core" may depend on (no other component), or add the dependency "core" -> "feature" to the model in a design step.`,
			}},
		},
		{
			name: "external modules",
			graph: Graph{Module: testModule, Packages: []Package{
				{Path: core, Dir: "internal/core", Files: []File{
					{Name: "internal/core/core.go", Imports: []Import{{Path: "golang.org/x/text/language", Module: "golang.org/x/text", Line: 2}}},
					{Name: "internal/core/core_test.go", Test: true, Imports: []Import{
						{Path: "github.com/google/go-cmp/cmp", Module: "github.com/google/go-cmp", Line: 3},
						{Path: "example.com/mock", Module: "example.com/mock", Line: 4},
					}},
				}},
				pkg("internal/feature", false, File{Name: "internal/feature/f.go", Imports: []Import{
					{Path: "github.com/google/go-cmp/cmp", Module: "github.com/google/go-cmp", Line: 9},
				}}),
			}},
			want: []report.Finding{
				{
					Location: "internal/core/core.go:2", Rule: RuleExternalModule,
					Message: `component "core" imports "golang.org/x/text/language" from module "golang.org/x/text", but the model does not permit this module`,
					Fix:     `Add module "golang.org/x/text" to the modules of component "core" in a design step, and give the reason in the design record.`,
				},
				{
					Location: "internal/core/core_test.go:4", Rule: RuleExternalModule,
					Message: `component "core" imports "example.com/mock" from module "example.com/mock", but the model does not permit this module`,
					Fix:     `Add module "example.com/mock" to the test modules or to the modules of component "core" in a design step, and give the reason in the design record.`,
				},
				{
					Location: "internal/feature/f.go:9", Rule: RuleExternalModule,
					Message: `component "feature" imports "github.com/google/go-cmp/cmp" from module "github.com/google/go-cmp", but the model does not permit this module`,
					Fix:     `Add module "github.com/google/go-cmp" to the modules of component "feature" in a design step, and give the reason in the design record.`,
				},
			},
		},
		{
			name: "forbidden import and symbols",
			graph: Graph{Module: testModule, Packages: []Package{
				pkg("internal/core", false, File{
					Name: "internal/core/core.go",
					Imports: []Import{
						{Path: "log", Line: 3},
						{Path: "net/http/httptest", Line: 4},
						{Path: "net/httpx", Line: 5},
					},
					Symbols: []Symbol{{Name: "fmt.Println", Line: 8}, {Name: "fmt.Sprintf", Line: 9}, {Name: "println", Line: 10}},
				}),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go"}),
			}},
			want: []report.Finding{
				quietFinding("internal/core/core.go:10", "use of println"),
				quietFinding("internal/core/core.go:3", `import of "log"`),
				quietFinding("internal/core/core.go:4", `import of "net/http/httptest"`),
				quietFinding("internal/core/core.go:8", "use of fmt.Println"),
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := validModel()
			if tt.change != nil {
				tt.change(m)
			}
			got := report.Sort(CheckCode(m, "model.yaml", tt.graph))
			if diff := cmp.Diff(tt.want, got); diff != "" {
				t.Errorf("CheckCode() mismatch (-want +got):\n%s", diff)
			}
		})
	}
}

func unreadFinding(location string) report.Finding {
	return report.Finding{
		Location: location,
		Rule:     RuleUnreadPath,
		Message:  "the check cannot read this path, so the rules of the model do not apply to it",
		Fix:      "Remove the build constraint or the cgo code, or make the directory readable. If the code needs them, change tools/archcheck in a design step so that the check reads the path.",
	}
}

func quietFinding(location, what string) report.Finding {
	return report.Finding{
		Location: location,
		Rule:     "quiet",
		Message:  what + ` in component "core" breaks the rule: Libraries do not print.`,
		Fix:      "Return the value.",
	}
}

func TestCheckCodeRuleScope(t *testing.T) {
	fileWith := func(name string, test bool) File {
		return File{Name: name, Test: test, Symbols: []Symbol{{Name: "fmt.Println", Line: 1}}}
	}
	tests := []struct {
		name    string
		scope   RuleScope
		except  []string
		main    bool
		test    bool
		flagged bool
	}{
		{name: "library file", scope: RuleScope{Containers: []string{"library"}}, flagged: true},
		{name: "other container", scope: RuleScope{Containers: []string{"tools"}}},
		{name: "excepted component", scope: RuleScope{Containers: []string{"library"}}, except: []string{"core"}},
		{name: "main package", scope: RuleScope{Containers: []string{"library"}}, main: true},
		{name: "main package in scope", scope: RuleScope{Containers: []string{"library"}, MainPackages: true}, main: true, flagged: true},
		{name: "test file", scope: RuleScope{Containers: []string{"library"}}, test: true},
		{name: "test file in scope", scope: RuleScope{Containers: []string{"library"}, TestFiles: true}, test: true, flagged: true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := validModel()
			m.Rules[0].Scope = tt.scope
			m.Rules[0].ExceptComponents = tt.except
			g := Graph{Module: testModule, Packages: []Package{
				pkg("internal/core", tt.main, fileWith("internal/core/core.go", tt.test)),
				pkg("internal/feature", false, File{Name: "internal/feature/f.go"}),
			}}
			got := len(CheckCode(m, "model.yaml", g)) > 0
			if got != tt.flagged {
				t.Errorf("CheckCode() flagged = %v, want %v", got, tt.flagged)
			}
		})
	}
}

func TestMatchImport(t *testing.T) {
	tests := []struct {
		pattern, path string
		want          bool
	}{
		{"log", "log", true},
		{"log", "log/slog", false},
		{"net/http/...", "net/http", true},
		{"net/http/...", "net/http/httptest", true},
		{"net/http/...", "net/httptest", false},
		{"net/http/...", "net", false},
	}
	for _, tt := range tests {
		if got := matchImport(tt.pattern, tt.path); got != tt.want {
			t.Errorf("matchImport(%q, %q) = %v, want %v", tt.pattern, tt.path, got, tt.want)
		}
	}
}
