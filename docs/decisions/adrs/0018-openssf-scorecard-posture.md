# 0018. OpenSSF Scorecard posture

Status: Accepted

Supersedes: none. Amends the token-permission and dependency-pinning practice
established by [ADR 0004](0004-sbom-and-supply-chain.md), and records repository
settings that [ADR 0016](0016-automate-dependency-updates.md) depends on.

## Context

[ADR 0004](0004-sbom-and-supply-chain.md) committed this repository to a
supply-chain posture: SHA-pinned actions, an SBOM, and build provenance. Issue
#58 added the OpenSSF Scorecard workflow that measures that posture publicly, and
its first default-branch run scored **5.6**, emitting 19 SARIF findings across
nine checks.

Issue #142 set the target: zero findings outside `Maintained` and `Contributors`.
Working through them showed that Scorecard's checks fall into three distinct
categories, and that treating them uniformly is the mistake. Some are properties
of the code, fixable here. Some are properties of the *repository*, invisible to
git. Some are properties of *history*, which no change can retroactively alter.

This ADR records what was decided for each, so a future contributor does not
reopen a settled question or -- worse -- reach for a suppression.

## Decision

### 1. Workflow tokens are read-only at the top level

Every workflow declares a read-only top-level `permissions` block. Writes are
declared on the individual job that performs them, never at the workflow level.

This is not a stylistic preference. Scorecard's scorer applies its penalty
(`reduceBy()`) only in the top-level branch; a job-level write costs nothing
*provided* the file's top level is read-only, and is penalized only when the top
level is write-all or undeclared. So least privilege here means "read-only at the
top, scoped writes on the job" -- not "never write". `release-please.yml` still
holds `contents: write` on the jobs that push a signed tag and cut a Release,
which is correct and unpenalized.

A job-level `permissions` block **replaces** the top-level one rather than
merging with it, so a job that declares any scope must restate the reads it needs.

`tests/test_workflow_permissions.py` asserts this over every file in
`.github/workflows/`, once, so a new workflow inherits the contract instead of
needing its own bespoke test.

### 2. CI installs are hash-locked, and the locks are not the package's metadata

Every `pip install` in every workflow uses a shape Scorecard recognizes as
pinned: `--require-hashes -r <lock>`, `--no-deps -e <local path>`, or a bare
`*.whl`. A version pin such as `pip-audit==2.10.1` is **not** sufficient -- it
still trusts whatever artifact the index serves for that version.

The locks live in `requirements/`, are generated with
`uv pip compile --generate-hashes`, and are maintained by Dependabot. `uv` is a
maintainer-side tool only; CI consumes the committed files.

The distinction that matters: **these are CI toolchain pins, not a restatement of
what the distributed package requires.** `pyproject.toml` keeps `PyYAML>=6` as a
compatibility floor so downstream consumers can resolve. Collapsing that into an
exact pin to satisfy a scanner would make this library hostile to its own users.
`requirements/runtime.txt` is the resolved closure *of* those declared
dependencies; `tests/test_dependency_pinning.py` asserts the lock **satisfies**
pyproject's constraints rather than equalling them, and fails if the published
metadata is ever collapsed to all-exact pins.

Two related consequences:

- **Every** build disables PEP 517 isolation, because an isolated build resolves
  pyproject's `build-system` requirement (`hatchling`) from the network at build
  time, unpinned, which defeats the lock entirely. That applies to the release
  build (`python -m build --no-isolation`) *and* to each editable install
  (`pip install --no-deps --no-build-isolation -e .`) -- an editable install is
  still a PEP 517 build, and `--no-deps` does not cover its build-system
  requirements. The backend comes from `requirements/build.txt`, which also pins
  `editables`: hatchling imports it lazily when building an editable wheel and
  does not declare it, so the install fails without it.

  The check that this actually holds is an install with `--no-index`. If either
  path still resolves something from the network, it cannot complete offline.
- One workflow job is one Python environment. Locks installed by different steps
  of the same job must agree on shared transitive packages, and the test derives
  those groupings from the workflows rather than hard-coding them. Locks that
  never share an environment may disagree -- `requirements/docs.txt` pins an
  older `markdown-it-py` than the runtime closure because `myst-parser` requires
  it, and that is fine.

### 3. Fuzzing targets the consumer boundary, and actually runs

Scorecard's Python fuzzing detector looks for Atheris. This repository parses
attacker-controlled pack content -- YAML, tar members, symlinks -- so a fuzz
target here is genuine security work rather than a detector-shaped marker.

`fuzz/fuzz_validate_pack.py` fuzzes `validate_pack()`, whose documented contract
is falsifiable: invalid foreign input returns bounded error codes, and unexpected
defects raise. The harness asserts exactly that, and deliberately does **not**
catch exceptions from the call -- swallowing them would convert real defects into
silent passes. Only the harness's own workspace setup is guarded.

`content_ci.main()` and the author-side validators are explicitly **not** fuzzed.
They intentionally resolve imports and execute catalog-controlled code
([ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md)); pushing
attacker input through a path designed to trust it would be a vulnerability, not
a test.

`.github/workflows/fuzz.yml` runs a bounded session on pull requests and a longer
one weekly. Throughput is roughly 4-5 executions per second, bounded by the cost
of a full pack validation through the pinned ACES SDL parser -- so a pull-request
session explores hundreds of cases, not millions. This is a regression guard and
a slow explorer, not a substitute for OSS-Fuzz. Recording the real number here so
nobody mistakes a green run for exhaustive coverage.

### 4. Repository settings are recorded here because git cannot hold them

Branch protection on `main`:

