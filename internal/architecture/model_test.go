package architecture

import (
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

const testModule = "example.com/repo"

// validModel returns a small model with no defects. Each call returns a new
// value, so a test can change it.
func validModel() *Model {
	return &Model{
		Version: 1,
		Module:  testModule,
		System:  Element{ID: "system", Name: "System", Description: "The system."},
		People:  []Element{{ID: "author", Name: "Author", Description: "Writes packs."}},
		ExternalSystems: []Element{
			{ID: "upstream", Name: "Upstream", Description: "An external system."},
		},
		Relationships: []Relationship{
			{From: "author", To: "system", Description: "Uses"},
			{From: "system", To: "upstream", Description: "Calls"},
		},
		Containers: []Container{
			{ID: "library", Name: "Library", Technology: "Go", Description: "The library."},
			{ID: "tools", Name: "Tools", Technology: "Go", Description: "The tools."},
		},
		Components: []Component{
			{
				ID: "core", Container: "library", Description: "The core.",
				Packages: []string{testModule + "/internal/core"},
			},
			{
				ID: "feature", Container: "library", Description: "A feature.",
				Packages:  []string{testModule + "/internal/feature"},
				DependsOn: []string{"core"},
				Modules:   []string{"golang.org/x/text"},
			},
		},
		TestModules: []string{"github.com/google/go-cmp"},
		Rules: []Rule{{
			ID:            "quiet",
			Description:   "Libraries do not print.",
			Scope:         RuleScope{Containers: []string{"library"}},
			ForbidImports: []string{"log", "net/http/..."},
			ForbidSymbols: []string{"fmt.Println", "println"},
			Fix:           "Return the value.",
		}},
	}
}

func TestParseModel(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    *Model
		wantErr string
	}{
		{
			name:  "valid",
			input: "version: 1\nmodule: example.com/repo\nsystem:\n  id: system\n  name: System\n",
			want:  &Model{Version: 1, Module: testModule, System: Element{ID: "system", Name: "System"}},
		},
		{
			name:    "unknown field",
			input:   "version: 1\nmodul: example.com/repo\n",
			wantErr: "field modul not found",
		},
		{
			name:    "two documents",
			input:   "version: 1\n---\nversion: 2\n",
			wantErr: "more than one YAML document",
		},
		{
			name:    "invalid YAML",
			input:   "version: [1\n",
			wantErr: "decode model",
		},
		{
			name:    "empty",
			input:   "",
			wantErr: "decode model: EOF",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseModel([]byte(tt.input))
			checkParse(t, "ParseModel", tt.input, got, err, tt.want, tt.wantErr)
		})
	}
}

// checkParse checks the result of a parse function for one input. When
// wantErr is not empty, the error must contain it.
func checkParse[T any](t *testing.T, function, input string, got T, err error, want T, wantErr string) {
	t.Helper()
	if wantErr != "" {
		if err == nil || !strings.Contains(err.Error(), wantErr) {
			t.Fatalf("%s(%q) error = %v, want an error with %q", function, input, err, wantErr)
		}
		return
	}
	if err != nil {
		t.Fatalf("%s(%q) error = %v, want nil", function, input, err)
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("%s(%q) mismatch (-want +got):\n%s", function, input, diff)
	}
}

