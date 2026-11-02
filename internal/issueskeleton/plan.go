// Package issueskeleton plans the standard planning issues of a new pack, and
// writes them to GitHub through gh (design 0008). It is the logic of
// raes-pack-issue-skeleton.
package issueskeleton

import (
	"regexp"
	"strings"

	"github.com/OpenRAE/env-packs/internal/terminal"
)

// The repository of this project keeps its packs under packs/ (ADR 0036).
const firstPartyRepo = "OpenRAE/env-packs"

// The messages name an example catalog.
const exampleCatalog = "example-org/example-packs"

// targetRepo matches an OWNER/REPOSITORY selector. The gh command resolves
// the repository; the pattern only rejects URLs, extra parts, and other
// characters.
var targetRepo = regexp.MustCompile(`^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`)

// packID matches a lowercase kebab-case pack id.
var packID = regexp.MustCompile(`^[a-z0-9][a-z0-9-]*[a-z0-9]$`)

// An Error is an expected failure of the command. Its message is the message
// of the Python code, and it is safe to write to a terminal.
type Error struct {
	Message string
}

// Error returns the message of the failure.
func (e *Error) Error() string {
	return e.Message
}

// fail returns a failure with message.
func fail(message string) *Error {
	return &Error{Message: message}
}

// A Plan is the plan of the issues of one pack.
type Plan struct {
	PackID string
	Title  string
	Focus  string
	// Sources are the entries of the source log.
	Sources []string
	// Labels are extra labels for each issue, if the repository has them.
	Labels []string
	// PackRoot is the directory of the packs in the repository.
	PackRoot string
	// MilestoneNumber is the number of an existing milestone, or nil.
	MilestoneNumber *int
	// MilestoneTitle is the title of the milestone, or "".
	MilestoneTitle string
}

// ValidateRepo checks the OWNER/REPOSITORY selector of --repo, before the
// command starts gh.
func ValidateRepo(repo string) error {
	if repo == "" {
		return fail("--repo OWNER/REPOSITORY is required: name the catalog repository " +
			"that will own the pack (e.g. " + exampleCatalog + ").")
	}
	if !targetRepo.MatchString(repo) {
		return fail("--repo must be a GitHub OWNER/REPOSITORY slug using letters, " +
			"digits, '.', '_', and '-'; got " + terminal.Quote(repo))
	}
	return nil
}

// ValidatePackID checks a pack id.
func ValidatePackID(id string) error {
	if !packID.MatchString(id) {
		return fail("pack id must be lowercase kebab-case, start/end with a letter or " +
			"digit, and contain only a-z, 0-9, and '-'")
	}
	return nil
}

// TitleFromPackID returns the title of a pack id: each part, with a capital
// first letter, separated by a space.
func TitleFromPackID(id string) string {
	parts := strings.Split(id, "-")
	for i, part := range parts {
		if part != "" {
			parts[i] = strings.ToUpper(part[:1]) + part[1:]
		}
	}
	return strings.Join(parts, " ")
}

// PackRootForRepo returns the directory of the packs in repo: packs/ in this
// repository, and environments/ in each other catalog.
func PackRootForRepo(repo string) string {
	if strings.EqualFold(repo, firstPartyRepo) {
		return "packs"
	}
	return "environments"
}
