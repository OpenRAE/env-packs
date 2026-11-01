# Design records

A design record states the change that a piece of work makes to the
architecture model, `architecture/model.yaml`, before the code exists (ADR 0047).
`tools/archcheck` checks each record against the model.

## The design step

Do these steps before you write the code of a change:

1. Write a design record in this directory. Use the next number, for example
   `0007-pack-filesystem.md`.
2. List the changes to the model in the front matter of the record.
3. Change `architecture/model.yaml` to match.
4. Run `make go-arch-design`. It checks the model and the design records, and
   it does not read the code.

Then write the code, and run `make go-arch`. It checks the code against the
model. It loads the code once for each platform in the `platforms` list of the
model. So it also checks a file that build constraints exclude on one platform.

## Format

A record is a Markdown file with YAML front matter. The body explains the
problem, the design, and the reasons. The front matter lists the changes to the
structure of the model:

```yaml
---
design: 7
issue: 561
title: Pack filesystem boundary
changes:
  containers:
    add: [example-container]
  components:
    add:
      - id: packfs
        container: library
  packages:
    add:
      - path: github.com/OpenRAE/env-packs/internal/packfs
        component: packfs
  dependencies:
    add:
      - from: pack
        to: packfs
  modules:
    add:
      - component: packfs
        module: golang.org/x/sys
  test_modules:
    add: [example.com/test/module]
  rules:
    add: [example-rule]
---
```

Each list can have `add` and `remove` entries. Leave out a list that the design
does not change. The descriptions and the rule bodies are only in the model, so
a record does not copy them.

`design` is the number in the file name, and the numbers start at 1 with no
gap. `issue` is the GitHub issue of the work.

## The check

`archcheck design` applies the records in number order to an empty model. The
result must be equal to the structure of `architecture/model.yaml`. A record
cannot add an element that exists, and it cannot remove an element that does
not exist.
