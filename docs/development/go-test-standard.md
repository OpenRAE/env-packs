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

## Coverage

`make go-check` writes `coverage-go.out`. CI sends it to SonarCloud with the
Python coverage report.

## Contracts

The conformance corpus (chunk 09) tests the external contracts of the commands
and library operations. Package tests cover the behavior inside a package.
