package main

import (
	"bytes"
	"io"
	"io/fs"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/OpenRAE/env-packs/internal/outcome"
)

func TestAddRejectsMalformedInput(t *testing.T) {
	input := repositoryInput{Documents: map[string]any{}, Text: map[string]string{}}
	if err := input.add(fstest.MapFS{"config.yml": {Data: []byte("[broken")}}, "config.yml"); err == nil {
		t.Error("add accepted malformed configuration")
	}
	if _, exists := input.Documents["config.yml"]; exists {
		t.Error("failed input entered documents")
	}
}

type selectionFS struct {
	fs.FS
	directory string
	count     int
}

func (f selectionFS) ReadDir(name string) ([]fs.DirEntry, error) {
	entries, err := fs.ReadDir(f.FS, name)
	if err == nil && name == f.directory && len(entries) > f.count {
		entries = entries[:f.count]
	}
	return entries, err
}

func TestCollectorDiscoveryPopulation(t *testing.T) {
	repo := repository(t)
	_, err := collect(selectionFS{FS: repo, directory: ".github/workflows", count: 0})
	if err == nil || !strings.Contains(err.Error(), `cannot discover inputs in ".github/workflows"`) {
		t.Fatalf("collect(empty discovery) error = %v, want workflow discovery refusal", err)
	}
	if _, err := collect(selectionFS{FS: repo, directory: "requirements", count: 1}); err != nil {
		t.Fatalf("collect(one discovered requirement) error = %v, want collection success", err)
	}
}

type deniedDirectoryFS struct{ fs.FS }

func (f deniedDirectoryFS) Open(name string) (fs.File, error) {
	if name == "docs/public/decisions" {
		return nil, fs.ErrPermission
	}
	return f.FS.Open(name)
}

func TestDirectoryInspectionFailure(t *testing.T) {
	_, err := collect(deniedDirectoryFS{FS: repository(t)})
	if err == nil || err.Error() != "cannot inspect public documentation directories" {
		t.Fatalf("collect(inaccessible directory) error = %v, want refusal", err)
	}
}

type countedFile struct {
	fs.File
	read *int
}

func (f countedFile) Read(p []byte) (int, error) {
	n, err := f.File.Read(p)
	*f.read += n
	return n, err
}

type countedFS struct {
	fs.FS
	read *int
}

func (f countedFS) Open(name string) (fs.File, error) {
	file, err := f.FS.Open(name)
	if err != nil {
		return nil, err
	}
	return countedFile{File: file, read: f.read}, nil
}

func TestReadBudgetStopsAfterOversizeDetection(t *testing.T) {
	read := 0
	repo := countedFS{FS: fstest.MapFS{"large": {Data: []byte(strings.Repeat("x", 4<<20))}}, read: &read}
	if _, err := readFile(repo, "large"); err == nil {
		t.Error("oversized input accepted")
	}
	if read != (2<<20)+1 {
		t.Errorf("read %d bytes, want only budget plus one detection byte", read)
	}
}

type replacedFS struct {
	fs.FS
	name, text string
}

func (f replacedFS) Open(name string) (fs.File, error) {
	if name == f.name {
		return fstest.MapFS{name: {Data: []byte(f.text)}}.Open(name)
	}
	return f.FS.Open(name)
}

func TestUnencodableInputFailsWithoutPartialJSON(t *testing.T) {
	repo := replacedFS{FS: repository(t), name: ".ground-control.yaml", text: "value: .nan\n"}
	var output bytes.Buffer
	if status := run(repo, &output, io.Discard); status != outcome.ToolFailure {
		t.Errorf("run(unencodable facts) = %d, want tool failure", status)
	}
	if output.Len() != 0 {
		t.Error("unencodable facts produced partial JSON")
	}
}
