package issueskeleton

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"

	"github.com/OpenRAE/env-packs/internal/terminal"
)

// A Runner runs gh with arguments and standard input. It returns the standard
// output of a run that succeeds. For a run that exits with another status, it
// returns a *RunError.
type Runner interface {
	// Run runs gh with args and stdin.
	Run(args []string, stdin []byte) ([]byte, error)
}

// A RunError reports a run of gh that exited with a failure status.
type RunError struct {
	Stdout, Stderr []byte
}

// Error returns the output of the failed run, as the Python code reports it:
// the standard error, or the standard output when the error is empty. It
// escapes each line for a terminal.
func (e *RunError) Error() string {
	text := strings.TrimFunc(string(e.Stderr), isSpace)
	if text == "" {
		text = strings.TrimFunc(string(e.Stdout), isSpace)
	}
	lines := strings.Split(text, "\n")
	for i, line := range lines {
		lines[i] = terminal.Escape(line)
	}
	return strings.Join(lines, "\n")
}

// The parts of the arguments of gh that the calls share.
const (
	jsonFlag = "--json"
	repos    = "repos/"
)

// A GitHub client reads and writes one repository through gh.
type GitHub struct {
	runner Runner
	repo   string
}

// NewGitHub returns a client for repo, which must pass ValidateRepo.
func NewGitHub(runner Runner, repo string) *GitHub {
	return &GitHub{runner: runner, repo: repo}
}

// run runs gh with args and stdin, and decodes its JSON output into out when
// the output is not empty. A payload goes to gh on its standard input, with
// "--input -", and never on its command line.
func (g *GitHub) run(args []string, stdin []byte, out any) error {
	if stdin != nil {
		args = append(args, "--input", "-")
	}
	stdout, err := g.runner.Run(args, stdin)
	if runErr, ok := errors.AsType[*RunError](err); ok {
		return fail(runErr.Error())
	}
	if err != nil {
		return err
	}
	if len(bytes.TrimSpace(stdout)) == 0 {
		return nil
	}
	return json.Unmarshal(stdout, out)
}

// The payloads of gh, in the order of the keys of the Python code.
type (
	milestonePayload struct {
		Title string `json:"title"`
	}
	issuePayload struct {
		Title     string   `json:"title"`
		Body      string   `json:"body"`
		Labels    []string `json:"labels"`
		Milestone int      `json:"milestone"`
	}
)

// ResolveRepo resolves the repository to its canonical OWNER/REPOSITORY, and
// the client uses that name from then on. The gh command follows renames,
// fixes the letter case, and fails for a repository that does not exist or
// that the user cannot read.
func (g *GitHub) ResolveRepo() (string, error) {
	var row struct {
		NameWithOwner string `json:"nameWithOwner"`
	}
	if err := g.run([]string{"repo", "view", g.repo, jsonFlag, "nameWithOwner"}, nil, &row); err != nil {
		return "", err
	}
	if row.NameWithOwner == "" {
		return "", fail("could not resolve repository: " + g.repo)
	}
	g.repo = row.NameWithOwner
	return g.repo, nil
}

// Labels returns the labels of the repository.
func (g *GitHub) Labels() (map[string]bool, error) {
	var rows []struct {
		Name string `json:"name"`
	}
	if err := g.run([]string{"label", "list", "--repo", g.repo, "--limit", "500", jsonFlag, "name"}, nil, &rows); err != nil {
		return nil, err
	}
	labels := make(map[string]bool, len(rows))
	for _, row := range rows {
		labels[row.Name] = true
	}
	return labels, nil
}

// Issues returns the issues of the repository.
func (g *GitHub) Issues() ([]Issue, error) {
	var issues []Issue
	err := g.run([]string{
		"issue", "list", "--repo", g.repo, "--state", "all", "--limit", "2000",
		jsonFlag, "number,title,milestone,labels",
	}, nil, &issues)
	return issues, err
}

// A milestone is a milestone of the repository.
type milestone struct {
	Number int    `json:"number"`
	Title  string `json:"title"`
}

