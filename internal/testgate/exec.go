package testgate

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// linesFile is the file in the worktree root that holds the changed lines of
// a run on the changed lines. The exec step reads it.
const linesFile = ".testgate-lines.json"

// The exec statuses that go-mutesting expects from its exec command.
const (
	// ExecKilled reports a mutant that a test kills.
	ExecKilled = 0
	// ExecEscaped reports a mutant that each test passes with.
	ExecEscaped = 1
	// ExecNotCompiled reports a mutant that does not compile.
	ExecNotCompiled = 2
)

// A Mutant is the input of the exec step for one mutant.
type Mutant struct {
	// Original is the file that the mutant changes.
	Original string
	// Mutated is the file with the mutant.
	Mutated string
	// Package is the package of the file, as go-mutesting names it: the
	// directory of the file for a package of a module.
	Package string
	// Timeout is the time limit of the tests.
	Timeout time.Duration
}

// ExecMutant tests one mutant for go-mutesting. It puts the mutated file in
// the place of the original file, runs go test -json on the package in
// directory dir, and restores the original file. It returns one of the exec
// statuses.
//
// A mutant that does not change the source, or that changes no line in the
// changed lines file of dir, is out of scope. ExecMutant reports it as killed
// without a test run, and the gate counts it as skipped.
func ExecMutant(ctx context.Context, r Runner, dir string, m Mutant) (status int, err error) {
	if strings.HasPrefix(m.Package, "-") {
		return 0, fmt.Errorf("package %q is not a package path", m.Package)
	}
	original, err := readFile(m.Original)
	if err != nil {
		return 0, fmt.Errorf("read the original file: %w", err)
	}
	mutated, err := readFile(m.Mutated)
	if err != nil {
		return 0, fmt.Errorf("read the mutant: %w", err)
	}
	scope, err := inScope(dir, m.Original, string(original), string(mutated))
	if err != nil {
		return 0, err
	}
	if !scope {
		return ExecKilled, nil
	}
	if writeErr := os.WriteFile(m.Original, mutated, 0o600); writeErr != nil {
		return 0, fmt.Errorf("put the mutant in place: %w", writeErr)
	}
	defer func() { err = errors.Join(err, os.WriteFile(m.Original, original, 0o600)) }()
	res, err := r.Run(ctx, Command{Dir: dir, Name: "go", Args: []string{
		"test", "-json", "-count=1", "-timeout=" + m.Timeout.String(), m.Package,
	}})
	if err != nil {
		return 0, err
	}
	return execStatus(res, m.Package)
}

// inScope reports whether a mutant of file changes the source and a line in
// the changed lines file of directory dir. Without that file, each mutant
// that changes the source is in scope.
func inScope(dir, file, original, mutated string) (bool, error) {
	start, end, changed := changedRange(strings.Split(original, "\n"), strings.Split(mutated, "\n"))
	if !changed {
		return false, nil
	}
	data, err := readFile(filepath.Join(dir, linesFile))
	if errors.Is(err, fs.ErrNotExist) {
		return true, nil
	}
	if err != nil {
		return false, fmt.Errorf("read the changed lines: %w", err)
	}
	var changes Changes
	if err := json.Unmarshal(data, &changes); err != nil {
		return false, fmt.Errorf("decode the changed lines: %w", err)
	}
	return changes[file].Intersects(start, end), nil
}

// execStatus classifies the output of go test -json for the one package pkg.
// The events name the package by its import path, which can differ from pkg.
func execStatus(res Result, pkg string) (int, error) {
	events, err := parseEvents(res.Stdout)
	if err != nil {
		return 0, err
	}
	if buildFailed(events) {
		return ExecNotCompiled, nil
	}
	switch outcome(events, packageOf(events), "") {
	case "fail":
		return ExecKilled, nil
	case "pass", "skip":
		return ExecEscaped, nil
	}
	return 0, fmt.Errorf("go test reported no result for %s: exit status %d: %s", pkg, res.ExitCode, bytes.TrimSpace(res.Stderr))
}
