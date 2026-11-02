# Go port audit: issue 617

The port is incomplete. Passing checks on PR 618 do not establish delivery
of the milestone or acceptance of every earlier PR.

The audit covers all 32 chunks and 119 acceptance criteria. It covers 17
related PRs, including the superseded closed PR and the stabilization PR.
The earlier progress update counted 18 PRs; the checked inventory has 17.

The [acceptance register](go-port-audit.json) records every criterion, its
assessment, evidence, and the reviewed PR heads. The source baseline is
`570ff17aae37b90100190bf7a5ad3e124bcfc971`. Changes after that baseline need
fresh verification. Design 0010 records the fixes from this audit.

## Findings

| ID | Finding | Source | Disposition |
| --- | --- | --- | --- |
| A01 | A short JSON exponent reaches the schema validator and panics. | PR 611; `document/json.go` and `schema/schema.go` | Bound number expansion at ingestion. |
| A02 | Empty or inconsistent mutation reports pass the gate. | PR 591; `testgate/report.go` | Require counts and matching mutant lists. |
| A03 | Failed platform discovery skips lint and returns success. | PR 606; `Makefile` | Capture discovery before the loop. |
| A04 | A panic after exchange leaves the replacement installed. | PR 606; `packfs/transactions.go` | Roll back before panic propagation; retain recovery paths. |
| A05 | A maximum integer byte budget returns empty content with success. | PR 606; `packfs/member.go` | Saturate the lookahead limit. |
| A06 | An unpaired Unicode escape reports a duplicate key. | PR 611; `document/json.go` | Use the standard duplicate-name error. |
| A07 | The executable check permits group write access. | PR 616; command `ghPath` | Reject group write access; state the trusted-PATH requirement. |
| A08 | Fuzzing never constructs hardlinks or tests bounded reads. | PR 606; `packfs/fuzz_test.go` | Add both and correct the seed selectors. |
| A09 | Vulnerability scanning covers only the host build. | PR 592; `Makefile` | Scan all four model platforms. |
| A10 | Help omits option descriptions and defaults. | PR 616; command flag parser | Print the standard flag help. |
| A11 | The wizard alias has no blocking-status case. | PR 596; conformance corpus | Add an existing-target case. |
| A12 | The stack predates current dev and RAES 10.4 changes. | Branch history; PR 607 | Merged current dev into the stabilization leaf; revalidate before integration. |
| A13 | The RAES map omits retained content-test operations. | PR 615; content tests | Mapped 97 imports and added the missing declarations; adapter delivery remains open. |
| A14 | The shared architecture checker is not in use. | PR 590; `go.mod` | Track release and compatibility prerequisites before adoption. |
| A15 | Weekly Go checks and Go dependency updates are not operational. | PRs 589, 591, 592 | Configuration must reach the default branch through an approved PR. |
| A16 | External command execution has no duration or output bound. | PR 616; `ghRunner` | Add bounded execution and failure tests. |
| A17 | Discovery silently stops at 2,000 issues or 500 labels. | PR 616; GitHub client | Refuse capped discovery and missing read responses before any write. |

Earlier fixes in PR 618 cover usage escaping, foreign absolute diagnostic
paths, process-stream access, model-change records, stacked CodeQL, and the
title guard. They also add the missing tool-failure corpus cases.

## Delivery assessment

PRs 584, 586, 587, 589, and 590 merged into `go-cutover`. PR 585 closed
without merging; PR 586 superseded it. No delivery credit goes to PR 585.

PRs 592, 593, and 596 merged into intermediate branches. PR 591 carries
their combined work. PR 616 also merged into an intermediate branch.
PRs 591, 605, 606, 611, 614, 615, and 618 remain open.

Only `raes-pack-issue-skeleton` has a Go command. Chunks 13–23 and 25–31
still lack their Go delivery. Chunk 01 has declarations but no adapter.
Foundations do not establish command parity for these absent implementations.

Chunks 10 and 11 also name Python consumers outside their new packages.
Those consumers remain unchanged until their own port chunks. These scope
items must stay visible even when the foundation PR passes.

The refreshed RAES inventory includes custom backend-manifest planning,
realization concern descriptors, compiled document access, and observation
support. It also covers compilation of instantiated scenarios and time-model
contracts. The declarations now represent those calls. RAES continues to own
the semantics; adapter implementations and contract tests remain blocked on
the upstream module.

## Reuse and shared concerns

| Concern | Assessment |
| --- | --- |
| JSON Schema | Uses `santhosh-tekuri/jsonschema/v6`; full keyword support and network loading disabled. Keep it. |
| YAML | Uses maintained `yaml.v3`; local checks enforce pack limits and Python compatibility. Keep the parser. |
| Git diffs | Uses `bluekeyes/go-gitdiff`. Keep it. |
| Conformance | Uses `go-internal/testscript` and `txtar`. Keep them. |
| Unicode | Uses `x/text` normalization and case folding. Keep them. |
| Templates | Uses standard `embed` and `text/template`. Keep them. |
| Filesystem | Uses standard file operations plus `x/sys/unix` for required descriptor and atomic operations. |
| JSON output | Uses standard `jsontext`; local number formatting preserves Python output bytes. |
| Terminal output | One shared escaping package serves the command and diagnostics. |
| Architecture | Local checker duplicates a shared concern. Replace it after shared release and compatibility verification. |
| Mutation and regression | Local wrappers use an existing mutator and Git diff library. Review migration to shared tools with their release. |

The shared checker has development branches, but no tag or release at the
audit snapshot. Its issue 3 blocks release on engineering checks and the
first release of `go-rae-gremlins`. Calling it absent would be inaccurate;
calling its local checkout a released dependency would also be inaccurate.

## Errors, logging, and security

Silent libraries are the intended architecture. They return structured errors;
command boundaries own terminal output and exit status. Adding library logging
would violate that design and could expose authored content.

Product diagnostics, developer findings, and RAES transport diagnostics have
different purposes. Their separate types do not establish duplicate product
policy. The adapter must convert RAES diagnostics without copying message text.

The staging writer assumes a fresh private tree. Reusing an untrusted tree
can truncate a hardlink or block on a FIFO. State and preserve that
precondition in every future caller. It is not a safe general file writer.

The filesystem design excludes concurrent mutation of the source tree.
The audit does not claim protection beyond that declared threat model.
The command also depends on a trusted PATH, including executable ownership.

Sonar is intentionally separate from `verify` under ADR 0029. It checks
eligible PRs and consumes Go coverage. Its omission from the universal
required-check list is not a new port defect.

## Verification and remaining gates

Targeted probes reproduced A01–A07 before the fixes. Negative tests now
cover those inputs. Filesystem tests exercise real temporary trees; command
tests use fake executables and do not contact GitHub.

The old head passed 23 hosted checks. That result does not verify later
changes. Record new test, mutation, regression, fuzz, and hosted results in
issue 617 before calling the stabilization PR ready.

The merge policy keeps zero required approvals, as the maintainer selected.
It still requires a PR and passing checks. Human approval remains necessary
before merging a PR. No audit finding authorizes a merge or a Go release.