| Setting | Value |
|---|---|
| Force pushes / deletions | blocked |
| Pull request required | yes |
| Required approving reviews | **1** |
| Code-owner review required | **no** (see below) |
| Dismiss stale reviews | yes |
| Require branch up to date (`strict`) | yes |
| Required status check | `verify` |
| Require last-push approval | **no** |
| Administrator enforcement | **no** |

Two repository *rulesets* sit alongside this and pin merge methods -- `dev` is
squash-only, `main` is merge/rebase-only. They require zero approvals, so they
add no review friction, but note that rulesets have no bypass actors configured
and therefore cannot be admin-overridden the way the settings above can.

**This does not reach Scorecard's top tier, and that is a deliberate, bounded
decision rather than an oversight.**

Scorecard's tier 4 wants two approving reviews and tier 5 wants administrator
enforcement. This repository has a single active maintainer, and **GitHub does
not permit a pull request author to approve their own pull request.** Any
configuration that requires an approval the maintainer cannot supply, while also
enforcing it against administrators, does not harden the repository -- it stops
all work, including security fixes. Requiring *one* approval rather than two
changes nothing about that: one is already unobtainable.

So administrator enforcement stays off, which preserves
[ADR 0016](0016-automate-dependency-updates.md)'s bypass. That bypass is what
lets the maintainer merge at all, and it is also what lets release-please's own
release PR and bot-created back-merge PRs land, since neither triggers the
required checks (both are opened with `GITHUB_TOKEN`).

Code-owner review is off for the same reason, and specifically because leaving it
on bought nothing. Scorecard's tier 4 requires code-owner review **and** two
approving reviews; with one approval that tier cannot be satisfied either way, so
the setting scored zero points while costing an override on every merge.
`.github/CODEOWNERS` is still committed, so enabling it is a one-line change when
a second maintainer makes tier 4 reachable.

The single-approval requirement is still declared rather than deleted. It costs
the maintainer one "merge without waiting for requirements" override per merge,
and becomes enforceable automatically the moment a second reviewer exists --
which is the point of leaving it in place.

The required `verify` status check is kept because it is worth real points
(tier 3) and runs normally on maintainer-opened pull requests. It does not report
on release-please's release pull request or the bot back-merge pull request,
since neither triggers workflows when opened with `GITHUB_TOKEN`; those merge via
the same administrator override, exactly as before this decision.

Consequence for the score: `Branch-Protection` satisfies tiers 1-3 and caps
around **8/10** rather than 10. It therefore remains a reported finding. The
honest path to 10 is a second reviewer, or a PAT for release-please so its checks
run under enforcement -- not a setting that makes the repository unworkable.

### 5. Signer identity is bound to the repository path

Recorded in [ADR 0017](0017-sign-release-tags-with-keyless-sigstore.md) rather
than here, but reached during this work: a repository transfer changes the OIDC
certificate identity, GitHub's redirect does not apply to identity matching, and
a stale value fails verification closed. The move to `RAESystem/env-packs` would
have blocked every subsequent release.

### 6. Documentation is published from the same locked toolchain

Read the Docs builds `docs/` with Sphinx + MyST from `requirements/docs.txt`,
hash-locked like every other install, with `fail_on_warning` so a broken
cross-reference fails the build instead of publishing. The package is not
installed for the docs build: the pages are narrative, and installing would pull
the entire pinned `aces-sdl` runtime closure to render markdown.

### 7. Findings this repository accepts, and why

These are **not** suppressed, filtered, or excluded from the SARIF upload. They
are reported, visible, and understood:

| Check | Why it is not fixed by a change here |
|---|---|
| `Branch-Protection` | Caps at tier 3 (~8/10) per §4. Tiers 4-5 need a second reviewer and administrator enforcement, which a single-maintainer repository cannot supply without blocking its own security fixes. |
| `Code-Review` | Scores the last ~30 changesets and does not count self-merges. With one active maintainer there is nobody to approve, and fabricating reviews to clear it would be fraud against the control. |
| `CI-Tests` | Historical, 25/27 at the time of writing. Self-heals as new PRs land with CI green. |
| `SAST` | Historical, 22/30 commits. CodeQL (#132) runs on every PR now, so this rises as commits accrue. |
| `CII-Best-Practices` | Requires registering the project at bestpractices.dev and completing a maintainer self-certification. It is external state that no repository change can produce. |
| `Maintained` | Excluded by #142. Time-based; the repository was created within 90 days. |
| `Contributors` | Excluded by #142. Reflects the contributor base, not the code. |

The general rule this table encodes: **a Scorecard finding is either fixed or
explained, never silenced.** Setting a scanner non-blocking, adding a suppression
entry, or narrowing the reported scope to reach a green number is prohibited.
Suppression is legitimate only for a factually false finding, and the rationale
must say why it is false.

## Consequences

- Adding a workflow means declaring a read-only top-level `permissions` block and
  SHA-pinning its actions, or `tests/test_workflow_permissions.py` fails.
- Adding a CI tool means adding a `requirements/*.in`, regenerating the lock with
  `uv pip compile --generate-hashes`, and installing it with `--require-hashes`.
- Bumping `aces-sdl` now touches `pyproject.toml` and `requirements/runtime.txt`
  together; the contract test fails if they drift. This is intentional -- ADR 0011
  keeps that bump under human review.
- Merges to `main` surface a review requirement the sole maintainer satisfies with
  an administrator override per §4. If a second maintainer joins, remove the
  override habit first and the rules become real without any settings change.
- The Scorecard score is only observable from a default-branch run. Local tests
  verify the workflow *shapes*; they cannot verify repository rules, historical
  review evidence, or published results. Acceptance for #142 is a fresh
  default-branch run, not a green local suite.
