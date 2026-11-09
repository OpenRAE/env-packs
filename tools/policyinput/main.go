// Command policyinput supplies contained repository facts to local Rego policies.
// It does not evaluate policy or execute the shell commands that it parses.
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"maps"
	"os"
	"path"
	"slices"
	"strings"

	"github.com/OpenRAE/env-packs/internal/outcome"
	"github.com/OpenRAE/env-packs/internal/report"
	"github.com/OpenRAE/env-packs/internal/strictyaml"
	"github.com/OpenRAE/env-packs/internal/terminal"
	"github.com/pelletier/go-toml/v2"
	"mvdan.cc/sh/v3/syntax"
)

func main() {
	root, err := os.OpenRoot(".")
	if err != nil {
		os.Exit(outcome.ToolFailure)
	}
	status := run(root.FS(), os.Stdout, os.Stderr)
	if root.Close() != nil {
		status = outcome.ToolFailure
	}
	os.Exit(status)
}

func run(repo fs.FS, stdout, stderr io.Writer) int {
	out := outcome.NewStreams(stdout, stderr)
	input, err := collect(repo)
	if err != nil {
		findings := []report.Finding{{Location: "repository", Rule: "policy-input", Message: terminal.Quote(err.Error()), Fix: "Restore the required readable inputs and valid syntax."}}
		report.Write(out, "policyinput", findings)
		return out.Flush(outcome.ToolFailure)
	}
	if err := json.NewEncoder(out.Stdout).Encode(input); err != nil {
		return out.Flush(outcome.ToolFailure)
	}
	return out.Flush(outcome.OK)
}

type repositoryInput struct {
	Documents   map[string]any    `json:"documents"`
	Text        map[string]string `json:"text"`
	Commands    []command         `json:"commands"`
	Directories []string          `json:"directories"`
}

type command struct {
	File string   `json:"file"`
	Job  string   `json:"job"`
	Args []string `json:"args"`
}

// collect reads fixed inputs and the discovered workflows and public pages.
func collect(repo fs.FS) (repositoryInput, error) {
	input := repositoryInput{Documents: map[string]any{}, Text: map[string]string{}}
	names := []string{".ground-control.yaml", ".readthedocs.yaml", ".github/dependabot.yml", ".github/codeql/codeql-config.yml", "release-please-config.json", "pyproject.toml", "mise.toml", "Makefile", "README.md", "CONTRIBUTING.md", ".gc/plan-rules.md", "docs/README.md", "docs/public/conf.py", "docs/development/ci.md", "docs/development/scrub-policy.md", "docs/decisions/adrs/README.md", "packs/techvault/README.md", "go.mod", "go.sum", "sonar-project.properties"}
	for _, dir := range []string{".github/workflows", "docs/public", "requirements"} {
		found, err := discover(repo, dir)
		if err != nil || len(found) == 0 {
			return input, fmt.Errorf("cannot discover inputs in %q", dir)
		}
		names = append(names, found...)
	}
	for _, required := range []string{".github/workflows/ci.yml", ".github/workflows/codeql.yml", ".github/workflows/scorecard.yml", ".github/workflows/release-please.yml", ".github/workflows/pack-distribution.yml", ".github/workflows/pr-title.yml", "docs/public/index.md"} {
		if _, err := readFile(repo, required); err != nil {
			return input, err
		}
	}
	for _, name := range names {
		if err := input.add(repo, name); err != nil {
			return input, err
		}
	}
	if _, err := fs.Stat(repo, "docs/public/decisions"); err == nil {
		input.Directories = append(input.Directories, "docs/public/decisions")
	} else if !errors.Is(err, fs.ErrNotExist) {
		return input, errors.New("cannot inspect public documentation directories")
	}
	return input, nil
}

func discover(repo fs.FS, dir string) ([]string, error) {
	var names []string
	err := fs.WalkDir(repo, dir, func(name string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.Type()&fs.ModeSymlink != 0 {
			return errors.New("symlink in policy inputs")
		}
		if entry.IsDir() {
			if path.Base(name) == "_build" {
				return fs.SkipDir
			}
			return nil
		}
		switch path.Ext(name) {
		case ".yaml", ".yml", ".md", ".txt", ".in":
			names = append(names, name)
		}
		return nil
	})
	return names, err
}

