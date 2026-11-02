package issueskeleton

import (
	"bufio"
	"errors"
	"slices"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

// call is one run of the fake gh.
type call struct {
	args  string
	stdin string
}

// fakeRunner answers each run of gh from answers, by its arguments, and
// records the runs.
type fakeRunner struct {
	answers map[string]string
	errs    map[string]error
	calls   []call
}

func (f *fakeRunner) Run(args []string, stdin []byte) ([]byte, error) {
	key := strings.Join(args, " ")
	f.calls = append(f.calls, call{args: key, stdin: string(stdin)})
	if err := f.errs[key]; err != nil {
		return nil, err
	}
	return []byte(f.answers[key]), nil
}

// newFake returns a fake gh for the repository o/r with milestone 7.
func newFake() *fakeRunner {
	return &fakeRunner{answers: map[string]string{
		"repo view x/y --json nameWithOwner":                                                  `{"nameWithOwner": "o/r"}`,
		"api repos/o/r/milestones --paginate":                                                 `[{"number": 7, "title": "Environment pack: Example Pack"}]` + "\n" + `[{"number": 8, "title": "Other"}]`,
		"issue list --repo o/r --state all --limit 2000 --json number,title,milestone,labels": `[{"number": 3, "title": "example-pack: create scenario contract and pack skeleton", "milestone": {"number": 7}}]`,
		"label list --repo o/r --limit 500 --json name":                                       `[{"name": "documentation"}, {"name": "scenario:example-pack"}, {"name": "area:content"}]`,
		"api --method POST repos/o/r/milestones --input -":                                    `{"number": 9}`,
		"api --method POST repos/o/r/issues --input -":                                        `{}`,
		"api --method PATCH repos/o/r/issues/3 --input -":                                     `{}`,
	}, errs: map[string]error{}}
}

// resolved returns a client of the fake gh after ResolveRepo.
func resolved(t *testing.T, f *fakeRunner) *GitHub {
	t.Helper()
	gh := NewGitHub(f, "x/y")
	if repo, err := gh.ResolveRepo(); err != nil || repo != "o/r" {
		t.Fatalf("ResolveRepo() = %q, %v; want o/r", repo, err)
	}
	return gh
}

func TestResolveRepoErrors(t *testing.T) {
	f := newFake()
	f.answers["repo view x/y --json nameWithOwner"] = `{"nameWithOwner": ""}`
	if _, err := NewGitHub(f, "x/y").ResolveRepo(); err == nil || err.Error() != "could not resolve repository: x/y" {
		t.Errorf("ResolveRepo() of an empty name error = %v", err)
	}
	f.errs["repo view x/y --json nameWithOwner"] = &RunError{Stderr: []byte("  HTTP 404\x1b[2J\nline two\n"), Stdout: []byte("ignored")}
	_, err := NewGitHub(f, "x/y").ResolveRepo()
	if e, ok := errors.AsType[*Error](err); !ok || e.Message != `HTTP 404\x1b[2J`+"\nline two" {
		t.Errorf("ResolveRepo() of a failed run error = %#v", err)
	}
	other := errors.New("no gh")
	f.errs["repo view x/y --json nameWithOwner"] = other
	if _, err := NewGitHub(f, "x/y").ResolveRepo(); !errors.Is(err, other) {
		t.Errorf("ResolveRepo() of a run that could not start error = %v, want %v", err, other)
	}
}

func TestRunErrorUsesStdout(t *testing.T) {
	if got := (&RunError{Stdout: []byte(" from stdout \n"), Stderr: []byte("\n")}).Error(); got != "from stdout" {
		t.Errorf("Error() = %q, want %q", got, "from stdout")
	}
	if got := (&RunError{Stderr: []byte("\x1cmessage\x1f")}).Error(); got != "message" {
		t.Errorf("Error() = %q, want the separators stripped as Python strips them", got)
	}
}

func TestMilestones(t *testing.T) {
	f := newFake()
	got, err := resolved(t, f).Milestones()
	want := []milestone{{Number: 7, Title: "Environment pack: Example Pack"}, {Number: 8, Title: "Other"}}
	if err != nil || !slices.Equal(got, want) {
		t.Errorf("Milestones() = %v, %v; want %v", got, err, want)
	}
	f.answers["api repos/o/r/milestones --paginate"] = "[{"
	if _, err := resolved(t, f).Milestones(); err == nil {
		t.Error("Milestones() of bad JSON: no error")
	}
	f.errs["api repos/o/r/milestones --paginate"] = &RunError{Stderr: []byte("denied")}
	if _, err := resolved(t, f).Milestones(); err == nil || err.Error() != "denied" {
		t.Errorf("Milestones() of a failed run error = %v", err)
	} else if _, ok := errors.AsType[*Error](err); !ok {
		t.Errorf("Milestones() of a failed run error = %#v, want an *Error", err)
	}
	other := errors.New("no gh")
	f.errs["api repos/o/r/milestones --paginate"] = other
	if _, err := resolved(t, f).Milestones(); !errors.Is(err, other) {
		t.Errorf("Milestones() error = %v, want %v", err, other)
	}
}

func TestCreateMilestone(t *testing.T) {
	f := newFake()
	gh := resolved(t, f)
	if n, err := gh.CreateMilestone("New"); err != nil || n != 9 {
		t.Errorf("CreateMilestone() = %d, %v; want 9", n, err)
	}
	if got := f.calls[len(f.calls)-1].stdin; got != `{"title":"New"}` {
		t.Errorf("CreateMilestone() payload = %q", got)
	}
	f.answers["api --method POST repos/o/r/milestones --input -"] = `{}`
	if n, err := gh.CreateMilestone("it's"); n != 0 || err == nil || err.Error() != `unexpected milestone response for "it's"` {
		t.Errorf("CreateMilestone() without a number = %d, %v", n, err)
	}
	f.errs["api --method POST repos/o/r/milestones --input -"] = &RunError{Stderr: []byte("no")}
	if n, err := gh.CreateMilestone("x"); n != 0 || err == nil {
		t.Errorf("CreateMilestone() of a failed run = %d, %v; want 0 and an error", n, err)
	}
}

func TestPrepare(t *testing.T) {
	tmpl := loadTestTemplates(t)
	f := newFake()
	plan := testPlan()
	plan.MilestoneNumber = nil
	operations, number, err := resolved(t, f).Prepare(tmpl, plan, false, false)
	if err != nil || number == nil || *number != 7 || len(operations) != 9 {
		t.Fatalf("Prepare() = %d operations, %v, %v; want 9 operations in milestone 7", len(operations), number, err)
	}
	if n := operations[1].MilestoneNumber; n == nil || *n != 7 {
		t.Errorf("Prepare() gives milestone %v to a new issue, want 7", n)
	}
	if op := operations[0]; op.Action != actionSkipIssue || op.IssueNumber != 3 {
		t.Errorf("Prepare() first operation = %+v, want a skip of issue 3", op)
	}
	if op := operations[1]; op.Action != actionCreateIssue || !slices.Equal(op.Labels, []string{"area:content", "scenario:example-pack"}) {
		t.Errorf("Prepare() second operation = %+v, want a create with the available labels", op)
	}
	plan.MilestoneTitle = "Missing"
	if _, _, missingErr := resolved(t, f).Prepare(tmpl, plan, false, false); missingErr == nil ||
		missingErr.Error() != "milestone not found: 'Missing'; pass --create-milestone" {
		t.Errorf("Prepare() of a missing milestone error = %v", missingErr)
	}
	// Without a milestone number, an issue in any milestone matches, as in the
	// Python code, so refresh updates issue 3.
	operations, number, err = resolved(t, f).Prepare(tmpl, plan, true, true)
	if err != nil || number != nil || operations[0].Action != actionCreateMilestone ||
		operations[1].Action != actionUpdateIssue || operations[1].IssueNumber != 3 {
		t.Errorf("Prepare() with create = %v, %v, %+v; want a new milestone, then an update of issue 3", number, err, operations[:2])
	}
	plan.MilestoneNumber = new(8)
	plan.MilestoneTitle = "Environment pack: Example Pack"
	operations, number, err = resolved(t, f).Prepare(tmpl, plan, false, true)
	if err != nil || number == nil || *number != 8 || operations[0].Action != actionCreateIssue {
		t.Errorf("Prepare() in milestone 8 = %v, %v; want a new issue, because issue 3 is in milestone 7", number, err)
	}
}

func TestPrepareErrors(t *testing.T) {
	tmpl := loadTestTemplates(t)
	for _, key := range []string{
		"api repos/o/r/milestones --paginate",
		"issue list --repo o/r --state all --limit 2000 --json number,title,milestone,labels",
		"label list --repo o/r --limit 500 --json name",
	} {
		f := newFake()
		f.errs[key] = &RunError{Stderr: []byte("failed")}
		if _, _, err := resolved(t, f).Prepare(tmpl, testPlan(), false, false); err == nil || err.Error() != "failed" {
			t.Errorf("Prepare() with a failed %q error = %v", key, err)
		}
	}
}

func TestApply(t *testing.T) {
	f := newFake()
	// gh can answer a write with no output.
	f.answers["api --method PATCH repos/o/r/issues/3 --input -"] = ""
	gh := resolved(t, f)
	var out strings.Builder
	w := bufio.NewWriter(&out)
	operations := []Operation{
		{Action: actionCreateMilestone, Title: "New\x1b"},
		{Action: actionCreateIssue, Title: "i1", Body: "b1"},
		{Action: actionUpdateIssue, Title: "i2", Body: "b2", IssueNumber: 3, Labels: []string{"documentation"}},
		{Action: actionSkipIssue, Title: "i3", IssueNumber: 4},
	}
	if err := gh.Apply(w, operations, nil); err != nil {
		t.Fatalf("Apply() error = %v", err)
	}
	if err := w.Flush(); err != nil {
		t.Fatalf("Flush() error = %v", err)
	}
	want := "created milestone 9: New\\x1b\ncreated issue: i1\nupdated issue #3: i2\nskipped issue #4: i3\n"
	if out.String() != want {
		t.Errorf("Apply() wrote %q, want %q", out.String(), want)
	}
	if got := f.calls[len(f.calls)-1].args; got != "api --method PATCH repos/o/r/issues/3 --input -" {
		t.Errorf("Apply() of an update ran gh %q, want a PATCH of issue 3", got)
	}
	payloads := []string{f.calls[len(f.calls)-2].stdin, f.calls[len(f.calls)-1].stdin}
	wantPayloads := []string{
		`{"title":"i1","body":"b1","labels":[],"milestone":9}`,
		`{"title":"i2","body":"b2","labels":["documentation"],"milestone":9}`,
	}
	if diff := cmp.Diff(wantPayloads, payloads); diff != "" {
		t.Errorf("Apply() payloads mismatch (-want +got):\n%s", diff)
	}
}

func TestApplyErrors(t *testing.T) {
	var out strings.Builder
	w := bufio.NewWriter(&out)
	f := newFake()
	gh := resolved(t, f)
	for _, action := range []string{actionCreateIssue, actionUpdateIssue} {
		err := gh.Apply(w, []Operation{{Action: action, Title: "t"}}, nil)
		want := "cannot " + strings.TrimSuffix(action, "_issue") + " issue without a milestone number"
		if err == nil || err.Error() != want {
			t.Errorf("Apply() of %s without a milestone error = %v, want %q", action, err, want)
		}
	}
	f.errs["api --method POST repos/o/r/milestones --input -"] = &RunError{Stderr: []byte("no milestone")}
	if err := gh.Apply(w, []Operation{{Action: actionCreateMilestone, Title: "t"}}, nil); err == nil || err.Error() != "no milestone" {
		t.Errorf("Apply() of a failed milestone error = %v", err)
	}
	f.errs["api --method POST repos/o/r/issues --input -"] = &RunError{Stderr: []byte("no issue")}
	if err := gh.Apply(w, []Operation{{Action: actionCreateIssue, Title: "t"}}, new(1)); err == nil || err.Error() != "no issue" {
		t.Errorf("Apply() of a failed issue error = %v", err)
	}
}
