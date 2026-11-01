package architecture

import (
	"io/fs"
	"strconv"
	"testing"
	"testing/fstest"

	"github.com/OpenRAE/env-packs/internal/report"
	"github.com/google/go-cmp/cmp"
)

// designsFor returns one design record that adds the structure of
// validModel.
func designsFor() []Design {
	return []Design{{
		Path:   "designs/0001-start.md",
		Number: 1,
		Issue:  1,
		Title:  "Start",
		Changes: Changes{
			Containers: Change[string]{Add: []string{"library", "tools"}},
			Components: Change[ComponentRef]{Add: []ComponentRef{
				{ID: "core", Container: "library"},
				{ID: "feature", Container: "library"},
			}},
			Packages: Change[PackageRef]{Add: []PackageRef{
				{Path: testModule + "/internal/core", Component: "core"},
				{Path: testModule + "/internal/feature", Component: "feature"},
			}},
			Dependencies: Change[DependencyRef]{Add: []DependencyRef{{From: "feature", To: "core"}}},
			Modules:      Change[ModuleRef]{Add: []ModuleRef{{Component: "feature", Module: "golang.org/x/text"}}},
			TestModules:  Change[string]{Add: []string{"github.com/google/go-cmp"}},
			Rules:        Change[string]{Add: []string{"quiet"}},
		},
	}}
}

func TestParseDesign(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    Design
		wantErr string
	}{
		{
			name:  "valid",
			input: "---\ndesign: 2\nissue: 9\ntitle: T\nchanges:\n  rules:\n    remove: [quiet]\n---\n\n# Body\n",
			want: Design{Number: 2, Issue: 9, Title: "T", Changes: Changes{
				Rules: Change[string]{Remove: []string{"quiet"}},
			}},
		},
		{name: "no front matter", input: "# Title\n", wantErr: "has no YAML front matter at the first line"},
		{name: "no end line", input: "---\ndesign: 1\n", wantErr: "has no line that ends the YAML front matter"},
		{name: "unknown field", input: "---\ndesign: 1\nissues: 2\n---\n", wantErr: "field issues not found"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseDesign([]byte(tt.input))
			checkParse(t, "ParseDesign", tt.input, got, err, tt.want, tt.wantErr)
		})
	}
}

func TestLoadDesigns(t *testing.T) {
	record := func(number, issue int, title string) *fstest.MapFile {
		return &fstest.MapFile{Data: []byte("---\ndesign: " + strconv.Itoa(number) + "\nissue: " + strconv.Itoa(issue) + "\ntitle: " + title + "\n---\n")}
	}
	fsys := fstest.MapFS{
		"designs/README.md":           {Data: []byte("# Records\n")},
		"designs/0002-second.md":      record(2, 7, "Second"),
		"designs/0001-first.md":       record(1, 1, "First"),
		"designs/0003-numbers.md":     record(4, 8, "Wrong number"),
		"designs/0004-no-issue.md":    {Data: []byte("---\ndesign: 4\ntitle: No issue\n---\n")},
		"designs/0005-no-title.md":    {Data: []byte("---\ndesign: 5\nissue: 9\n---\n")},
		"designs/0006-broken.md":      {Data: []byte("no front matter\n")},
		"designs/notes.md":            {Data: []byte("x")},
		"designs/0007-Upper.md":       record(7, 1, "Upper"),
		"designs/0008-directory.md/x": {Data: []byte("x")},
		"designs/0009-negative.md":    record(-9, 2, "Negative"),
	}
	designs, findings, err := LoadDesigns(fsys, "designs")
	if err != nil {
		t.Fatalf("LoadDesigns() error = %v", err)
	}
	var numbers []int
	for _, d := range designs {
		numbers = append(numbers, d.Number)
	}
	if diff := cmp.Diff([]int{-9, 1, 2, 4, 4, 5}, numbers); diff != "" {
		t.Errorf("LoadDesigns() numbers mismatch (-want +got):\n%s", diff)
	}
	if first := designs[1]; first.Path != "designs/0001-first.md" || first.Title != "First" || first.Issue != 1 {
		t.Errorf("LoadDesigns() record 1 = %+v, want the parsed first record", first)
	}
	want := []report.Finding{
		designFinding("designs/0003-numbers.md", "has design number 4, but its file name does not start with 0004-"),
		designFinding("designs/0004-no-issue.md", "names no GitHub issue"),
		designFinding("designs/0005-no-title.md", "has no title"),
		designFinding("designs/0006-broken.md", "has no YAML front matter at the first line"),
		designFinding("designs/0007-Upper.md", "is not a design record file named NNNN-slug.md"),
		designFinding("designs/0008-directory.md", "is not a design record file named NNNN-slug.md"),
		designFinding("designs/0009-negative.md", "has design number -9, but its file name does not start with -009-"),
		designFinding("designs/notes.md", "is not a design record file named NNNN-slug.md"),
	}
	if diff := cmp.Diff(want, report.Sort(findings)); diff != "" {
		t.Errorf("LoadDesigns() findings mismatch (-want +got):\n%s", diff)
	}
}

