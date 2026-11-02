package issueskeleton

import (
	"bufio"
	"fmt"
	"slices"
	"strconv"

	"github.com/OpenRAE/env-packs/internal/terminal"
)

// The actions of an operation.
const (
	actionCreateMilestone = "create_milestone"
	actionCreateIssue     = "create_issue"
	actionUpdateIssue     = "update_issue"
	actionSkipIssue       = "skip_issue"
)

// An Operation is one change that the command plans.
type Operation struct {
	// Action is "create_milestone", "create_issue", "update_issue", or
	// "skip_issue".
	Action string
	Title  string
	Body   string
	Labels []string
	// IssueNumber is the number of an existing issue.
	IssueNumber int
	// MilestoneNumber is the number of the milestone, or nil.
	MilestoneNumber *int
	// MilestoneTitle is the title of the milestone of a new issue or of a new
	// milestone.
	MilestoneTitle string
}

// An Issue is an existing issue, as gh lists it.
type Issue struct {
	Number    int    `json:"number"`
	Title     string `json:"title"`
	Milestone *struct {
		Number int `json:"number"`
	} `json:"milestone"`
}

// MilestoneTitle returns the title of the milestone of plan.
func MilestoneTitle(plan Plan) string {
	if plan.MilestoneTitle != "" {
		return plan.MilestoneTitle
	}
	return "Environment pack: " + plan.Title
}

// wantedLabels returns the labels of an issue: the labels of its template and
// of plan that the repository has, sorted.
func wantedLabels(plan Plan, template IssueTemplate, available map[string]bool) []string {
	var labels []string
	for _, label := range slices.Concat(template.Labels, plan.Labels) {
		if available[label] && !slices.Contains(labels, label) {
			labels = append(labels, label)
		}
	}
	slices.Sort(labels)
	return labels
}

// matchingIssue returns the issue with title in the milestone of plan, or nil.
// With no milestone number, any milestone matches.
func matchingIssue(issues []Issue, title string, milestone *int) *Issue {
	for i, issue := range issues {
		if issue.Title != title {
			continue
		}
		if milestone == nil || issue.Milestone != nil && issue.Milestone.Number == *milestone {
			return &issues[i]
		}
	}
	return nil
}

// matchingTemplateIssue returns the existing issue of template: the issue with
// its title or with a former title.
func matchingTemplateIssue(issues []Issue, plan Plan, template IssueTemplate) *Issue {
	for _, suffix := range slices.Concat([]string{template.Suffix}, template.LegacySuffixes) {
		if found := matchingIssue(issues, plan.PackID+": "+suffix, plan.MilestoneNumber); found != nil {
			return found
		}
	}
	return nil
}

// BuildOperations returns the operations for plan: create the milestone when
// it does not exist, and create each missing issue. An existing issue is
// skipped, or updated with refresh.
func (t *Templates) BuildOperations(plan Plan, issues []Issue, available map[string]bool, refresh, milestoneExists bool) ([]Operation, error) {
	var operations []Operation
	if !milestoneExists {
		title := MilestoneTitle(plan)
		operations = append(operations, Operation{Action: actionCreateMilestone, Title: title, MilestoneTitle: title})
	}
	for _, template := range t.Issues {
		title := plan.PackID + ": " + template.Suffix
		found := matchingTemplateIssue(issues, plan, template)
		if found != nil && !refresh {
			operations = append(operations, Operation{
				Action: actionSkipIssue, Title: title, IssueNumber: found.Number, MilestoneNumber: plan.MilestoneNumber,
			})
			continue
		}
		body, err := t.Body(plan, template.Key)
		if err != nil {
			return nil, err
		}
		op := Operation{
			Action: actionCreateIssue, Title: title, Body: body,
			Labels: wantedLabels(plan, template, available), MilestoneNumber: plan.MilestoneNumber,
			MilestoneTitle: MilestoneTitle(plan),
		}
		if found != nil {
			op.Action, op.IssueNumber, op.MilestoneTitle = actionUpdateIssue, found.Number, ""
		}
		operations = append(operations, op)
	}
	return operations, nil
}

// WritePlan writes the dry run report of operations to w. It escapes each
// title, which can hold the text of an argument.
func WritePlan(w *bufio.Writer, operations []Operation) {
	fmt.Fprintf(w, "DRY RUN: no GitHub changes will be written. Pass --apply to write.\n")
	for _, op := range operations {
		title := terminal.Escape(op.Title)
		switch op.Action {
		case actionCreateMilestone:
			fmt.Fprintf(w, "CREATE milestone: %s\n", title)
		case actionCreateIssue:
			where := terminal.Escape(op.MilestoneTitle)
			if op.MilestoneNumber != nil {
				where = strconv.Itoa(*op.MilestoneNumber)
			}
			fmt.Fprintf(w, "CREATE issue in milestone %s: %s\n", where, title)
		case actionUpdateIssue:
			fmt.Fprintf(w, "UPDATE issue #%d: %s\n", op.IssueNumber, title)
		case actionSkipIssue:
			fmt.Fprintf(w, "SKIP existing issue #%d: %s\n", op.IssueNumber, title)
		}
	}
}
