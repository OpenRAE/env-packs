// Command testgate runs the test gates of ADR 0047: mutation testing on the
// changed Go lines, and the proof that each new regression test fails on the
// code before its fix.
//
// Usage:
//
//	testgate [-root dir] mutation -base commit [-timeout duration] [-memory mib]
//	testgate [-root dir] mutation -all [-timeout duration] [-memory mib]
//	testgate [-root dir] regression -base commit
//	testgate exec [-memory mib]
//
// The mutation and regression modes exit with status 0 with no findings, 1
// with findings, 2 for invalid usage, and 3 when the tool cannot complete.
//
// go-mutesting runs the exec mode for each mutant, with the environment
// variables MUTATE_ORIGINAL, MUTATE_CHANGED, MUTATE_PACKAGE, and
// MUTATE_TIMEOUT. The exec mode exits with status 0 when a test kills the
// mutant, 1 when the mutant survives, 2 when the mutant does not compile,
// and 3 when the tool cannot complete.
//
// The exec mode limits the address space of each process of the test run to
// -memory MiB, so that a mutant that allocates without end stops with an
// out-of-memory error. Linux enforces the limit. See
// docs/development/designs/0002-test-gates.md.
package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/OpenRAE/env-packs/internal/testgate"
)

const (
	exitOK       = 0
	exitFindings = 1
	exitUsage    = 2
	exitFailure  = 3
)

// process is what the command takes from the operating system.
type process struct {
	// args is the command line, which starts with the program name.
	args []string
	// environ is the environment, in the form of os.Environ.
	environ []string
	// exe and exeErr are the results of os.Executable.
	exe    string
	exeErr error
	// tempDir is the directory for temporary files.
	tempDir string
	// runner runs git, go, and go-mutesting.
	runner testgate.Runner
	// limitMemory limits the address space of the process and of the
	// processes that it starts to the given number of bytes.
	limitMemory func(bytes uint64) error
	// stdout and stderr are the output streams.
	stdout, stderr io.Writer
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	exe, exeErr := os.Executable()
	status := run(ctx, process{
		args:        os.Args,
		environ:     os.Environ(),
		exe:         exe,
		exeErr:      exeErr,
		tempDir:     os.TempDir(),
		runner:      testgate.ExecRunner{Env: os.Environ()},
		limitMemory: limitAddressSpace,
		stdout:      os.Stdout,
		stderr:      os.Stderr,
	})
	stop()
	os.Exit(status)
}

// limitAddressSpace limits the address space of the process to bytes. The
// processes that it starts inherit the limit.
func limitAddressSpace(bytes uint64) error {
	return syscall.Setrlimit(syscall.RLIMIT_AS, &syscall.Rlimit{Cur: bytes, Max: bytes})
}

// run runs the command and returns the exit status.
func run(ctx context.Context, p process) int {
	out := &output{stdout: p.stdout, stderr: p.stderr}
	flags := flag.NewFlagSet("testgate", flag.ContinueOnError)
	flags.SetOutput(p.stderr)
	root := flags.String("root", ".", "repository `directory`")
	if err := flags.Parse(p.args[1:]); err != nil {
		return exitUsage
	}
	if flags.NArg() == 0 {
		out.printf(out.stderr, "testgate: give a mode: mutation, regression, or exec\n")
		return out.status(exitUsage)
	}
	mode, rest := flags.Arg(0), flags.Args()[1:]
	switch mode {
	case "mutation":
		return runMutation(ctx, p, *root, rest, out)
	case "regression":
		return runRegression(ctx, p, *root, rest, out)
	case "exec":
		return runExec(ctx, p, rest, out)
	}
	out.printf(out.stderr, "testgate: unknown mode %q; give mutation, regression, or exec\n", mode)
	return out.status(exitUsage)
}