func (input *repositoryInput) add(repo fs.FS, name string) error {
	data, err := readFile(repo, name)
	if err != nil {
		return err
	}
	input.Text[name] = string(data)
	switch path.Ext(name) {
	case ".yaml", ".yml", ".json", ".toml":
		doc, err := decodeInput(name, data)
		if err != nil {
			return err
		}
		input.Documents[name] = doc
		if strings.HasPrefix(name, ".github/workflows/") {
			return input.addCommands(name, doc)
		}
	}
	return nil
}

func (input *repositoryInput) addCommands(name string, doc any) error {
	workflow, ok := doc.(map[string]any)
	if !ok {
		return errors.New("workflow must be an object")
	}
	jobs, ok := workflow["jobs"].(map[string]any)
	if !ok {
		return errors.New("workflow jobs must be an object")
	}
	for _, jobName := range slices.Sorted(maps.Keys(jobs)) {
		if err := input.addJobCommands(name, jobName, jobs[jobName]); err != nil {
			return err
		}
	}
	return nil
}

func (input *repositoryInput) addJobCommands(name, jobName string, rawJob any) error {
	job, ok := rawJob.(map[string]any)
	if !ok {
		return errors.New("workflow job must be an object")
	}
	if _, reusable := job["uses"]; reusable {
		return nil
	}
	steps, ok := job["steps"].([]any)
	if !ok {
		return errors.New("workflow steps must be an array")
	}
	for _, rawStep := range steps {
		step, ok := rawStep.(map[string]any)
		if !ok {
			return errors.New("workflow step must be an object")
		}
		run, ok := step["run"].(string)
		if !ok {
			continue
		}
		commands, err := shellCommands(run)
		if err != nil {
			return fmt.Errorf("invalid shell syntax in %q job %q", name, jobName)
		}
		for _, args := range commands {
			input.Commands = append(input.Commands, command{File: name, Job: jobName, Args: args})
		}
	}
	return nil
}

func decodeInput(name string, data []byte) (any, error) {
	var doc map[string]any
	var err error
	switch {
	case path.Ext(name) == ".toml":
		err = toml.Unmarshal(data, &doc)
	case path.Ext(name) == ".json" && !json.Valid(data):
		err = errors.New("invalid JSON syntax")
	default:
		err = strictyaml.Decode(data, &doc)
	}
	if err != nil || doc == nil {
		return nil, fmt.Errorf("invalid structured input %q", name)
	}
	return doc, nil
}

func readFile(repo fs.FS, name string) ([]byte, error) {
	f, err := repo.Open(name)
	if err != nil {
		return nil, fmt.Errorf("cannot open input %q", name)
	}
	data, readErr := io.ReadAll(io.LimitReader(f, (2<<20)+1))
	closeErr := f.Close()
	if readErr != nil || closeErr != nil || len(data) > 2<<20 {
		return nil, fmt.Errorf("cannot read bounded input %q", name)
	}
	return data, nil
}

func shellCommands(script string) ([][]string, error) {
	file, err := syntax.NewParser(syntax.Variant(syntax.LangBash)).Parse(strings.NewReader(script), "workflow")
	if err != nil {
		return nil, errors.New("invalid shell syntax")
	}
	var commands [][]string
	var printErr error
	syntax.Walk(file, func(node syntax.Node) bool {
		call, ok := node.(*syntax.CallExpr)
		if !ok || len(call.Args) == 0 {
			return true
		}
		var args []string
		for _, word := range call.Args {
			text, err := wordText(word.Parts)
			if err != nil {
				printErr = err
				return false
			}
			args = append(args, text)
		}
		commands = append(commands, args)
		return true
	})
	return commands, printErr
}

func wordText(parts []syntax.WordPart) (string, error) {
	var text strings.Builder
	for _, part := range parts {
		switch p := part.(type) {
		case *syntax.Lit:
			text.WriteString(p.Value)
		case *syntax.SglQuoted:
			text.WriteString(p.Value)
		case *syntax.DblQuoted:
			value, err := wordText(p.Parts)
			if err != nil {
				return "", err
			}
			text.WriteString(value)
		default:
			var b bytes.Buffer
			if err := syntax.NewPrinter().Print(&b, part); err != nil {
				return "", errors.New("unsupported shell expression")
			}
			text.WriteString(b.String())
		}
	}
	return text.String(), nil
}
