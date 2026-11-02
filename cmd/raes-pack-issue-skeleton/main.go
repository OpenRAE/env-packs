// Command raes-pack-issue-skeleton creates the standard planning issues of a
// new environment pack in a GitHub catalog repository, through gh (design
// 0008). Dry run is the default; --apply writes to GitHub.
package main

import (
	"bytes"
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
	"unicode"

	"github.com/OpenRAE/env-packs/internal/issueskeleton"
	"github.com/OpenRAE/env-packs/internal/outcome"
	"github.com/OpenRAE/env-packs/internal/terminal"
)

// name is the name of the command.
const name = "raes-pack-issue-skeleton"

// usageLine is the usage line of the command, as argparse gives it.
const usageLine = "usage: " + name + " [-h] [--repo REPO] [--pack-id PACK_ID] [--title TITLE] [--focus FOCUS]" +
	" [--source SOURCE] [--label LABEL] [--milestone-number MILESTONE_NUMBER]" +
	" [--milestone-title MILESTONE_TITLE] [--create-milestone] [--refresh-existing] [--apply]"

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr, ghRunner{}))
}

// run runs the command with args and returns its exit status.
func run(args []string, stdout, stderr io.Writer, runner issueskeleton.Runner) int {
	return outcome.Run(name, outcome.NewStreams(stdout, stderr), func(s outcome.Streams) (int, error) {
		return body(args, s, runner)
	})
}

// options are the flags of the command.
type options struct {
	repo, packID, title, focus, milestoneTitle string
	sources, labels                            []string
	milestoneNumber                            *int
	createMilestone, refresh, apply            bool
}

// parse parses the flags in args. It returns false with the status of a
// usage error or of help, and true when the command goes on.
func parse(args []string, s outcome.Streams) (o options, status int, ok bool) {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	fs.StringVar(&o.repo, "repo", "", "GitHub catalog repository (OWNER/REPOSITORY) that will own the pack")
	fs.StringVar(&o.packID, "pack-id", "", "lowercase kebab-case environment pack id")
	fs.StringVar(&o.title, "title", "", "human-readable scenario title")
	fs.StringVar(&o.focus, "focus", "TBD by the pack-design agent.", "one-sentence scenario focus")
	fs.Func("source", "source-log entry; repeatable", func(v string) error {
		o.sources = append(o.sources, v)
		return nil
	})
	fs.Func("label", "extra issue label to apply if it exists; repeatable", func(v string) error {
		o.labels = append(o.labels, v)
		return nil
	})
	fs.Func("milestone-number", "existing GitHub milestone number", func(v string) error {
		n, err := strconv.Atoi(strings.TrimFunc(v, unicode.IsSpace))
		if err != nil {
			return fmt.Errorf("invalid int value: %q", v)
		}
		o.milestoneNumber = &n
		return nil
	})
	fs.StringVar(&o.milestoneTitle, "milestone-title", "", "existing or new GitHub milestone title")
	fs.BoolVar(&o.createMilestone, "create-milestone", false, "create --milestone-title when it does not exist")
	fs.BoolVar(&o.refresh, "refresh-existing", false, "update existing skeleton issues instead of skipping them")
	fs.BoolVar(&o.apply, "apply", false, "write changes to GitHub; default is dry-run")
	err := fs.Parse(args)
	switch {
	case errors.Is(err, flag.ErrHelp):
		fmt.Fprintf(s.Stdout, "%s\n\nCreate standard skeleton GitHub issues for an environment pack.\n", usageLine)
		fs.SetOutput(s.Stdout)
		fs.PrintDefaults()
		return o, outcome.OK, false
	case err == nil && fs.NArg() > 0:
		err = errors.New("unrecognized arguments: " + strings.Join(fs.Args(), " "))
	}
	if err != nil {
		fmt.Fprintf(s.Stderr, "%s\n%s: error: %s\n", usageLine, name, terminal.Escape(err.Error()))
		return o, outcome.Usage, false
	}
	return o, outcome.OK, true
}

// body runs the command. An *issueskeleton.Error is an expected failure: the
// command writes its message and returns the status 1, as the Python command
// does. Any other error is a defect.
func body(args []string, s outcome.Streams, runner issueskeleton.Runner) (int, error) {
	o, status, ok := parse(args, s)
	if !ok {
		return status, nil
	}
	err := plan(o, s, runner)
	if failure, ok := errors.AsType[*issueskeleton.Error](err); ok {
		fmt.Fprintf(s.Stderr, "%s\n", failure.Message)
		return outcome.Blocking, nil
	}
	return outcome.OK, err
}

