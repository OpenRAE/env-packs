package issueskeleton

import (
	"bufio"
	"slices"
	"strings"
	"testing"
	"testing/fstest"
)

func TestValidateRepo(t *testing.T) {
	tests := map[string]string{
		"o/r":           "",
		"Org.1/re_po-2": "",
		"": "--repo OWNER/REPOSITORY is required: name the catalog repository that will own the pack " +
			"(e.g. example-org/example-packs).",
		"https://github.com/o/r": "--repo must be a GitHub OWNER/REPOSITORY slug using letters, digits, '.', '_', " +
			"and '-'; got 'https://github.com/o/r'",
		"o/r\x1b": `--repo must be a GitHub OWNER/REPOSITORY slug using letters, digits, '.', '_', and '-'; got 'o/r\x1b'`,
	}
	for repo, want := range tests {
		got := ""
		if err := ValidateRepo(repo); err != nil {
			got = err.Error()
		}
		if got != want {
			t.Errorf("ValidateRepo(%q) = %q, want %q", repo, got, want)
		}
	}
}

func TestValidatePackID(t *testing.T) {
	for id, ok := range map[string]bool{"demo": true, "a--b": true, "x9": true, "Demo": false, "-a": false, "a": false} {
		if err := ValidatePackID(id); (err == nil) != ok {
			t.Errorf("ValidatePackID(%q) = %v, want ok %v", id, err, ok)
		}
	}
}

func TestTitleFromPackID(t *testing.T) {
	for id, want := range map[string]string{"example-pack": "Example Pack", "a--b": "A  B", "x9-1z": "X9 1z"} {
		if got := TitleFromPackID(id); got != want {
			t.Errorf("TitleFromPackID(%q) = %q, want %q", id, got, want)
		}
	}
}

func TestPackRootForRepo(t *testing.T) {
	for repo, want := range map[string]string{"OpenRAE/env-packs": "packs", "openrae/ENV-PACKS": "packs", "o/r": "environments"} {
		if got := PackRootForRepo(repo); got != want {
			t.Errorf("PackRootForRepo(%q) = %q, want %q", repo, got, want)
		}
	}
}

func TestMilestoneTitle(t *testing.T) {
	plan := testPlan()
	if got := MilestoneTitle(plan); got != "Environment pack: Example Pack" {
		t.Errorf("MilestoneTitle() = %q", got)
	}
	plan.MilestoneTitle = "Own"
	if got := MilestoneTitle(plan); got != "Own" {
		t.Errorf("MilestoneTitle() with a title = %q", got)
	}
}

func TestBuildOperations(t *testing.T) {
	tmpl := loadTestTemplates(t)
	plan := testPlan()
	issues := []Issue{
		{Number: 3, Title: "example-pack: define hidden path, oracle, and validation model", Milestone: &struct {
			Number int `json:"number"`
		}{Number: 42}},
		{Number: 4, Title: "example-pack: add delivery profile bundles"},
	}
	available := map[string]bool{"tier:raes": true, "scenario:example-pack": true, "documentation": true}
	operations, err := tmpl.BuildOperations(plan, issues, available, false, false)
	if err != nil || len(operations) != 10 {
		t.Fatalf("BuildOperations() = %d operations, %v; want 10", len(operations), err)
	}
	if op := operations[0]; op.Action != actionCreateMilestone || op.Title != "Environment pack: Example Pack" {
		t.Errorf("first operation = %+v, want a new milestone", op)
	}
	if op := operations[1]; !slices.Equal(op.Labels, []string{"documentation", "scenario:example-pack", "tier:raes"}) ||
		op.MilestoneTitle != "Environment pack: Example Pack" || !strings.HasPrefix(op.Body, "## Goal\n") {
		t.Errorf("contract operation = %+v, want the labels, the milestone title, and the body", op)
	}
	if op := operations[3]; op.Action != actionSkipIssue || op.IssueNumber != 3 || op.Title != "example-pack: specify participant attacker behavior in RAES" {
		t.Errorf("behavior operation = %+v, want a skip of issue 3 under its new title", op)
	}
	if op := operations[5]; op.Action != actionCreateIssue {
		t.Errorf("profiles operation = %+v, want a create: issue 4 has no milestone", op)
	}
	operations, err = tmpl.BuildOperations(plan, issues, available, true, true)
	if op := operations[2]; err != nil || op.Action != actionUpdateIssue || op.IssueNumber != 3 || op.MilestoneTitle != "" || op.Body == "" {
		t.Errorf("refreshed behavior operation = %+v, %v; want an update of issue 3", op, err)
	}
}

