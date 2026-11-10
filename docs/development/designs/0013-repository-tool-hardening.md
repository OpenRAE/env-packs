---
design: 13
issue: 674
title: Repository tool hardening
changes:
  dependencies:
    add:
      - from: report
        to: terminal
---

# Design 0013: Repository tool hardening

Issue: #674.

This design closes gaps in the repository tools that a review of the Go port
found. It adds one dependency and no component, package, or module.

## Architecture inventory

The architecture checks read Go syntax only. The go command also compiles or
links native sources and objects, such as assembly and `.syso` files. Such a
file can hold behavior that the rules of the model do not see.

The unread-path inventory now lists each native source or object of the
module. The extensions are the ones that `go/build` classifies. The existing
`unread-path` finding then stops the gate. This keeps the fail-closed rule of
design 0001: the checks report each path that they cannot read.

## Escaped findings

A finding can hold a file name or a value from a change, such as a record of
`mutation.yaml`. Such a value can hold terminal control characters.

`report.Finding.String` now escapes each field with `terminal.Escape`
(design 0006). The escape is at the presentation boundary, so it covers each
tool that writes findings. A finding stays two lines: a newline in a field
becomes `\x0a`. This needs the dependency `report` -> `terminal`.

## Mutation records

The mutation gate read `mutation.yaml` only when a Go line was a target. A
change to the records alone skipped the check. The gate now parses and checks
the records of `HEAD` when it has no target.

## Policy input parsers

`tools/policyinput` parses YAML, JSON, TOML, and shell syntax from the
repository. A contributor controls that input. Each parser now has a native
fuzz target, as the [Go test standard](../go-test-standard.md) requires.

## Issue skeleton

The contract issue named `environments/` as the pack root for each plan. It
now names the pack root of the plan, so a first-party issue names `packs/`.
The Python implementation has the same correction, so both implementations
give the same body.
