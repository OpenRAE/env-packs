package main

import (
	"errors"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/OpenRAE/env-packs/internal/outcome"
)

func TestWorkflowShapes(t *testing.T) {
	for _, text := range []string{"{}", "jobs: null", "jobs: []", "jobs: {bad: 3}", "jobs: {bad: {steps: null}}", "jobs: {bad: {steps: [3]}}", "jobs: {bad: {steps: [{run: \"'\"}]}}"} {
		doc, err := decodeInput("w.yml", []byte(text))
		if err != nil {
			t.Fatal(err)
		}
		var input repositoryInput
		if err := input.addCommands("w.yml", doc); err == nil {
			t.Errorf("addCommands(%q) error = nil, want refusal", text)
		}
	}
	var input repositoryInput
	if err := input.addCommands("w.yml", []any{}); err == nil {
		t.Error("non-object workflow accepted")
	}
	doc, err := decodeInput("w.yml", []byte("jobs:\n  z: {uses: './reusable.yml'}\n  b: {steps: [{uses: './action'}, {run: 'echo b'}]}\n  a: {steps: [{run: 'echo a'}]}\n"))
	if err != nil {
		t.Fatal(err)
	}
	if err := input.addCommands("w.yml", doc); err != nil {
		t.Fatal(err)
	}
	if len(input.Commands) != 2 || input.Commands[0].Job != "a" || input.Commands[1].Job != "b" {
		t.Fatalf("commands = %v, want deterministic job order without action-only steps", input.Commands)
	}
}

func TestDiscoveryBoundaries(t *testing.T) {
	files := fstest.MapFS{"docs/public/index.md": {}, "docs/public/_build/hidden.md": {}, "docs/public/image.png": {}}
	names, err := discover(files, "docs/public")
	if err != nil || len(names) != 1 || names[0] != "docs/public/index.md" {
		t.Fatalf("discover() = %q, %v, want only index", names, err)
	}
	files["docs/public/link"] = &fstest.MapFile{Mode: fs.ModeSymlink}
	if _, err := discover(files, "docs/public"); err == nil {
		t.Error("discovery accepted a symlink")
	}
	if _, err := collect(fstest.MapFS{".github/workflows/ignored.png": {}}); err == nil {
		t.Error("empty workflow discovery accepted")
	}
}

func TestRootRejectsEscapingInput(t *testing.T) {
	dir := t.TempDir()
	if err := os.Symlink("../outside", filepath.Join(dir, "Makefile")); err != nil {
		t.Fatal(err)
	}
	root, err := os.OpenRoot(dir)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := root.Close(); err != nil {
			t.Error(err)
		}
	})
	if _, err := readFile(root.FS(), "Makefile"); err == nil {
		t.Error("root accepted a path outside the checkout")
	}
}

type failingFile struct {
	fs.File
	readErr, closeErr bool
}

func (f failingFile) Read(p []byte) (int, error) {
	if f.readErr {
		return 0, errors.New("untrusted input value")
	}
	return f.File.Read(p)
}

func (f failingFile) Close() error {
	err := f.File.Close()
	if f.closeErr {
		return errors.New("untrusted input value")
	}
	return err
}

type failingFS struct {
	fs.FS
	readErr, closeErr bool
}

func (f failingFS) Open(name string) (fs.File, error) {
	file, err := f.FS.Open(name)
	if err != nil {
		return nil, err
	}
	return failingFile{File: file, readErr: f.readErr, closeErr: f.closeErr}, nil
}

func TestReadFailures(t *testing.T) {
	for _, failures := range []failingFS{{readErr: true}, {closeErr: true}} {
		failures.FS = fstest.MapFS{"input": {Data: []byte("text")}}
		_, err := readFile(failures, "input")
		if err == nil || strings.Contains(err.Error(), "untrusted") {
			t.Errorf("readFile() error = %v, want value-free failure", err)
		}
	}
	files := fstest.MapFS{"maximum": {Data: []byte(strings.Repeat("x", 2<<20))}}
	if data, err := readFile(files, "maximum"); err != nil || len(data) != 2<<20 {
		t.Fatalf("maximum-sized input: len=%d err=%v", len(data), err)
	}
}

type failedWriter struct{}

func (failedWriter) Write([]byte) (int, error) { return 0, io.ErrClosedPipe }

func TestOutputFailure(t *testing.T) {
	if status := run(repository(t), failedWriter{}, io.Discard); status != outcome.ToolFailure {
		t.Errorf("run(broken stdout) = %d, want tool failure", status)
	}
	if status := run(fstest.MapFS{}, failedWriter{}, io.Discard); status != outcome.ToolFailure {
		t.Errorf("run(broken diagnostic output) = %d, want tool failure", status)
	}
}