func TestValidateModel(t *testing.T) {
	tests := []struct {
		name   string
		change func(m *Model)
		want   []string
	}{
		{name: "valid model", change: func(*Model) {}},
		{
			name:   "version",
			change: func(m *Model) { m.Version = 2 },
			want:   []string{"version is 2; the only supported version is 1"},
		},
		{
			name:   "module path",
			change: func(m *Model) { m.Module = "repo" },
			want: []string{
				`module "repo" is not a valid module path`,
				`package "example.com/repo/internal/core" of component "core" is outside module "repo"`,
				`package "example.com/repo/internal/feature" of component "feature" is outside module "repo"`,
			},
		},
		{
			name:   "system name",
			change: func(m *Model) { m.System.Name = "" },
			want:   []string{"the system has no name"},
		},
		{
			name:   "identifier format",
			change: func(m *Model) { m.People[0].ID = "Author" },
			want: []string{
				`person identifier "Author" must be lowercase words joined by hyphens`,
				`relationship "author" -> "system" must connect the system, people, or external systems`,
			},
		},
		{
			name:   "duplicate identifier",
			change: func(m *Model) { m.Containers[1].ID = "core" },
			want: []string{
				`identifier "core" is used more than once`,
			},
		},
		{
			name:   "duplicate rule",
			change: func(m *Model) { m.Rules = append(m.Rules, m.Rules[0]) },
			want:   []string{`rule identifier "quiet" is not valid or is used more than once`},
		},
		{
			name:   "invalid rule identifier",
			change: func(m *Model) { m.Rules[0].ID = "Quiet" },
			want:   []string{`rule identifier "Quiet" is not valid or is used more than once`},
		},
		{
			name:   "relationship",
			change: func(m *Model) { m.Relationships[0].To = "core" },
			want:   []string{`relationship "author" -> "core" must connect the system, people, or external systems`},
		},
		{
			name:   "relationship source",
			change: func(m *Model) { m.Relationships[0].From = "nobody" },
			want:   []string{`relationship "nobody" -> "system" must connect the system, people, or external systems`},
		},
		{
			name:   "component container",
			change: func(m *Model) { m.Components[0].Container = "missing" },
			want:   []string{`component "core" names unknown container "missing"`},
		},
		{
			name:   "component description",
			change: func(m *Model) { m.Components[0].Description = "" },
			want:   []string{`component "core" has no description`},
		},
		{
			name:   "package outside module",
			change: func(m *Model) { m.Components[0].Packages = []string{"example.com/repository/x"} },
			want:   []string{`package "example.com/repository/x" of component "core" is outside module "example.com/repo"`},
		},
		{
			name:   "module root package",
			change: func(m *Model) { m.Components[0].Packages = []string{testModule} },
		},
		{
			name:   "package with two owners",
			change: func(m *Model) { m.Components[1].Packages = m.Components[0].Packages },
			want:   []string{`package "example.com/repo/internal/core" has two owners: "core" and "feature"`},
		},
		{
			name:   "unknown dependency",
			change: func(m *Model) { m.Components[1].DependsOn = []string{"missing"} },
			want:   []string{`component "feature" depends on unknown component "missing"`},
		},
		{
			name:   "self dependency",
			change: func(m *Model) { m.Components[1].DependsOn = []string{"feature"} },
			want: []string{
				`component "feature" depends on itself`,
				`the dependencies of component "feature" form a cycle`,
			},
		},
		{
			name:   "duplicate dependency",
			change: func(m *Model) { m.Components[1].DependsOn = []string{"core", "core"} },
			want:   []string{`component "feature" lists dependency "core" more than once`},
		},
		{
			name:   "cycle",
			change: func(m *Model) { m.Components[0].DependsOn = []string{"feature"} },
			want:   []string{`the dependencies of component "core" form a cycle`},
		},
		{
			name:   "invalid module",
			change: func(m *Model) { m.Components[1].Modules = []string{"text"} },
			want:   []string{`module of component "feature" "text" is not a valid module path or is listed more than once`},
		},
		{
			name:   "duplicate test module",
			change: func(m *Model) { m.TestModules = append(m.TestModules, m.TestModules[0]) },
			want:   []string{`test module "github.com/google/go-cmp" is not a valid module path or is listed more than once`},
		},
		{
			name:   "rule without containers",
			change: func(m *Model) { m.Rules[0].Scope.Containers = nil },
			want:   []string{`rule "quiet" applies to no container`},
		},
		{
			name:   "rule with unknown container",
			change: func(m *Model) { m.Rules[0].Scope.Containers = []string{"missing"} },
			want:   []string{`rule "quiet" names unknown container "missing"`},
		},
		{
			name:   "rule with unknown exception",
			change: func(m *Model) { m.Rules[0].ExceptComponents = []string{"missing"} },
			want:   []string{`rule "quiet" names unknown component "missing"`},
		},
		{
			name: "rule that forbids nothing",
			change: func(m *Model) {
				m.Rules[0].ForbidImports = nil
				m.Rules[0].ForbidSymbols = nil
			},
			want: []string{`rule "quiet" forbids nothing`},
		},
		{
			name:   "invalid import pattern",
			change: func(m *Model) { m.Rules[0].ForbidImports = []string{"net/.../http"} },
			want:   []string{`rule "quiet" has invalid import pattern "net/.../http"`},
		},
		{
			name:   "invalid symbol",
			change: func(m *Model) { m.Rules[0].ForbidSymbols = []string{"fmt.println"} },
			want:   []string{`rule "quiet" has invalid symbol "fmt.println"`},
		},
		{
			name:   "rule without fix",
			change: func(m *Model) { m.Rules[0].Fix = "" },
			want:   []string{`rule "quiet" needs a description and a fix`},
		},
		{
			name:   "rule without description",
			change: func(m *Model) { m.Rules[0].Description = "" },
			want:   []string{`rule "quiet" needs a description and a fix`},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := validModel()
			tt.change(m)
			got := messages(t, ValidateModel(m, "model.yaml"), "model.yaml", RuleModel)
			if diff := cmp.Diff(tt.want, got); diff != "" {
				t.Errorf("ValidateModel() messages mismatch (-want +got):\n%s", diff)
			}
		})
	}
}