func TestBuildOperationsBodyError(t *testing.T) {
	tmpl, err := loadTemplates(fstest.MapFS{
		"templates/issues.json":          {Data: []byte(`[{"key": "missing", "suffix": "s"}]`)},
		"templates/common-anchors.txt":   {Data: []byte("")},
		"templates/pack.txt":             {Data: []byte("")},
		"templates/child-issue-note.txt": {Data: []byte("")},
	})
	if err != nil {
		t.Fatalf("loadTemplates() error = %v", err)
	}
	if _, err := tmpl.BuildOperations(testPlan(), nil, nil, false, true); err == nil {
		t.Error("BuildOperations() with a missing body: no error")
	}
	for _, missing := range []string{"templates/pack.txt", "templates/child-issue-note.txt"} {
		fsys := fstest.MapFS{
			"templates/issues.json":          {Data: []byte(`[]`)},
			"templates/common-anchors.txt":   {Data: []byte("")},
			"templates/pack.txt":             {Data: []byte("")},
			"templates/child-issue-note.txt": {Data: []byte("")},
		}
		delete(fsys, missing)
		tmpl, err := loadTemplates(fsys)
		if err != nil {
			t.Fatalf("loadTemplates() error = %v", err)
		}
		key := map[string]string{"templates/pack.txt": "child-issue-note", "templates/child-issue-note.txt": "pack"}[missing]
		if _, err := tmpl.Body(testPlan(), key); err == nil {
			t.Errorf("Body(%q) without %s: no error", key, missing)
		}
	}
}

func TestBuildOperationsLabelsAndOrder(t *testing.T) {
	tmpl := loadTestTemplates(t)
	plan := testPlan()
	plan.Labels = []string{"documentation", "documentation"}
	in42 := &struct {
		Number int `json:"number"`
	}{Number: 42}
	issues := []Issue{
		{Number: 1, Title: "example-pack: unrelated", Milestone: in42},
		{Number: 2, Title: "example-pack: create scenario contract and pack skeleton", Milestone: in42},
	}
	operations, err := tmpl.BuildOperations(plan, issues, map[string]bool{"documentation": true}, true, true)
	if err != nil {
		t.Fatalf("BuildOperations() error = %v", err)
	}
	if op := operations[0]; op.Action != actionUpdateIssue || op.IssueNumber != 2 || !slices.Equal(op.Labels, []string{"documentation"}) {
		t.Errorf("contract operation = %+v, want an update of issue 2 with one documentation label", op)
	}
}

func TestWritePlan(t *testing.T) {
	var out strings.Builder
	w := bufio.NewWriter(&out)
	WritePlan(w, []Operation{
		{Action: actionCreateMilestone, Title: "M\x1b"},
		{Action: actionCreateIssue, Title: "a", MilestoneTitle: "M\x1b"},
		{Action: actionCreateIssue, Title: "b", MilestoneNumber: new(7)},
		{Action: actionUpdateIssue, Title: "c", IssueNumber: 3},
		{Action: actionSkipIssue, Title: "d\x07", IssueNumber: 4},
	})
	if err := w.Flush(); err != nil {
		t.Fatalf("Flush() error = %v", err)
	}
	want := "DRY RUN: no GitHub changes will be written. Pass --apply to write.\n" +
		"CREATE milestone: M\\x1b\nCREATE issue in milestone M\\x1b: a\nCREATE issue in milestone 7: b\n" +
		"UPDATE issue #3: c\nSKIP existing issue #4: d\\x07\n"
	if out.String() != want {
		t.Errorf("WritePlan() wrote %q, want %q", out.String(), want)
	}
}

func TestErrorMessage(t *testing.T) {
	if got := fail("m").Error(); got != "m" {
		t.Errorf("Error() = %q, want %q", got, "m")
	}
}