// plan plans the issues of the pack, and writes them to GitHub with --apply.
func plan(o options, s outcome.Streams, runner issueskeleton.Runner) error {
	if err := issueskeleton.ValidateRepo(o.repo); err != nil {
		return err
	}
	gh := issueskeleton.NewGitHub(runner, o.repo)
	repo, err := gh.ResolveRepo()
	if err != nil {
		return err
	}
	p, err := o.plan(repo)
	if err != nil {
		return err
	}
	operations, milestone, err := gh.Prepare(issueskeleton.NewTemplates(), p, o.createMilestone || !o.apply, o.refresh)
	if err != nil {
		return err
	}
	if !o.apply {
		issueskeleton.WritePlan(s.Stdout, operations)
		return nil
	}
	return gh.Apply(s.Stdout, operations, milestone)
}

// plan returns the plan of the pack in repo, as plan_from_args of the Python
// code checks it.
func (o options) plan(repo string) (issueskeleton.Plan, error) {
	if o.packID == "" {
		return issueskeleton.Plan{}, &issueskeleton.Error{Message: "--pack-id is required"}
	}
	if err := issueskeleton.ValidatePackID(o.packID); err != nil {
		return issueskeleton.Plan{}, err
	}
	if (o.milestoneNumber == nil || *o.milestoneNumber == 0) && o.milestoneTitle == "" {
		return issueskeleton.Plan{}, &issueskeleton.Error{Message: "pass --milestone-number or --milestone-title"}
	}
	title := o.title
	if title == "" {
		title = issueskeleton.TitleFromPackID(o.packID)
	}
	return issueskeleton.Plan{
		PackID: o.packID, Title: title, Focus: o.focus, Sources: o.sources, Labels: o.labels,
		PackRoot: issueskeleton.PackRootForRepo(repo), MilestoneNumber: o.milestoneNumber,
		MilestoneTitle: o.milestoneTitle,
	}, nil
}

// ghRunner runs gh. It is the only code of the command that starts a process
// (design 0008).
type ghRunner struct{}

// Command limits bound the GitHub process and the data it can return.
const (
	ghTimeout     = time.Minute
	ghStdoutLimit = 8 << 20
	ghStderrLimit = 64 << 10
)

// errGHOutputLimit reports incomplete process output without exposing it.
var errGHOutputLimit = errors.New("gh output exceeds the command limit")

// Run runs gh with args, and gives it stdin.
func (ghRunner) Run(args []string, stdin []byte) ([]byte, error) {
	gh, err := ghPath()
	if err != nil {
		return nil, err
	}
	ctx, cancel := context.WithTimeout(context.Background(), ghTimeout)
	defer cancel()
	//nolint:gosec // G204 false positive: the program is gh at its checked absolute path, the arguments go as an argument vector without a shell, and the only argument from the user is the --repo selector, which ValidateRepo checks first.
	cmd := exec.CommandContext(ctx, gh, args...)
	cmd.WaitDelay = time.Second
	cmd.Stdin = bytes.NewReader(stdin)
	stdout, stderr := limitedBuffer{remaining: ghStdoutLimit}, limitedBuffer{remaining: ghStderrLimit}
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	err = cmd.Run()
	if stdout.exceeded || stderr.exceeded {
		return nil, errGHOutputLimit
	}
	// A signal (including a deadline kill) is an execution failure, not a
	// normal gh rejection. Keep it on the bounded internal-error path.
	if exitErr, ok := errors.AsType[*exec.ExitError](err); ok && exitErr.ExitCode() != -1 {
		return nil, &issueskeleton.RunError{Stdout: stdout.buffer.Bytes(), Stderr: stderr.buffer.Bytes()}
	}
	return stdout.buffer.Bytes(), err
}

// limitedBuffer bounds a process stream. A write past the limit fails, so
// os/exec stops copying the stream and reports an incomplete result.
type limitedBuffer struct {
	buffer    bytes.Buffer
	remaining int
	exceeded  bool
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	n := min(len(p), b.remaining)
	_, _ = b.buffer.Write(p[:n]) // bytes.Buffer.Write never returns an error.
	b.remaining -= n
	if n < len(p) {
		b.exceeded = true
		return n, errGHOutputLimit
	}
	return n, nil
}

// ghPath returns the absolute path of gh from PATH, after symlinks resolve.
// It rejects group or other write access to the file and its immediate
// directories. The caller must supply a trusted PATH, including the owners
// and parent directories of its entries.
func ghPath() (string, error) {
	found, err := exec.LookPath("gh")
	if err != nil {
		return "", err
	}
	resolved, err := filepath.EvalSymlinks(found)
	if err != nil {
		return "", err
	}
	for _, path := range []string{filepath.Dir(found), resolved, filepath.Dir(resolved)} {
		info, err := os.Stat(path)
		if err != nil {
			return "", err
		}
		if info.Mode().Perm()&0o022 != 0 {
			return "", &issueskeleton.Error{Message: "gh at " + terminal.Quote(found) +
				" is not safe to run: other users can write " + terminal.Quote(path)}
		}
	}
	return resolved, nil
}
