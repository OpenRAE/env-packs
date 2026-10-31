package testgate

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"maps"
	"os"
	"path"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"time"
)

// mutestingConfig is the go-mutesting configuration of the gate: a JSON
// report, and no rule that skips a file.
const mutestingConfig = `json_output: true
html_output: false
silent_mode: true
skip_without_test: false
skip_with_build_tags: false
`

// MutationOptions configure one run of the mutation gate.
type MutationOptions struct {
	// Repo is the root directory of the git repository and the Go module.
	Repo string
	// Base is the base revision. The gate does not use it with All.
	Base string
	// All selects each Go file of HEAD that is not a test file, instead of
	// the changed lines.
	All bool
	// Exec is the path of the testgate program. go-mutesting runs
	// "Exec exec" for each mutant.
	Exec string
	// TempDir is the directory for the temporary files of the run.
	TempDir string
	// Timeout is the time limit of the tests of one mutant.
	Timeout time.Duration
	// MemoryMiB is the address space limit in MiB of each process of the
	// tests of one mutant.
	MemoryMiB uint64
}

// MutationResult is the outcome of one run of the mutation gate.
type MutationResult struct {
	// Findings are the surviving mutants and the defects of mutation.yaml.
	// With All, they also include the stale records.
	Findings []Finding
	// Files is the number of files that the gate mutates.
	Files int
	// Mutants counts the mutants of the go-mutesting report.
	Mutants int
	// Skipped counts the mutants that change no changed line, or that do not
	// change the source. The exec step does not test them.
	Skipped int
	// Killed counts the tested mutants that a test kills.
	Killed int
	// NotCompiled counts the tested mutants that do not compile.
	NotCompiled int
	// Escaped counts the tested mutants that each test passes with, and
	// Equivalent counts those of them that a record matches, or that only
	// change a result beside a non-nil error.
	Escaped, Equivalent int
	// Packages are the scores of the package directories, sorted by
	// directory.
	Packages []PackageScore
}

// A PackageScore counts the tested mutants of the files in one directory.
type PackageScore struct {
	// Dir is the directory, relative to the repository root.
	Dir string
	// Killed counts the mutants that a test kills, Survived the mutants that
	// are findings, and Equivalent the equivalent mutants.
	Killed, Survived, Equivalent int
}

// Score returns the killed mutants as a percentage of the killed and the
// surviving mutants. It returns false when the package has no such mutant.
func (p PackageScore) Score() (float64, bool) {
	tested := p.Killed + p.Survived
	if tested == 0 {
		return 0, false
	}
	return 100 * float64(p.Killed) / float64(tested), true
}

// scores collects the package scores of one run, by directory.
type scores map[string]*PackageScore

// of returns the score of the directory of file.
func (s scores) of(file string) *PackageScore {
	dir := path.Dir(file)
	if s[dir] == nil {
		s[dir] = &PackageScore{Dir: dir}
	}
	return s[dir]
}

// sorted returns the scores sorted by directory.
func (s scores) sorted() []PackageScore {
	var list []PackageScore
	for _, dir := range slices.Sorted(maps.Keys(s)) {
		list = append(list, *s[dir])
	}
	return list
}

// Mutation runs the mutation gate.
func Mutation(ctx context.Context, r Runner, opts MutationOptions) (MutationResult, error) {
	targets, changes, err := mutationTargets(ctx, r, opts)
	if err != nil {
		return MutationResult{}, err
	}
	if len(targets) == 0 {
		return MutationResult{}, nil
	}
	if strings.ContainsAny(opts.Exec, " \t\n") {
		return MutationResult{}, fmt.Errorf("the path of testgate, %q, has white space, but go-mutesting splits its exec command at spaces", opts.Exec)
	}
	var res MutationResult
	err = withWorktree(ctx, r, opts.Repo, opts.TempDir, "HEAD", func(tree string) error {
		var treeErr error
		res, treeErr = mutateTree(ctx, r, tree, targets, changes, opts)
		return treeErr
	})
	return res, err
}

// mutateTree runs go-mutesting in the worktree tree, and evaluates its report
// with the records of the worktree.
func mutateTree(ctx context.Context, r Runner, tree string, targets []string, changes Changes, opts MutationOptions) (MutationResult, error) {
	rep, err := runMutesting(ctx, r, tree, targets, changes, opts)
	if err != nil {
		return MutationResult{}, err
	}
	data, err := fs.ReadFile(os.DirFS(tree), RecordsFile)
	if err != nil {
		return MutationResult{}, fmt.Errorf("read %s: %w", RecordsFile, err)
	}
	records, err := ParseRecords(data)
	if err != nil {
		return MutationResult{}, err
	}
	return evaluate(rep, targets, changes, records, opts.All)
}

// mutationTargets returns the files to mutate and their changed lines. With
// All, it returns each file of HEAD that the gate mutates, and no lines.
func mutationTargets(ctx context.Context, r Runner, opts MutationOptions) ([]string, Changes, error) {
	if opts.All {
		out, err := runOK(ctx, r, Command{Dir: opts.Repo, Name: "git", Args: []string{"ls-tree", "-r", "-z", "--name-only", "HEAD"}})
		if err != nil {
			return nil, nil, err
		}
		return slices.DeleteFunc(strings.Split(string(out), "\x00"), func(name string) bool { return !mutable(name) }), nil, nil
	}
	base, err := revParse(ctx, r, opts.Repo, opts.Base)
	if err != nil {
		return nil, nil, err
	}
	changes, err := changedLines(ctx, r, opts.Repo, base, "*.go")
	if err != nil {
		return nil, nil, err
	}
	var targets []string
	for name := range changes {
		if mutable(name) {
			targets = append(targets, name)
		}
	}
	slices.Sort(targets)
	return targets, changes, nil
}

