# ADR 0047 — Port the tooling to Go with one cutover

- Status: Accepted
- Date: 2026-10-31
- Supersedes, from the cutover: [ADR 0003](0003-build-and-release-model.md),
  [ADR 0027](0027-publish-only-the-active-pypi-distribution.md), the Python
  package decision of [ADR 0002](0002-distribute-as-installable-package.md),
  and the PyPI and import identities of
  [ADR 0021](0021-adopt-raes-environment-pack-identity.md)
- Amends, from the cutover: [ADR 0004](0004-sbom-and-supply-chain.md),
  [ADR 0008](0008-adopt-release-please.md),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md),
  [ADR 0015](0015-attest-python-distribution-build-provenance.md),
  [ADR 0041](0041-distribute-kits-as-package-resources.md),
  [ADR 0043](0043-require-a-minimum-raes-version.md), and
  [ADR 0045](0045-version-packs-with-the-package.md)
- Coordination: OpenRAE/env-packs issue 551 and the "Go port and hard cutover"
  milestone

## Context

A review of the Python implementation found structural defects at its
foundation. The code does not keep several rules that the ADRs state:

- Pack files are read by path outside the descriptor-anchored boundary.
- Two YAML loaders bypass the strict, bounded loader.
- A hand-written schema validator does not enforce every keyword of the
  packaged schemas.
- Six shapes report problems where the ADRs name one diagnostic envelope.
- Security policy code has several copies.
- Modules reach into the private names of other modules, and one import changes
  `sys.path` for the whole process.

RAES is moving to a Go implementation. That work keeps the RAES SDL and its
contracts stable. This repository makes the same move. It enforces its external
contracts and does not keep the Python structure, so that the maintainer can
set the priorities of the work.

Because of the problems that the review found, the maintainer chose one hard
cutover at the end of the work instead of a piecemeal change.

## Decision

### The contracts stay; the structure does not

These contracts stay stable through the port and after the cutover:

- the pack layout contract and its version (`pack-layout.md`, version 8);
- the packaged schemas, with their `$id` and `schema_version` values;
- the `raes-environment-pack:/` locator scheme;
- the command names, flags, exit codes, output streams, and JSON envelopes;
- the generated documents and their versions;
- the stable diagnostic codes and their documentation targets;
- the MCP tool names, input schemas, and envelopes;
- the library operations and their semantics;
- the pack-local execution contract;
- the first-party kit and pack collections.

The Python module structure, private names, test layout, and Python packaging
are not contracts. The Go code does not copy them.

Each command keeps its current exit codes. The commands that use the codes 0,
1, 2, and 3 keep those meanings. `raes-pack-validate` and `raes-pack-release`
keep 0 and 1.

### One corpus holds the contracts

A conformance corpus records the contracts as executable cases. The same cases
run against the Python commands and against the Go commands. A case for a
contract passes against Python before the Go code for that contract merges.
Before the cutover, every case passes against Go.

When the Python behavior differs from the written contract, the case follows
the written contract. The case marks the difference as a Python deviation. The
Go code does not copy the deviation.

### RAES

The Go code reaches RAES only through the RAES Go module. One interface package
declares the RAES operations that this repository uses. Only the adapter for
that interface imports the RAES Go module. The Go code does not call RAES
Python.

When the RAES Go module does not deliver an operation, the work that needs it
waits. This repository does not replace the operation with local code
(ADR 0009).

### Standards for the Go code

The Go code passes these gates before it merges:

- Strict lint, with no baseline. A suppression names one linter and states why
  the finding is false. A security finding is suppressed only when it is a
  verified false positive.
- The Google Go Style Guide rules that a tool can check deterministically. A
  map in the developer documents names the check for each rule, or marks the
  rule as a review item.
- Architecture as code. A committed model defines the components and their
  permitted dependencies. CI fails when the code and the model disagree.
- The test standard: the standard `testing` package with `go-cmp`, the race
  detector, shuffled test order, golden files, and a fuzz target for each parser
  of untrusted input.
- Mutation testing, with a threshold that the repository records.
- Security gates: `govulncheck`, CodeQL, Dependabot, and module checksum
  verification.