func TestLoadDesignsMissingDirectory(t *testing.T) {
	if _, _, err := LoadDesigns(fstest.MapFS{}, "designs"); err == nil {
		t.Error("LoadDesigns() of a missing directory: error = nil, want an error")
	}
}

// unreadable is a file system that lists its files but cannot read them.
type unreadable struct{ fstest.MapFS }

func (unreadable) ReadFile(string) ([]byte, error) { return nil, fs.ErrPermission }

func TestLoadDesignsUnreadableRecord(t *testing.T) {
	fsys := unreadable{fstest.MapFS{"designs/0001-a.md": {Data: []byte("---\n")}}}
	if _, _, err := LoadDesigns(fsys, "designs"); err == nil {
		t.Error("LoadDesigns() of an unreadable record: error = nil, want an error")
	}
}

func TestDesignName(t *testing.T) {
	tests := map[string]bool{
		"0001-a.md": true, "0042-pack-fs.md": true, "0000-zero.md": true, "9999-z9.md": true,
		"1-a.md": false, "00001-a.md": false, "0001-.md": false, "0001_a.md": false, "0001-a": false,
		"0001-a.txt": false, "00a1-a.md": false, "+001-a.md": false, "0001-A.md": false,
	}
	for name, want := range tests {
		if got := designName.MatchString(name); got != want {
			t.Errorf("designName.MatchString(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestCheckDesigns(t *testing.T) {
	tests := []struct {
		name    string
		model   func(m *Model)
		designs func(d []Design) []Design
		want    []string
	}{
		{name: "records match the model"},
		{
			name:  "model element without a record",
			model: func(m *Model) { m.TestModules = append(m.TestModules, "example.com/extra") },
			want:  []string{`the model has test module "example.com/extra", but no design record adds it`},
		},
		{
			name: "model component, package, and module without a record",
			model: func(m *Model) {
				m.Components = append(m.Components, Component{
					ID: "extra", Container: "tools", Description: "Extra.",
					Packages: []string{testModule + "/internal/extra"},
					Modules:  []string{"example.com/lib"},
				})
			},
			want: []string{
				`the model has component "extra" in container "tools", but no design record adds it`,
				`the model has package "example.com/repo/internal/extra" of component "extra", but no design record adds it`,
				`the model has module "example.com/lib" of component "extra", but no design record adds it`,
			},
		},
		{
			name:  "record element missing from the model",
			model: func(m *Model) { m.Components[1].DependsOn = nil },
			want:  []string{`the design records add dependency "feature" -> "core", but the model does not have it`},
		},
		{
			name: "record adds an element twice",
			designs: func(d []Design) []Design {
				second := Design{Path: "designs/0002-again.md", Number: 2, Issue: 2, Title: "Again",
					Changes: Changes{Rules: Change[string]{Add: []string{"quiet"}}}}
				return append(d, second)
			},
			want: []string{`the design record adds rule "quiet", which already exists at that point`},
		},
		{
			name: "record removes a missing element",
			designs: func(d []Design) []Design {
				second := Design{Path: "designs/0002-remove.md", Number: 2, Issue: 2, Title: "Remove",
					Changes: Changes{Containers: Change[string]{Remove: []string{"missing"}}}}
				return append(d, second)
			},
			want: []string{`the design record removes container "missing", which does not exist at that point`},
		},
		{
			name: "record moves a package",
			model: func(m *Model) {
				m.Components[0].Packages = append(m.Components[0].Packages, testModule+"/internal/feature")
				m.Components[1].Packages = nil
			},
			designs: func(d []Design) []Design {
				move := Design{Path: "designs/0002-move.md", Number: 2, Issue: 2, Title: "Move",
					Changes: Changes{Packages: Change[PackageRef]{
						Remove: []PackageRef{{Path: testModule + "/internal/feature", Component: "feature"}},
						Add:    []PackageRef{{Path: testModule + "/internal/feature", Component: "core"}},
					}}}
				return append(d, move)
			},
		},
		{
			name: "gap in the numbers",
			designs: func(d []Design) []Design {
				d[0].Number = 2
				return d
			},
			want: []string{"the design record has number 2, but the records must be numbered from 1 with no gap, and this is record 1"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := validModel()
			if tt.model != nil {
				tt.model(m)
			}
			designs := designsFor()
			if tt.designs != nil {
				designs = tt.designs(designs)
			}
			got := designMessages(t, CheckDesigns(m, "model.yaml", designs))
			if diff := cmp.Diff(tt.want, got); diff != "" {
				t.Errorf("CheckDesigns() messages mismatch (-want +got):\n%s", diff)
			}
		})
	}
}

// designMessages returns the messages of design findings, and checks that each
// finding has the design rule and a fix.
func designMessages(t *testing.T, findings []report.Finding) []string {
	t.Helper()
	var got []string
	for _, f := range findings {
		if f.Rule != RuleDesign || f.Fix == "" {
			t.Errorf("finding %+v, want rule %q and a fix", f, RuleDesign)
		}
		got = append(got, f.Message)
	}
	return got
}