// Milestones returns the milestones of the repository. The gh command writes
// one JSON array for each page.
func (g *GitHub) Milestones() ([]milestone, error) {
	stdout, err := g.runner.Run([]string{"api", repos + g.repo + "/milestones", "--paginate"}, nil)
	if runErr, ok := errors.AsType[*RunError](err); ok {
		return nil, fail(runErr.Error())
	}
	if err != nil {
		return nil, err
	}
	var all []milestone
	dec := json.NewDecoder(bytes.NewReader(stdout))
	for {
		var page []milestone
		if err := dec.Decode(&page); errors.Is(err, io.EOF) {
			return all, nil
		} else if err != nil {
			return nil, err
		}
		all = append(all, page...)
	}
}

// CreateMilestone creates a milestone with title, and returns its number.
func (g *GitHub) CreateMilestone(title string) (int, error) {
	var row struct {
		Number *int `json:"number"`
	}
	payload, _ := json.Marshal(milestonePayload{Title: title})
	if err := g.run([]string{"api", "--method", "POST", repos + g.repo + "/milestones"}, payload, &row); err != nil {
		return 0, err
	}
	if row.Number == nil {
		return 0, fail("unexpected milestone response for " + terminal.Quote(title))
	}
	return *row.Number, nil
}

// writeIssue creates an issue, or updates the issue with a number.
func (g *GitHub) writeIssue(op Operation, milestone int) error {
	method, path := "POST", repos+g.repo+"/issues"
	if op.Action == actionUpdateIssue {
		method, path = "PATCH", path+"/"+strconv.Itoa(op.IssueNumber)
	}
	labels := op.Labels
	if labels == nil {
		labels = []string{}
	}
	payload, _ := json.Marshal(issuePayload{Title: op.Title, Body: op.Body, Labels: labels, Milestone: milestone})
	return g.run([]string{"api", "--method", method, path}, payload, &json.RawMessage{})
}

// Prepare returns the operations for plan, and the number of its milestone
// when the milestone exists. With create, a missing milestone becomes an
// operation; a dry run sets create.
func (g *GitHub) Prepare(t *Templates, plan Plan, create, refresh bool) ([]Operation, *int, error) {
	milestones, err := g.Milestones()
	if err != nil {
		return nil, nil, err
	}
	number, exists := plan.MilestoneNumber, plan.MilestoneNumber != nil
	for _, m := range milestones {
		if !exists && m.Title == MilestoneTitle(plan) {
			number, exists = &m.Number, true
		}
	}
	if !exists && !create {
		return nil, nil, fail("milestone not found: " + terminal.Quote(MilestoneTitle(plan)) + "; pass --create-milestone")
	}
	plan.MilestoneNumber = number
	issues, err := g.Issues()
	if err != nil {
		return nil, nil, err
	}
	labels, err := g.Labels()
	if err != nil {
		return nil, nil, err
	}
	operations, err := t.BuildOperations(plan, issues, labels, refresh, exists)
	return operations, number, err
}

// Apply writes the operations to GitHub, and writes a line to w for each one.
// The milestone parameter is the number of the existing milestone, or nil.
func (g *GitHub) Apply(w *bufio.Writer, operations []Operation, milestone *int) error {
	for _, op := range operations {
		var err error
		switch op.Action {
		case actionCreateMilestone:
			var number int
			if number, err = g.CreateMilestone(op.Title); err == nil {
				milestone = &number
				fmt.Fprintf(w, "created milestone %d: %s\n", number, terminal.Escape(op.Title))
			}
		case actionCreateIssue, actionUpdateIssue:
			err = g.applyIssue(w, op, milestone)
		case actionSkipIssue:
			fmt.Fprintf(w, "skipped issue #%d: %s\n", op.IssueNumber, terminal.Escape(op.Title))
		}
		if err != nil {
			return err
		}
	}
	return nil
}

// applyIssue creates or updates the issue of op in the milestone, and writes
// a line to w.
func (g *GitHub) applyIssue(w *bufio.Writer, op Operation, milestone *int) error {
	verb, done := "create", "created issue: "
	if op.Action == actionUpdateIssue {
		verb, done = "update", "updated issue #"+strconv.Itoa(op.IssueNumber)+": "
	}
	if milestone == nil {
		return fail("cannot " + verb + " issue without a milestone number")
	}
	if err := g.writeIssue(op, *milestone); err != nil {
		return err
	}
	fmt.Fprintf(w, "%s%s\n", done, terminal.Escape(op.Title))
	return nil
}