// runMutation runs the mutation gate.
func runMutation(ctx context.Context, p process, root string, args []string, out *output) int {
	flags := flag.NewFlagSet("testgate mutation", flag.ContinueOnError)
	flags.SetOutput(p.stderr)
	base := flags.String("base", "", "base `commit` of the changed lines")
	all := flags.Bool("all", false, "mutate each Go file, not only the changed lines")
	timeout := flags.Duration("timeout", time.Minute, "time limit of the tests of one mutant")
	memory := flags.Uint64("memory", defaultMemoryMiB, "address space `limit` in MiB of each process of the tests of one mutant")
	if err := flags.Parse(args); err != nil {
		return exitUsage
	}
	if (*base == "") == !*all || flags.NArg() > 0 {
		out.printf(out.stderr, "testgate: mutation takes -base or -all, and no arguments\n")
		return out.status(exitUsage)
	}
	if p.exeErr != nil {
		return out.fail(fmt.Errorf("locate testgate for the exec step: %w", p.exeErr))
	}
	res, err := testgate.Mutation(ctx, p.runner, testgate.MutationOptions{
		Repo: root, Base: *base, All: *all, Exec: p.exe, TempDir: p.tempDir, Timeout: *timeout, MemoryMiB: *memory,
	})
	if err != nil {
		return out.fail(err)
	}
	out.printf(out.stderr, "testgate: %d mutants in %d files: %d skipped, %d killed, %d not compiled, %d escaped, %d equivalent\n",
		res.Mutants, res.Files, res.Skipped, res.Killed, res.NotCompiled, res.Escaped, res.Equivalent)
	for _, p := range res.Packages {
		score := "no score"
		if v, ok := p.Score(); ok {
			score = fmt.Sprintf("score %.1f%%", v)
		}
		out.printf(out.stderr, "testgate: %s: %d killed, %d survived, %d equivalent, %s\n", p.Dir, p.Killed, p.Survived, p.Equivalent, score)
	}
	return out.report(res.Findings)
}

// runRegression runs the regression gate.
func runRegression(ctx context.Context, p process, root string, args []string, out *output) int {
	flags := flag.NewFlagSet("testgate regression", flag.ContinueOnError)
	flags.SetOutput(p.stderr)
	base := flags.String("base", "", "base `commit` of the change")
	if err := flags.Parse(args); err != nil {
		return exitUsage
	}
	if *base == "" || flags.NArg() > 0 {
		out.printf(out.stderr, "testgate: regression takes -base, and no arguments\n")
		return out.status(exitUsage)
	}
	res, err := testgate.Regression(ctx, p.runner, testgate.RegressionOptions{Repo: root, Base: *base, TempDir: p.tempDir})
	if err != nil {
		return out.fail(err)
	}
	out.printf(out.stderr, "testgate: %d regression tests, %d fail on the merge base\n", res.Tests, res.Proven)
	return out.report(res.Findings)
}

// defaultMemoryMiB is the default address space limit of each process of the
// tests of one mutant. The whole Go test suite passes with 2 GiB.
const defaultMemoryMiB = 4096

// runExec runs the exec step for the mutant that the environment names.
func runExec(ctx context.Context, p process, args []string, out *output) int {
	flags := flag.NewFlagSet("testgate exec", flag.ContinueOnError)
	flags.SetOutput(p.stderr)
	memory := flags.Uint64("memory", 0, "address space `limit` in MiB of each process of the tests, or 0 for no limit")
	if err := flags.Parse(args); err != nil {
		return exitUsage
	}
	if flags.NArg() > 0 {
		out.printf(out.stderr, "testgate: exec takes no arguments\n")
		return out.status(exitUsage)
	}
	seconds, err := strconv.Atoi(lookup(p.environ, "MUTATE_TIMEOUT"))
	if err != nil {
		return out.fail(fmt.Errorf("read MUTATE_TIMEOUT: %w", err))
	}
	if *memory > 0 {
		if limitErr := p.limitMemory(*memory << 20); limitErr != nil {
			return out.fail(fmt.Errorf("limit the memory of the tests: %w", limitErr))
		}
	}
	status, err := testgate.ExecMutant(ctx, p.runner, ".", testgate.Mutant{
		Original: lookup(p.environ, "MUTATE_ORIGINAL"),
		Mutated:  lookup(p.environ, "MUTATE_CHANGED"),
		Package:  lookup(p.environ, "MUTATE_PACKAGE"),
		Timeout:  time.Duration(seconds) * time.Second,
	})
	if err != nil {
		return out.fail(err)
	}
	return status
}

// lookup returns the value of the last entry for key in environ, or the empty
// string.
func lookup(environ []string, key string) string {
	value := ""
	for _, kv := range environ {
		if v, ok := strings.CutPrefix(kv, key+"="); ok {
			value = v
		}
	}
	return value
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

// status returns code, or exitFailure after a failed write.
func (o *output) status(code int) int {
	if o.err != nil {
		return exitFailure
	}
	return code
}

// fail writes err and returns exitFailure.
func (o *output) fail(err error) int {
	o.printf(o.stderr, "testgate: %v\n", err)
	return exitFailure
}

// report writes the findings and returns the exit status.
func (o *output) report(findings []testgate.Finding) int {
	findings = testgate.SortFindings(findings)
	for _, f := range findings {
		o.printf(o.stdout, "%s\n", f)
	}
	o.printf(o.stderr, "testgate: %d findings\n", len(findings))
	if len(findings) > 0 {
		return o.status(exitFindings)
	}
	return o.status(exitOK)
}