// messages returns the messages of the findings, and checks that each finding
// has the given location and rule and a fix.
func messages(t *testing.T, findings []Finding, location, rule string) []string {
	t.Helper()
	var got []string
	for _, f := range findings {
		if f.Location != location || f.Rule != rule || f.Fix == "" {
			t.Errorf("finding %+v, want location %q, rule %q, and a fix", f, location, rule)
		}
		got = append(got, f.Message)
	}
	return got
}

func TestModelOwnersAndComponent(t *testing.T) {
	m := validModel()
	owners := m.Owners()
	if got := owners[testModule+"/internal/feature"].ID; got != "feature" {
		t.Errorf("Owners()[feature package].ID = %q, want %q", got, "feature")
	}
	if len(owners) != 2 {
		t.Errorf("len(Owners()) = %d, want 2", len(owners))
	}
	if c, ok := m.Component("core"); !ok || c.Container != "library" {
		t.Errorf("Component(%q) = %+v, %v, want the core component", "core", c, ok)
	}
	if c, ok := m.Component("missing"); ok || c != nil {
		t.Errorf("Component(%q) = %+v, %v, want nil, false", "missing", c, ok)
	}
}

func TestValidID(t *testing.T) {
	tests := map[string]bool{
		"a": true, "pack-fs": true, "a1-b2": true, "": false, "1a": false, "A": false,
		"a-": false, "a--b": false, "a_b": false, "-a": false, "a.b": false,
	}
	for id, want := range tests {
		if got := validID(id); got != want {
			t.Errorf("validID(%q) = %v, want %v", id, got, want)
		}
	}
}

func TestValidModulePath(t *testing.T) {
	tests := map[string]bool{
		"example.com/repo": true, "golang.org/x/tools": true, "go.yaml.in/yaml/v3": true,
		"": false, "repo": false, "repo/x.y": false, "example.com/a b": false, `example.com\a`: false,
	}
	for path, want := range tests {
		if got := validModulePath(path); got != want {
			t.Errorf("validModulePath(%q) = %v, want %v", path, got, want)
		}
	}
}

func TestValidImportPattern(t *testing.T) {
	tests := map[string]bool{
		"log": true, "net/http/...": true, "golang.org/x/tools/...": true,
		"": false, "/...": false, "net/../http": false, "a b": false,
	}
	for pattern, want := range tests {
		if got := validImportPattern(pattern); got != want {
			t.Errorf("validImportPattern(%q) = %v, want %v", pattern, got, want)
		}
	}
}

func TestValidSymbol(t *testing.T) {
	tests := map[string]bool{
		"println": true, "panic": true, "os.Getenv": true, "path/filepath.Walk": true,
		"golang.org/x/tools/go/packages.Load": true,
		"printf":                              false, "os.getenv": false, ".Getenv": false, "os.": false, "os.Get env": false,
	}
	for symbol, want := range tests {
		if got := validSymbol(symbol); got != want {
			t.Errorf("validSymbol(%q) = %v, want %v", symbol, got, want)
		}
	}
}
