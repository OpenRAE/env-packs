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
	"slices"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/OpenRAE/env-packs/internal/report"
	"github.com/OpenRAE/env-packs/internal/testgate"
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
	os.Exit(runMain())
}

// runMain runs the command with the state of the process, and returns the
// exit status.
func runMain() int {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	exe, exeErr := os.Executable()
	return run(ctx, process{
		args:        os.Args,
		environ:     os.Environ(),
		exe:         exe,
		exeErr:      exeErr,
		tempDir:     os.TempDir(),
		runner:      testgate.ExecRunner{Env: withoutMutation(os.Environ())},
		limitMemory: limitAddressSpace,
		stdout:      os.Stdout,
		stderr:      os.Stderr,
	})
}

// limitAddressSpace limits the address space of the process to bytes. The
// processes that it starts inherit the limit.
func limitAddressSpace(bytes uint64) error {
	return syscall.Setrlimit(syscall.RLIMIT_AS, &syscall.Rlimit{Cur: bytes, Max: bytes})
}

// run runs the command and returns the exit status. A failed write to stdout
// or stderr changes the status to report.StatusFailure.
func run(ctx context.Context, p process) int {
	out := report.NewStreams(p.stdout, p.stderr)
	return out.Flush(runMode(ctx, p, out))
}

func runMode(ctx context.Context, p process, out report.Streams) int {
	flags := flag.NewFlagSet("testgate", flag.ContinueOnError)
	flags.SetOutput(out.Stderr)
	root := flags.String("root", ".", "repository `directory`")
	if err := flags.Parse(p.args[1:]); err != nil {
		return report.StatusUsage
	}
	if flags.NArg() == 0 {
		fmt.Fprintf(out.Stderr, "testgate: give a mode: mutation, regression, or exec\n")
		return report.StatusUsage
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
	fmt.Fprintf(out.Stderr, "testgate: unknown mode %q; give mutation, regression, or exec\n", mode)
	return report.StatusUsage
}

// runMutation runs the mutation gate.
func runMutation(ctx context.Context, p process, root string, args []string, out report.Streams) int {
	flags := flag.NewFlagSet("testgate mutation", flag.ContinueOnError)
	flags.SetOutput(out.Stderr)
	base := flags.String("base", "", "base `commit` of the changed lines")
	all := flags.Bool("all", false, "mutate each Go file, not only the changed lines")
	timeout := flags.Duration("timeout", time.Minute, "time limit of the tests of one mutant")
	memory := flags.Uint64("memory", defaultMemoryMiB, "address space `limit` in MiB of each process of the tests of one mutant")
	if err := flags.Parse(args); err != nil {
		return report.StatusUsage
	}
	if (*base == "") == !*all || flags.NArg() > 0 {
		fmt.Fprintf(out.Stderr, "testgate: mutation takes -base or -all, and no arguments\n")
		return report.StatusUsage
	}
	if p.exeErr != nil {
		return fail(out, fmt.Errorf("locate testgate for the exec step: %w", p.exeErr))
	}
	res, err := testgate.Mutation(ctx, p.runner, testgate.MutationOptions{
		Repo: root, Base: *base, All: *all, Exec: p.exe, TempDir: p.tempDir, Timeout: *timeout, MemoryMiB: *memory,
	})
	if err != nil {
		return fail(out, err)
	}
	fmt.Fprintf(out.Stderr, "testgate: %d mutants in %d files: %d skipped, %d killed, %d not compiled, %d escaped, %d equivalent\n",
		res.Mutants, res.Files, res.Skipped, res.Killed, res.NotCompiled, res.Escaped, res.Equivalent)
	for _, p := range res.Packages {
		score := "no score"
		if v, ok := p.Score(); ok {
			score = fmt.Sprintf("score %.1f%%", v)
		}
		fmt.Fprintf(out.Stderr, "testgate: %s: %d killed, %d survived, %d equivalent, %s\n", p.Dir, p.Killed, p.Survived, p.Equivalent, score)
	}
	return out.Findings("testgate", res.Findings)
}

// runRegression runs the regression gate.
func runRegression(ctx context.Context, p process, root string, args []string, out report.Streams) int {
	flags := flag.NewFlagSet("testgate regression", flag.ContinueOnError)
	flags.SetOutput(out.Stderr)
	base := flags.String("base", "", "base `commit` of the change")
	if err := flags.Parse(args); err != nil {
		return report.StatusUsage
	}
	if *base == "" || flags.NArg() > 0 {
		fmt.Fprintf(out.Stderr, "testgate: regression takes -base, and no arguments\n")
		return report.StatusUsage
	}
	res, err := testgate.Regression(ctx, p.runner, testgate.RegressionOptions{Repo: root, Base: *base, TempDir: p.tempDir})
	if err != nil {
		return fail(out, err)
	}
	fmt.Fprintf(out.Stderr, "testgate: %d regression tests, %d fail on the merge base\n", res.Tests, res.Proven)
	return out.Findings("testgate", res.Findings)
}

// defaultMemoryMiB is the default address space limit of each process of the
// tests of one mutant. The whole Go test suite passes with 2 GiB.
const defaultMemoryMiB = 4096

// runExec runs the exec step for the mutant that the environment names.
func runExec(ctx context.Context, p process, args []string, out report.Streams) int {
	flags := flag.NewFlagSet("testgate exec", flag.ContinueOnError)
	flags.SetOutput(out.Stderr)
	memory := flags.Uint64("memory", 0, "address space `limit` in MiB of each process of the tests, or 0 for no limit")
	if err := flags.Parse(args); err != nil {
		return report.StatusUsage
	}
	if flags.NArg() > 0 {
		fmt.Fprintf(out.Stderr, "testgate: exec takes no arguments\n")
		return report.StatusUsage
	}
	seconds, err := strconv.Atoi(lookup(p.environ, "MUTATE_TIMEOUT"))
	if err != nil {
		return fail(out, fmt.Errorf("read MUTATE_TIMEOUT: %w", err))
	}
	if *memory > 0 {
		if limitErr := p.limitMemory(*memory << 20); limitErr != nil {
			return fail(out, fmt.Errorf("limit the memory of the tests: %w", limitErr))
		}
	}
	status, err := testgate.ExecMutant(ctx, p.runner, ".", testgate.Mutant{
		Original: lookup(p.environ, "MUTATE_ORIGINAL"),
		Mutated:  lookup(p.environ, "MUTATE_CHANGED"),
		Package:  lookup(p.environ, "MUTATE_PACKAGE"),
		Timeout:  time.Duration(seconds) * time.Second,
	})
	if err != nil {
		fmt.Fprintf(out.Stderr, "testgate: %v\n", err)
	}
	return status
}

// mutationPrefix starts the names of the variables that go-mutesting sets for
// the exec step.
const mutationPrefix = "MUTATE_"

// withoutMutation returns environ without the variables of go-mutesting. The
// processes that the gates start do not get them, so a test that starts a
// process sees the same environment with and without go-mutesting.
func withoutMutation(environ []string) []string {
	return slices.DeleteFunc(slices.Clone(environ), func(kv string) bool {
		return strings.HasPrefix(kv, mutationPrefix)
	})
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

// fail writes err and returns report.StatusFailure.
func fail(out report.Streams, err error) int {
	fmt.Fprintf(out.Stderr, "testgate: %v\n", err)
	return report.StatusFailure
}
