// Command archcheck checks the architecture model of this repository, its
// design records, and its Go code (ADR 0047).
//
// Usage:
//
//	archcheck [-root dir] design
//	archcheck [-root dir] check
//	archcheck [-root dir] dsl [-write]
//
// The design mode checks the model and the design records, and does not read
// the code. Run it in the design step, before the code exists. The check mode
// also compares the code and the C4 view with the model. The dsl mode renders
// the C4 view of the model, and -write writes it to architecture/workspace.dsl.
//
// The exit status is 0 with no findings, 1 with findings, 2 for invalid
// usage, and 3 when the tool cannot complete. See
// docs/development/designs/README.md.
package main

import (
	"bytes"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"os"

	"github.com/OpenRAE/env-packs/internal/architecture"
)

const (
	exitOK       = 0
	exitFindings = 1
	exitUsage    = 2
	exitFailure  = 3
)

// The architecture files, relative to the repository root.
const (
	modelFile = "architecture/model.yaml"
	designDir = "docs/development/designs"
	dslFile   = "architecture/workspace.dsl"
)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	out := &output{stdout: stdout, stderr: stderr}
	flags := flag.NewFlagSet("archcheck", flag.ContinueOnError)
	flags.SetOutput(stderr)
	dir := flags.String("root", ".", "repository `directory`")
	if err := flags.Parse(args); err != nil {
		return exitUsage
	}
	if flags.NArg() == 0 {
		out.printf(out.stderr, "archcheck: give a mode: design, check, or dsl\n")
		return out.status(exitUsage)
	}
	mode, rest := flags.Arg(0), flags.Args()[1:]
	if mode != "design" && mode != "check" && mode != "dsl" {
		out.printf(out.stderr, "archcheck: unknown mode %q; give design, check, or dsl\n", mode)
		return out.status(exitUsage)
	}
	root, err := os.OpenRoot(*dir)
	if err != nil {
		out.printf(out.stderr, "archcheck: open the repository root: %v\n", err)
		return out.status(exitFailure)
	}
	status := runMode(mode, rest, root, *dir, out)
	if err := root.Close(); err != nil {
		out.printf(out.stderr, "archcheck: close the repository root: %v\n", err)
		return out.status(exitFailure)
	}
	return status
}

// runMode runs one mode of the command and returns the exit status.
func runMode(mode string, args []string, root *os.Root, dir string, out *output) int {
	switch mode {
	case "design":
		return out.report(designResult(root))
	case "check":
		return out.report(checkResult(root, dir))
	default:
		return runDSL(root, args, out)
	}
}

// result is the outcome of one check run.
type result struct {
	model    *architecture.Model
	findings []architecture.Finding
	err      error
}

// designResult checks the model and the design records.
func designResult(root *os.Root) result {
	m, findings, err := loadModel(root)
	if err != nil || m == nil {
		return result{findings: findings, err: err}
	}
	findings = append(findings, architecture.ValidateModel(m, modelFile)...)
	designs, recordFindings, err := architecture.LoadDesigns(root.FS(), designDir)
	if err != nil {
		return result{err: err}
	}
	findings = append(findings, recordFindings...)
	findings = append(findings, architecture.CheckDesigns(m, modelFile, designs)...)
	return result{model: m, findings: findings}
}

// checkResult adds the code checks and the C4 view check to designResult.
// The directory dir is the same as root, for the Go package loader.
func checkResult(root *os.Root, dir string) result {
	r := designResult(root)
	if r.err != nil || r.model == nil {
		return r
	}
	graph, err := architecture.LoadGraph(dir)
	if err != nil {
		return result{err: err}
	}
	r.findings = append(r.findings, architecture.CheckCode(r.model, modelFile, graph)...)
	view, err := root.ReadFile(dslFile)
	if err != nil && !errors.Is(err, fs.ErrNotExist) {
		return result{err: fmt.Errorf("read the C4 view: %w", err)}
	}
	if !bytes.Equal(view, architecture.RenderDSL(r.model)) {
		r.findings = append(r.findings, architecture.Finding{
			Location: dslFile,
			Rule:     architecture.RuleC4View,
			Message:  "the C4 view differs from the rendered architecture model",
			Fix:      "Run make go-arch-dsl to render the view again, and commit the result.",
		})
	}
	return r
}

// loadModel reads and decodes the model. A file that cannot be read is an
// error, and a model that does not decode is a finding.
func loadModel(root *os.Root) (*architecture.Model, []architecture.Finding, error) {
	data, err := root.ReadFile(modelFile)
	if err != nil {
		return nil, nil, fmt.Errorf("read the model: %w", err)
	}
	m, findings := parseModel(data)
	return m, findings, nil
}

// parseModel decodes the model. A decode failure is a finding about the model.
func parseModel(data []byte) (*architecture.Model, []architecture.Finding) {
	m, err := architecture.ParseModel(data)
	if err != nil {
		return nil, []architecture.Finding{{
			Location: modelFile,
			Rule:     architecture.RuleModel,
			Message:  err.Error(),
			Fix:      "Correct the YAML of the model. Use only the fields of the existing model and the design-record README.",
		}}
	}
	return m, nil
}

// runDSL renders the C4 view. With -write, it writes the view file.
func runDSL(root *os.Root, args []string, out *output) int {
	flags := flag.NewFlagSet("archcheck dsl", flag.ContinueOnError)
	flags.SetOutput(out.stderr)
	write := flags.Bool("write", false, "write "+dslFile+" instead of standard output")
	if err := flags.Parse(args); err != nil {
		return exitUsage
	}
	m, findings, err := loadModel(root)
	if err == nil && m != nil {
		findings = architecture.ValidateModel(m, modelFile)
	}
	if err != nil || len(findings) > 0 {
		return out.report(result{findings: findings, err: err})
	}
	view := architecture.RenderDSL(m)
	if !*write {
		out.write(out.stdout, view)
		return out.status(exitOK)
	}
	if err := root.WriteFile(dslFile, view, 0o644); err != nil {
		out.printf(out.stderr, "archcheck: write the C4 view: %v\n", err)
		return out.status(exitFailure)
	}
	return out.status(exitOK)
}

// output writes to the standard streams. It keeps the first write error, so
// that a failed write changes the exit status instead of being lost.
type output struct {
	stdout io.Writer
	stderr io.Writer
	err    error
}

func (o *output) printf(w io.Writer, format string, args ...any) {
	if o.err == nil {
		_, o.err = fmt.Fprintf(w, format, args...)
	}
}

func (o *output) write(w io.Writer, data []byte) {
	if o.err == nil {
		_, o.err = w.Write(data)
	}
}

// status returns code, or exitFailure after a failed write.
func (o *output) status(code int) int {
	if o.err != nil {
		return exitFailure
	}
	return code
}

// report writes the findings and returns the exit status.
func (o *output) report(r result) int {
	if r.err != nil {
		o.printf(o.stderr, "archcheck: %v\n", r.err)
		return o.status(exitFailure)
	}
	findings := architecture.SortFindings(r.findings)
	for _, f := range findings {
		o.printf(o.stdout, "%s\n", f)
	}
	o.printf(o.stderr, "archcheck: %d findings\n", len(findings))
	if len(findings) > 0 {
		return o.status(exitFindings)
	}
	return o.status(exitOK)
}