// runMutesting runs go-mutesting on the targets in the worktree tree, with
// the gate as its exec command, and returns the report.
func runMutesting(ctx context.Context, r Runner, tree string, targets []string, changes Changes, opts MutationOptions) (report, error) {
	config := filepath.Join(tree, ".testgate-go-mutesting.yaml")
	if err := os.WriteFile(config, []byte(mutestingConfig), 0o600); err != nil {
		return report{}, fmt.Errorf("write the go-mutesting configuration: %w", err)
	}
	if !opts.All {
		data, _ := json.Marshal(changes)
		if err := os.WriteFile(filepath.Join(tree, linesFile), data, 0o600); err != nil {
			return report{}, fmt.Errorf("write the changed lines: %w", err)
		}
	}
	args := append([]string{
		"--config=" + config,
		"--exec=" + opts.Exec + " exec -memory " + strconv.FormatUint(opts.MemoryMiB, 10),
		"--exec-timeout=" + strconv.Itoa(int(opts.Timeout/time.Second)),
		"--",
	}, targets...)
	if _, err := runOK(ctx, r, Command{Dir: tree, Name: "go-mutesting", Args: args}); err != nil {
		return report{}, err
	}
	data, err := fs.ReadFile(os.DirFS(tree), "report.json")
	if err != nil {
		return report{}, fmt.Errorf("read the go-mutesting report: %w", err)
	}
	rep, err := parseReport(data)
	if err != nil {
		return report{}, err
	}
	if rep.Stats.Errored > 0 {
		return report{}, fmt.Errorf("the exec step failed for %d mutants; see the output of go-mutesting", rep.Stats.Errored)
	}
	return rep, nil
}

// evaluate turns the escaped mutants of the report into findings. Without
// all, it keeps only the mutants on the changed lines. It counts the killed
// mutants that the exec step skipped.
func evaluate(rep report, targets []string, changes Changes, records Records, all bool) (MutationResult, error) {
	res := MutationResult{
		Findings:    records.Check(),
		Files:       len(targets),
		Mutants:     rep.Stats.Total,
		NotCompiled: rep.Stats.NotCompiled,
	}
	pkgs := scores{}
	for _, m := range rep.Killed {
		if inGate(m, changes, all) {
			res.Killed++
			pkgs.of(m.Mutator.File).Killed++
		} else {
			res.Skipped++
		}
	}
	matched := make([]bool, len(records.Equivalents))
	for _, m := range rep.Escaped {
		if !slices.Contains(targets, m.Mutator.File) {
			return MutationResult{}, fmt.Errorf("go-mutesting reported a mutant of %s, which the gate did not mutate", m.Mutator.File)
		}
		if !inGate(m, changes, all) {
			res.Skipped++
			continue
		}
		s, _, err := survivor(m)
		if err != nil {
			return MutationResult{}, err
		}
		res.Escaped++
		if equivalent(m, s, records, matched) {
			res.Equivalent++
			pkgs.of(s.File).Equivalent++
			continue
		}
		pkgs.of(s.File).Survived++
		res.Findings = append(res.Findings, survivorFinding(s))
	}
	res.Packages = pkgs.sorted()
	if all {
		res.Findings = append(res.Findings, staleRecords(records, matched)...)
	}
	return res, nil
}

// equivalent reports whether a record matches the survivor s of mutant m, or
// whether m only changes a result beside a non-nil error. It marks the
// matched record.
func equivalent(m mutant, s Survivor, records Records, matched []bool) bool {
	if i := records.match(s); i >= 0 {
		matched[i] = true
		return true
	}
	return errorContract(m, s.Start)
}

// inGate reports whether the gate tests the mutant: it changes the source,
// and, without all, it changes a changed line.
func inGate(m mutant, changes Changes, all bool) bool {
	start, end, changed := m.span()
	return changed && (all || changes[m.Mutator.File].Intersects(start, end))
}

func survivorFinding(s Survivor) Finding {
	where := "outside a function"
	if s.Function != "" {
		where = "in " + s.Function
	}
	return Finding{
		Location: s.File + ":" + strconv.Itoa(s.Start),
		Rule:     RuleMutant,
		Message:  fmt.Sprintf("no test kills the %s mutant %s: %q becomes %q", s.Mutator, where, s.Line, s.Mutated),
		Fix:      "Add a test that fails with the mutant. If no test can observe the change, record the mutant in " + RecordsFile + " with the reason.",
	}
}

// staleRecords returns a finding for each record that matched no mutant.
func staleRecords(records Records, matched []bool) []Finding {
	var findings []Finding
	for i, e := range records.Equivalents {
		if !matched[i] {
			findings = append(findings, Finding{
				Location: RecordsFile,
				Rule:     RuleRecord,
				Message:  fmt.Sprintf("record %d (%s, %q) matches no surviving mutant", i+1, e.File, e.Line),
				Fix:      "Remove the record, or correct it so that it names the mutant.",
			})
		}
	}
	return findings
}
