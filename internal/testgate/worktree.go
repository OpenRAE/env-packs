package testgate

import (
	"context"
	"errors"
	"fmt"
	"io/fs"
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

// readFile reads the file at path. It opens the directory of the file as the
// root of the read.
func readFile(path string) ([]byte, error) {
	return fs.ReadFile(os.DirFS(filepath.Dir(path)), filepath.Base(path))
}
