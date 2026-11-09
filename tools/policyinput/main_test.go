package main

import (
	"io/fs"
	"os"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/google/go-cmp/cmp"
)

func repository(t *testing.T) fs.FS {
	t.Helper()
	root, err := os.OpenRoot("../..")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := root.Close(); err != nil {
			t.Error(err)
		}
	})
	return root.FS()
}

func TestShellCommands(t *testing.T) {
	for _, tc := range []struct {
		name, script string
		want         [][]string
	}{
		{"wrapped", "python -m pip install --require-hashes \\\n -r requirements/docs.txt\n", [][]string{{"python", "-m", "pip", "install", "--require-hashes", "-r", "requirements/docs.txt"}}},
		{"quotes and comment", "# pip install unsafe\npip3 install '--no-deps' -e \".\" # comment\n", [][]string{{"pip3", "install", "--no-deps", "-e", "."}}},
		{"two commands", "pip install a; pip install b", [][]string{{"pip", "install", "a"}, {"pip", "install", "b"}}},
		{"expansion stays data", "pip install \"$PACKAGE\"", [][]string{{"pip", "install", "$PACKAGE"}}},
		{"wheel glob", "pip install dist/*.whl", [][]string{{"pip", "install", "dist/*.whl"}}},
		{"assignment and no arguments", "VALUE=fact\ntrue", [][]string{{"true"}}},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := shellCommands(tc.script)
			if err != nil {
				t.Fatalf("shellCommands() error = %v", err)
			}
			if diff := cmp.Diff(tc.want, got); diff != "" {
				t.Errorf("shellCommands() mismatch (-want +got):\n%s", diff)
			}
		})
	}
	if _, err := shellCommands("pip install 'unterminated"); err == nil {
		t.Error("shellCommands(unterminated quote) error = nil, want refusal")
	}
}

func TestReadInput(t *testing.T) {
	for _, tc := range []struct {
		name, file, content string
		want                any
		bad                 bool
	}{
		{"workflow on", "w.yml", "on:\n  pull_request:\npermissions: read-all\n", map[string]any{"on": map[string]any{"pull_request": nil}, "permissions": "read-all"}, false},
		{"duplicate", "w.yaml", "a: 1\na: 2\n", nil, true},
		{"multiple", "w.yml", "a: 1\n---\na: 2\n", nil, true},
		{"recursive alias", "w.yml", "a: &a [*a]\n", nil, true},
		{"toml", "mise.toml", "[tools]\nconftest='0.71.1'\n", map[string]any{"tools": map[string]any{"conftest": "0.71.1"}}, false},
		{"bad toml", "mise.toml", "[", nil, true},
		{"json", "config.json", `{"enabled":true}`, map[string]any{"enabled": true}, false},
		{"yaml in json", "config.json", "enabled: true", nil, true},
		{"json duplicate", "config.json", `{"enabled":true,"enabled":false}`, nil, true},
		{"json trailing", "config.json", `{"enabled":true} {}`, nil, true},
		{"json null", "config.json", `null`, nil, true},
		{"empty", "w.yml", "", nil, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			got, err := decodeInput(tc.file, []byte(tc.content))
			if (err != nil) != tc.bad {
				t.Fatalf("decodeInput() error = %v, want bad=%t", err, tc.bad)
			}
			if !tc.bad {
				if diff := cmp.Diff(tc.want, got); diff != "" {
					t.Errorf("decodeInput() mismatch (-want +got):\n%s", diff)
				}
			}
		})
	}
}

func TestReadFile(t *testing.T) {
	files := fstest.MapFS{"good": {Data: []byte("text")}, "large": {Data: []byte(strings.Repeat("x", 2<<20+1))}}
	got, err := readFile(files, "good")
	if err != nil || string(got) != "text" {
		t.Fatalf("readFile(good) = %q, %v, want text", got, err)
	}
	for _, name := range []string{"missing", "large", "../outside"} {
		if _, err := readFile(files, name); err == nil {
			t.Errorf("readFile(%q) error = nil, want refusal", name)
		}
	}
}

func TestCollectorFailsClosed(t *testing.T) {
	if _, err := collect(fstest.MapFS{}); err == nil {
		t.Error("collect(empty repository) error = nil, want refusal")
	}
	// The real repository proves that every selected input reaches the envelope.
	root := repository(t)
	got, err := collect(root)
	if err != nil {
		t.Fatalf("collect(repository) error = %v", err)
	}
	if got.Documents[".github/workflows/ci.yml"] == nil || !strings.Contains(got.Text["Makefile"], "devmain:") || len(got.Commands) == 0 {
		t.Fatal("collect(repository) omitted workflows, maintained text, or shell commands")
	}
	for _, name := range []string{".ground-control.yaml", ".github/workflows/ci.yml", "Makefile", "docs/public/index.md"} {
		if _, err := collect(hiddenFS{FS: root, hidden: name}); err == nil {
			t.Errorf("collect(without %q) error = nil, want refusal", name)
		}
	}
}

type hiddenFS struct {
	fs.FS
	hidden string
}

func (f hiddenFS) Open(name string) (fs.File, error) {
	if name == f.hidden {
		return nil, fs.ErrNotExist
	}
	return f.FS.Open(name)
}

func (f hiddenFS) ReadDir(name string) ([]fs.DirEntry, error) {
	entries, err := fs.ReadDir(f.FS, name)
	var visible []fs.DirEntry
	for _, entry := range entries {
		if name+"/"+entry.Name() != f.hidden {
			visible = append(visible, entry)
		}
	}
	return visible, err
}
