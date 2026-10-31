---
design: 1
issue: 555
title: Architecture model, checker, and design step
changes:
  containers:
    add:
      - commands
      - library
      - repository-tools
  components:
    add:
      - id: root
        container: library
      - id: architecture
        container: repository-tools
  packages:
    add:
      - path: github.com/OpenRAE/env-packs
        component: root
      - path: github.com/OpenRAE/env-packs/internal/architecture
        component: architecture
      - path: github.com/OpenRAE/env-packs/tools/archcheck
        component: architecture
  modules:
    add:
      - component: architecture
        module: golang.org/x/tools
      - component: architecture
        module: go.yaml.in/yaml/v3
  test_modules:
    add:
      - github.com/google/go-cmp
  rules:
    add:
      - silent-libraries
      - flags-in-commands
      - networkless-code
      - no-process-execution
      - files-through-packfs
---

# Design 0001: Architecture model, checker, and design step

Issue: #555 (chunk 04 of the Go port).

## Problem

The Python implementation has no architecture check. The review found 44
references from 10 modules to 24 private names of other modules, and an import
that changes `sys.path` for the whole process. The ADRs state structural rules,
such as "every pack read uses the descriptor-anchored boundary", but no tool
checks them. The Go code must not repeat these failure modes.

## Design

### The model

`architecture/model.yaml` is the one architecture model of the repository. It
names:

- the system, its people, and the external systems (the C4 context);
- the containers: the commands, the Go library, and the repository tools;
- the components, the container of each component, and the Go packages that
  each component owns;
- the components that each component may depend on;
- the external modules that each component may import, and the modules that
  any test file may import;
- the rules: forbidden imports and forbidden symbols, with the scope of each
  rule and a fix-it message.

Each package names its owner explicitly. A pattern cannot own a package, so a
new package needs a model change.

### The checker

`tools/archcheck` loads the model, the design records, and every package of
the module with `golang.org/x/tools/go/packages`. It has two modes:

- `archcheck design` checks the model and the design records. It does not read
  the code, so it passes before the code exists.
- `archcheck check` adds the code checks and the check of the generated C4
  view.

The code checks report these findings:

- a package that no component owns;
- a package that the model names but the code does not have;
- an import of another component that the model does not permit;
- an import of an external module that the component may not use;
- an import or a symbol that a rule forbids.

Each finding gives the file and line, the rule, and a fix-it message. The
checker reports every finding and exits with status 1 when there is one. It has
no baseline: the Go code starts with no findings.

### Design records

A design record is a Markdown file in `docs/development/designs/`, named
`NNNN-slug.md`. Its front matter lists the changes that the design makes to the
structure of the model: containers, components, packages, dependencies,
modules, test modules, and rule identifiers. Each list has `add` and `remove`
entries.

The checker applies the records in number order to an empty model. The result
must be equal to the structure of `architecture/model.yaml`. So the model
cannot change without a design record, and a design record cannot declare a
change that the model does not have.

The descriptions and the rule bodies are only in the model, so the records do
not copy them.

### The C4 view

The checker renders the model as a Structurizr DSL workspace. `archcheck
check` fails when `architecture/workspace.dsl` differs from the rendered view.
`make go-arch-dsl` writes the file again.

### Rules moved from golangci-lint

Chunk 03 put the silent-library rules in `.golangci.yml`. They are rules of the
architecture, so this design moves them to the model. `.golangci.yml` keeps the
rules that apply to all code: no assertion libraries, no `reflect.DeepEqual`,
no `math/rand`, no `io/ioutil`, no `github.com/pkg/errors`, and no
`golang.org/x/exp` copies of standard packages.

## Packages

| Package | Component | Purpose |
| --- | --- | --- |
| `github.com/OpenRAE/env-packs` | `root` | The root package of the module. |
| `github.com/OpenRAE/env-packs/internal/architecture` | `architecture` | The model, the design records, the code checks, and the C4 view. |
| `github.com/OpenRAE/env-packs/tools/archcheck` | `architecture` | The command that runs the checks. |

## New modules

| Module | Used by | Reason |
| --- | --- | --- |
| `golang.org/x/tools` | `architecture` | `go/packages` loads the packages, imports, and type information of the module. The Go team maintains it. |
| `go.yaml.in/yaml/v3` | `architecture` | Decodes the model and the front matter of the design records. It is the maintained, stable successor of `gopkg.in/yaml.v3`. |
| `github.com/google/go-cmp` | test files | The Go test standard uses it for comparisons. |

## Alternatives

- `go-arch-lint` checks component dependencies, but it has no package
  ownership check, no design records, and fixed messages.
- Generated `depguard` and `forbidigo` settings cannot check package ownership,
  and they cannot scope a forbidden call to a component without many exclusion
  rules.
