package testgate

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

// withWorktree makes a temporary directory in tempDir and a git worktree of
// commit in it, calls f with the worktree directory, and then removes both.
// The removal runs also when ctx is canceled.
func withWorktree(ctx context.Context, r Runner, repo, tempDir, commit string, f func(tree string) error) (err error) {
	tmp, err := os.MkdirTemp(tempDir, "testgate-")
	if err != nil {
		return fmt.Errorf("make a temporary directory: %w", err)
	}
	defer func() { err = errors.Join(err, os.RemoveAll(tmp)) }()
	tree := filepath.Join(tmp, "tree")
	if _, addErr := runOK(ctx, r, Command{Dir: repo, Name: "git", Args: []string{"worktree", "add", "--detach", "--quiet", tree, commit}}); addErr != nil {
		return addErr
	}
	defer func() {
		_, removeErr := runOK(context.WithoutCancel(ctx), r, Command{Dir: repo, Name: "git", Args: []string{"worktree", "remove", "--force", tree}})
		err = errors.Join(err, removeErr)
	}()
	return f(tree)
}

// readFile reads a file that the gate wrote, or that go-mutesting named. The
// gosec check G304 reports a read through a path variable as a file
// inclusion. That is a false positive here, because no path comes from an
// untrusted input.
func readFile(path string) ([]byte, error) {
	return os.ReadFile(path) //nolint:gosec // G304 false positive: each path comes from the gate or from go-mutesting.
}
