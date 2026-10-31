# Go style map

This map connects each rule of the
[Google Go Style Guide](https://google.github.io/styleguide/go/) to the check
that enforces it. It covers the guide at revision `9d7ce97` (2026-10-30) of
`google/styleguide`.

`.golangci.yml` holds the checks, and `make go-lint` runs them. A "Review" entry
means that no tool checks the rule deterministically, so the reviewer checks
it. An entry with a check and "review" means that the check covers only part of
the rule.

The checks are stricter than the guide in two places:

- `nakedret` rejects every naked return. The guide permits naked returns in
  very short functions.
- `godox` rejects `TODO`, `FIXME`, `BUG`, `HACK`, and `XXX` comments. Record the
  work in an issue instead.

Some checks enforce the rules of this repository, not the guide:

- `forbidigo` and `depguard` keep library packages silent: they do not print,
  log, read the environment, read the clock, define flags, or exit (ADR 0047).
  Packages under `cmd/` and `tools/` are the composition root and can do these
  things.
- `gosec`, `bidichk`, `errcheck`, and the `govet` analyzers find defects that
  the guide does not name.

## Style guide

| Rule | Check |
| --- | --- |
| Style principles: clarity, simplicity, least mechanism, concision, maintainability, consistency | Review |
| Formatting | `gofmt` (with simplification) and `goimports` through `golangci-lint fmt --diff` |
| MixedCaps | `revive` `var-naming`, `staticcheck` ST1003 |
| Line length | No check: the guide sets no fixed limit |
| Naming | See the Style Decisions naming rules |
| Local consistency | Review |

## Style decisions

### Naming

| Rule | Check |
| --- | --- |
| Underscores | `revive` `var-naming`, `staticcheck` ST1003 |
| Package names | `revive` `package-naming` (with the extra bad names) and `package-directory-mismatch` |
| Receiver names | `revive` `receiver-naming`, `staticcheck` ST1016; review for length |
| Constant names | `revive` `var-naming` (rejects `ALL_CAPS` and a leading `k`) |
| Initialisms | `revive` `var-naming`, `staticcheck` ST1003 |
| Getters | Review |
| Variable names | Review |
| Single-letter variable names | Review |
| Repetition: package vs. exported symbol name | `revive` `exported` (stutter check) |
| Repetition: variable name vs. type | Review |
| Repetition: external context vs. local names | Review |

### Commentary

| Rule | Check |
| --- | --- |
| Comment line length | Review: the guide sets no fixed limit |
| Doc comments | `revive` `exported`, `godoclint` `start-with-name`, `staticcheck` ST1020, ST1021, and ST1022 |
| Comment sentences | `godot` (capital letter and final period on declaration comments) |
| Examples | `testableexamples`; review for presence |
| Named result parameters | `nakedret`; review for the choice of names |
| Package comments | `revive` `package-comments`, `staticcheck` ST1000, `godoclint` `pkg-doc`, `single-pkg-doc`, and `require-pkg-doc` |

### Imports

| Rule | Check |
| --- | --- |
| Import renaming | `revive` `redundant-import-alias` and `import-alias-naming`; review |
| Import grouping | `goimports` (standard library, then other packages); review for side-effect imports |
| Import "blank" (`import _`) | `revive` `blank-imports`; review |
| Import "dot" (`import .`) | `revive` `dot-imports`, `staticcheck` ST1001 |

### Errors

| Rule | Check |
| --- | --- |
| Returning errors | `revive` `error-return`, `staticcheck` ST1008; review for concrete error types |
| Error strings | `revive` `error-strings`, `staticcheck` ST1005 |
| Handle errors | `errcheck` (including blank assignments) |
| In-band errors | Review |
| Indent error flow | `revive` `indent-error-flow`, `superfluous-else`, and `early-return` |

### Language

| Rule | Check |
| --- | --- |
| Literal formatting: field names | `govet` `composites` (types from other packages) |
| Literal formatting: matching braces | `gofmt`; review |
| Literal formatting: cuddled braces | `gofmt`; review |
| Literal formatting: repeated type names | `gofmt` simplification |
| Literal formatting: zero-value fields | Review |
| Nil slices | Review |
| Indentation confusion | `gofmt`; review |
| Function formatting | Review |
| Conditionals and loops | Review |
| Copying | `govet` `copylocks`; review for other types |
| Don't panic | `revive` `deep-exit`; review |
| Must functions | Review |
| Goroutine lifetimes | `govet` `lostcancel`, `containedctx`, `fatcontext`; review |
| Interfaces | `iface`, `interfacebloat`, `inamedparam`; review |
| Generics | Review |
| Pass values | Review (`gocritic` `hugeParam` is off because it asks for the opposite) |
| Receiver type | `recvcheck`; review |
| `switch` and `break` | `revive` `useless-break` |
| Synchronous functions | Review |
| Type aliases | Review |
| Use %q | `gocritic` `sprintfQuotedString` |
| Use any | `revive` `use-any`, `modernize` |

### Common libraries

| Rule | Check |
| --- | --- |
| Flags | `depguard` (only commands import `flag`); review for flag names |
| Logging | `depguard` (only commands import `log` and `log/slog`); review |
| Contexts | `revive` `context-as-argument`, `containedctx`, `contextcheck` |
| Custom contexts | Review |
| crypto/rand | `depguard` (rejects `math/rand`), `gosec` G404; review |

### Useful test failures

| Rule | Check |
| --- | --- |
| Assertion libraries | `depguard` (rejects testify, gomega, ginkgo, gotest.tools, and is) |
| Identify the function | Review |
| Identify the input | Review |
| Got before want | Review |
| Full structure comparisons | Review |
| Compare stable results | Review |
| Keep going | Review |
| Equality comparison and diffs | `forbidigo` (rejects `reflect.DeepEqual`; use go-cmp) |
| Level of detail | Review |
| Print diffs | Review |
| Test error semantics | `errorlint`; review |

### Test structure

| Rule | Check |
| --- | --- |
| Subtests | Review |
| Subtest names | Review |
| Table-driven tests | `dupl`; review |
| Data-driven test cases | Review |
| Identifying the row | Review |
| Test helpers | `thelper` |
| Test package: tests in the same package | Review |
| Test package: tests in a different package | Review |
| Use package `testing` | `depguard` (rejects other test frameworks) |

### Non-decisions

The guide lists these topics as open choices. No check applies.

## Best practices

### Naming

| Rule | Check |
| --- | --- |
| Function and method names: avoid repetition | `revive` `exported` (stutter check); review |
| Function and method names: naming conventions | Review |
| Test double and helper packages, and their subsections | `revive` `package-naming`; review |
| Shadowing | `govet` `shadow`; review |
| Util packages | `revive` `package-naming` (with the extra bad names) |

### Package size

| Rule | Check |
| --- | --- |
| Package size | Review; the architecture model (chunk 04) records each package |

### Imports

| Rule | Check |
| --- | --- |
| Protocol Buffer messages and stubs | Not used in this repository |
| Import ordering | `goimports` |

### Error handling

| Rule | Check |
| --- | --- |
| Error structure | `errname`, `errorlint`; review |
| Adding information to errors | `errorlint`; review |
| Placement of %w in errors, and sentinel error placement | Review |
| Logging errors, and custom verbosity levels | `depguard` (libraries do not log); review |
| Program initialization | Review |
| Program checks and panics | `revive` `deep-exit`; review |
| When to panic | Review |

### Documentation

| Rule | Check |
| --- | --- |
| Conventions: parameters and configuration, contexts, concurrency, cleanup, and errors | Review |
| Preview | Review |
| Godoc formatting | `godoclint`, `godot`; review |
| Signal boosting | Review |

### Variable declarations

| Rule | Check |
| --- | --- |
| Initialization | `revive` `var-declaration`; review |
| Declaring variables with zero values | `revive` `var-declaration`; review |
| Composite literals | Review |
| Size hints | Review |
| Channel direction | Review |

### Function argument lists

| Rule | Check |
| --- | --- |
| Option structure | Review |
| Variadic options | Review |

### Complex command-line interfaces

| Rule | Check |
| --- | --- |
| Complex command-line interfaces | Review |

### Tests

| Rule | Check |
| --- | --- |
| Leave testing to the `Test` function | Review |
| Designing extensible validation APIs, acceptance testing, and writing an acceptance test | Review |
| Use real transports | Review |
| `t.Error` vs. `t.Fatal` | Review |
| Error handling in test helpers | `thelper`; review |
| Don't call `t.Fatal` from separate goroutines | `govet` `testinggoroutine` |
| Use field names in struct literals | `govet` `composites` (types from other packages); review |
| Keep setup code scoped to specific tests, a custom `TestMain`, and amortized setup | Review |

### String concatenation

| Rule | Check |
| --- | --- |
| Prefer "+" for simple cases | `perfsprint`; review |
| Prefer `fmt.Sprintf` when formatting | Review |
| Prefer `strings.Builder` for constructing a string piecemeal | Review |
| Constant strings | Review |

### Global state

| Rule | Check |
| --- | --- |
| Major forms of package state APIs | `gochecknoglobals`, `gochecknoinits` |
| Litmus tests | Review |
| Providing a default instance | Review |

### Interfaces

| Rule | Check |
| --- | --- |
| Avoid unnecessary interfaces | `iface`; review |
| Interface ownership and visibility | Review |
| Designing effective interfaces | `interfacebloat`, `inamedparam`; review |
