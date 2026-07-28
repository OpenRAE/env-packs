# ADR 0029 — Parallel PR feedback with a complete merge gate

- Status: Accepted
- Date: 2026-07-28
- Extends: [ADR 0004](0004-sbom-and-supply-chain.md),
  [ADR 0018](0018-openssf-scorecard-posture.md), and
  [ADR 0020](0020-no-auto-merge.md)

## Context

The required `verify` job serializes dependency audit, unit tests, the
environment-pack-content gate, and the pack-release gate. SonarCloud then waits
for all of `verify` before independently installing the package and rerunning the
unit suite for coverage. This delays actionable failures and puts unrelated work
on the required-check critical path.

The optimization boundary is CI orchestration, not the RAES environment-pack
contract or its tooling. Faster feedback must not create a second definition of
the test suite, validation gates, coverage scope, dependency policy, or required
merge gate.

## Decision

Keep `verify` as the stable protected-branch status context and make it a
fail-closed aggregate of every mandatory verification job. The aggregate runs
even when a dependency fails and succeeds only when every mandatory result is
successful; a failed, cancelled, or unexpectedly skipped mandatory job is not a
pass. Change classification and secret availability never remove work from this
aggregate.

Run independent mandatory work concurrently. Each job invokes the repository's
existing command rather than reimplementing it:

- `python -m unittest discover -s tests`;
- `raes-pack-validate --repo .`;
- `raes-pack-release check --all`; and
- `python3 -m compileall src tests`.

The dependency vulnerability audit remains an independent mandatory result and
retains its bounded retry for the network-backed advisory service. Its audited
environment must not be narrowed accidentally when it is split out: the current
runtime, build, and audit-tool locks remain present when `pip-audit` runs unless
a later decision replaces that population with equally complete explicit
requirement audits. Every job continues to install from the applicable
hash-locked `requirements/*.txt` files with `--require-hashes`, and editable
installs continue to use `--no-deps --no-build-isolation`. Repeated explicit
install commands are preferable to hiding this security-sensitive shape behind
a helper that the existing repo-wide workflow tests cannot inspect.

Generate the complete coverage input as part of the unit-test authority, once.
SonarCloud depends only on that successful coverage producer, consumes its
same-run, exact-name artifact, and continues to use `.coveragerc` and
`sonar-project.properties`. It does not wait for audit or pack gates. The
SonarCloud quality gate remains complete, but its secret eligibility remains
unchanged: `SONAR_TOKEN` is passed through the scanner step's environment, never
command-line arguments or artifacts, and scans remain skipped for fork and
Dependabot pull requests. SonarCloud is not folded into `verify`, because a
secret-backed check unavailable to those pull requests cannot be a universal
required context.

CodeQL and fuzzing retain their separate workflows and security contracts.
CodeQL's existing `build-mode: none` is already the earliest valid Python SAST
path and gains no dependency on package verification.

Do not shard the current unit suite. It contains 474 tests and completes in
about 14 seconds on the development host; the workflow overhead and added
coverage fan-in would dominate without GitHub-hosted timing evidence to the
contrary. If hosted-run p95 later justifies sharding, one canonical deterministic
test inventory must assign every test ID to exactly one `(shard_index,
shard_count)` pair, and the full run must prove that the shard manifests are
disjoint and their union equals the inventory before coverage is combined.
Per-shard file lists or duplicated test-category taxonomies are prohibited.

The early-feedback lane is unconditional syntax/static checking, not a
change-based substitute for verification. A future change classifier may add
advisory checks from a closed, repository-owned path policy, but a
misclassification must only cause extra work or less early feedback; it must
never skip or satisfy a mandatory gate. Pull-request data stays untrusted:
workflows use `pull_request`, not `pull_request_target`, and do not interpolate
event-controlled values into shell commands.

Cache only downloaded dependency artifacts, keyed by runner OS, Python version,
and the exact lock files consumed by the job. Restores still pass through pip's
hash verification. Do not cache installed environments, editable source,
advisory results, coverage outputs, scanner credentials, or other mutable
verification state.

Measure end-to-end GitHub Actions time, including queueing. For a fixed,
documented cohort of non-cancelled pull-request first attempts:

- time to first failure is event creation to the first failed mandatory or
  advisory feedback job, calculated only for runs that fail; and
- time to final required-check completion is event creation to terminal
  completion of `verify`.

Record sample window, sample count, workflow revision, median, and nearest-rank
p95 for both before and after cohorts. Do not count cancelled superseded runs as
fast completions or combine push, schedule, rerun, and pull-request populations.

Workflow-specific contract tests own the required job topology, aggregate
membership, Sonar coverage dependency, and secret eligibility. Existing
repo-wide tests remain the authorities for action SHA pinning, least-privilege
permissions, no auto-merge, and hash-locked pip command shapes; those rules are
not duplicated in a new validator.

## Consequences

- Required coverage remains stable behind the existing `verify` status while
  independent failures surface earlier.
- Coverage is produced once and handed to SonarCloud without making artifacts or
  caches a cross-run trust boundary.
- Adding a mandatory check means adding one independent result to the `verify`
  aggregate and its workflow-contract test. `shard_count` is the future scaling
  seam if hosted-run evidence warrants unit-test sharding.
- CI documentation must distinguish early feedback, the full `verify` gate,
  optional secret-backed analysis, and exact local reproduction commands. The
  Makefile remains free of a fourth copy of the verification command list.

## Non-goals

This decision does not change branch-protection coverage, make SonarCloud
universally required, suppress or narrow any security scan, add auto-merge,
change release automation, introduce a CI service or metrics database, or alter
package code, schemas, validation results, exception behavior, logging, pack
layout, or RAES semantics. It does not promise sharding or path-based skipping
without later timing evidence and a closed correctness contract.