These standards stay as they are today:

- Documentation: the style guide, the ADR process, the split between public and
  developer documents (ADR 0030), the warning-strict Sphinx build on Read the
  Docs, the publication-boundary check, and ASD-STE100.
- Release: release-please, Conventional Commit titles, signed tags (ADR 0017),
  build provenance, the SBOM, a human merge for every pull request (ADR 0020),
  and merge commits for promotions (ADR 0019).
- Supply chain: actions pinned by full commit SHA, least-privilege tokens, and
  OpenSSF Scorecard (ADR 0018).

### During the port

- The Python implementation stays the shipped product until the cutover.
- Python changes are limited to fixes, security updates, and RAES dependency
  updates.
- A change to a contract changes the corpus in the same pull request. Both
  implementations follow it.
- A pull request that changes only Go code, CI, or documents uses a Conventional
  Commit type that does not release: `build`, `ci`, `docs`, `refactor`, `test`,
  or `chore`.

### Commands after the cutover

The Go commands keep the names, flags, exit codes, and output streams of the
Python commands.

One new command, `raes-pack-content`, gives consumers that do not use Go the
content-identity operations: manifest validation, digest output, digest
verification, artifact resolution, and manifest derivation. Its output is a
versioned JSON envelope. Pack-local code and OpenRAE/lilrae use these
operations through the Python library today.

`raes-pack-validate` starts pack-local validators and tests with the Python
interpreter that the caller names with `--python`. Without that flag, it uses
the first `python3` on `PATH`. The caller supplies the Python packages that
pack-local code imports. This replaces the "current Python interpreter" rule of
ADR 0013. The discovery roots and the runner controls of ADR 0013 do not change.

### Distribution after the cutover

GitHub Releases and GitHub Packages carry the Go distribution. Each release has
the command binaries for Linux and macOS on amd64 and arm64, build provenance
attestations, and an SBOM. The Go module `github.com/OpenRAE/env-packs`
releases through tags.

The commands and the Go module embed the first-party kit and pack collections.
The pack filesystem package reads an embedded collection through the same
inventory and member operations as a directory. Each release also attaches an
archive of each first-party pack, made with the existing archive export.

The bundled kit source keeps the source id `openrae-env-packs`. Its revision
label becomes `github.com/OpenRAE/env-packs@v<version>`.

PyPI gets one final release of `raes-env-packs`. That release changes only the
package description, which points to the Go distribution and the migration
page. After it, the PyPI project is frozen. Earlier PyPI releases stay
available.

The version stays in one file that release-please writes. The pack version
tools read that file (ADR 0045). The RAES dependency is the RAES Go module, with
a minimum version in `go.mod` (ADR 0043).

### Differences that the cutover makes

- Archive bytes change, because a different compressor writes them. Archive
  transport digests therefore change. RAES set digests do not change.
- The schema validator enforces every keyword of the packaged schemas. All
  hosted kits and packs pass the full schemas.
- The corpus lists every other Python deviation.

### The cutover

One pull request makes the Go implementation the product. It merges after every
other chunk of the milestone is closed, every corpus case passes against Go, no
Python deviation mark remains, and every gate is green.

The cutover removes the Python implementation, its tests, its packaging, its
locks, its requirement files, and the Python repository tools. It keeps the pack
and kit content, including pack-local Python code, and the documentation
toolchain: `requirements/docs.in`, `requirements/docs.txt`, and
`docs/public/conf.py`. Its title marks a breaking change, so the next release
is a major release.

## Consequences

- Pack-local code and OpenRAE/lilrae move from the Python library to the Go
  commands or the Go module before the cutover.
- Python consumers either pin the last Python release or move to the Go
  distribution. The migration page maps each Python API and command to its
  replacement.
- Two implementations exist until the cutover. The corpus keeps them in step.
- The delivery of the RAES Go module sets the schedule for the work that needs
  RAES operations.

## Non-goals

This decision adds no functionality other than `raes-pack-content`. It adds no
OCI transport and no signature verifier. It does not change the RAES SDL or any
RAES contract. It does not change pack or kit content, except the pack-local
code that imports the Python library.
