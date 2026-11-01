# Go test standard

Every Go package in this repository follows this standard (ADR 0047). The
standard applies to the Go code of the port and to the Go code after the
cutover.

The gates are:

- `make go-check`: builds, vets, and tests every package with the race
  detector and in shuffled order, and writes the coverage profile.
- `make go-fuzz`: runs every fuzz target for a fixed time.
- `make go-lint`: rejects assertion libraries, `reflect.DeepEqual`, and test
  helpers without `t.Helper()` (see the style map).
- `make go-mutation`: mutation testing on the Go lines that the change adds or
  changes. Each mutant on those lines must fail a test.
- `make go-regression`: proves that each new regression test fails on the
  code before the fix.

[Design 0002](designs/0002-test-gates.md) records the design of the two
gates.

## Tools

- Use the standard `testing` package.
- Compare values with `github.com/google/go-cmp/cmp`. Print the difference as
  `cmp.Diff(want, got)` with the label `(-want +got)`.
- Do not use an assertion library or another test framework.

## Structure

- Use a table test when cases differ only in data. Give each row a name, and
  run each row as a subtest with `t.Run`.
- Write failure messages with the function, the input, and `got` before
  `want`, for example `Parse(%q) = %v, want %v`.
- Call `t.Error` when the test can continue. Call `t.Fatal` only when the
  rest of the test cannot run.
- Test helpers call `t.Helper()` first. A helper does not call `t.Fatal` from a
  goroutine that it starts.
- Test behavior through the exported API of a package. Test an unexported
  function only when the exported API cannot reach the case.

## Golden files

- Keep the expected command output and the expected generated documents in
  `testdata/`, beside the test that reads them.
- Compare exact bytes when the contract requires exact bytes. Otherwise compare
  the decoded content.
- Rewrite golden files only through the `-update` flag of the package test.
  Review every change to a golden file as a change to the contract.

## Untrusted input

- Each parser of untrusted input has a native fuzz target, `FuzzXxx`, with a
  seed corpus. Untrusted input includes pack files, archives, replay
  documents, source manifests, and MCP requests.
- The fuzz oracle is the same for every target:
  - invalid input gives a bounded result with a stable code;
  - a panic, an unbounded result, or a different result for the same input
    fails the target;
  - the target does not recover a panic, so a defect stays visible.
- `make go-fuzz` runs each target for `FUZZTIME`, which is 30 seconds by
  default. CI runs it on each pull request, and a weekly schedule runs each
  target for 10 minutes.
- When the fuzzer finds a failing input, commit that input to the seed corpus
  with the fix.

## Determinism and isolation

- Tests do not use the network.
- Tests do not read the environment or the clock. Pass these values as
  parameters, as library code does.
- Use `t.TempDir` for files. A test pack is a synthetic pack in a temporary
  directory, or a hosted pack or kit without changes.
- Every test passes with the race detector and in any order.

## Mutation testing

`make go-mutation` runs go-mutesting on the Go files that HEAD changes since
`BASE`, and keeps the mutants on the changed lines. The default `BASE` is
`origin/go-cutover`. The gate reads only committed code, so commit the work
before you run it.

- A mutant survives when each test passes with it. A surviving mutant on a
  changed line is a finding.
- Kill a survivor with a test that checks the behavior that the mutant
  changes. Pin a contract value, such as a limit or an exit status, with a
  literal in the test. A test that uses the same constant as the code does
  not kill a mutant of that constant.
- Prefer simpler code to a test of an unreachable branch. An error check that
  no input can reach gives a mutant that no test can kill.
- A mutant that does not compile does not count as killed. The gate reports
  the number of such mutants.
- `make go-mutation-all` mutates each Go file. A weekly workflow runs it.
- Each run reports the score of each package: the killed mutants as a
  percentage of the killed and the surviving mutants. The threshold is 100%.

## Equivalent mutants

An equivalent mutant changes no behavior that a test can observe.

The gate knows one kind by a rule. A numbers mutant that changes only a result
beside a non-nil error is equivalent. Go leaves the other results unspecified
when a function returns an error. The rule applies to a `return` statement in
a function whose last result has the type `error`, when the last result is not
`nil`. Do not write tests for those results.

Record each other equivalent mutant in `mutation.yaml`:

```yaml
version: 1
equivalents:
  - file: internal/example/example.go
    function: Parse
    mutator: expression/comparison
    line: if i < 0 {
    reason: >-
      A leading separator is invalid on both paths, so the result is the
      same when i is 0.
```

- `function` is the name of the function, `Type.Method` for a method, or
  empty outside a function.
- `line` is the text of the first changed line, without leading and trailing
  space. The finding of the gate shows it.
- `reason` tells why no test can observe the change. "The test is hard to
  write" is not a reason.
- The weekly run reports each record that matches no mutant. Remove such a
  record.

## Regression tests

A regression test proves the fix of a defect. Put the text `Regression test
for #N` in the doc comment of the test, where `N` is the issue of the defect:

```go
// TestParseEmptyName checks that an empty name is an error.
// Regression test for #123.
func TestParseEmptyName(t *testing.T) {
```

`make go-regression` runs each regression test that the change adds or
changes on the merge base with `BASE`. It copies in the changed test files and
the changed `testdata` files of the package. The test must compile there and
fail there. Write it against the API that the merge base has.

## Coverage

`make go-check` writes `coverage-go.out`. CI sends it to SonarCloud with the
Python coverage report.

## Contracts

The conformance corpus in `conformance/` tests the external contracts of the
commands and library operations
([design 0003](designs/0003-conformance-corpus.md)). Package tests cover the
behavior inside a package.

- `make conformance` runs the corpus against the Python implementation.
- A port chunk adds the cases for its surface before its Go code merges.
