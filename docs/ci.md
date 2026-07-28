# Continuous integration

How this repository verifies a pull request, what blocks a merge, and how to
reproduce each check locally. The workflow files under `.github/workflows/` are
authoritative; this page explains their shape. The design rationale is
[ADR 0029](decisions/adrs/0029-parallel-pr-feedback-with-a-complete-merge-gate.md).

## The check surface on a pull request

A PR into `dev` (or `main`) runs several **independent** GitHub Actions
workflows concurrently:

| Workflow | Checks | Blocks merge? |
| --- | --- | --- |
| `ci.yml` | `compile`, `tests`, `audit`, `content`, **`verify`**, `sonar` | only **`verify`** |
| `codeql.yml` | `Analyze (python)` — SAST | branch-protection dependent |
| `fuzz.yml` | `Fuzz validate_pack` — bounded fuzzing of the untrusted-pack boundary | branch-protection dependent |
| `pr-title.yml` | `PR title guard` — Conventional Commit shape | branch-protection dependent |

`scorecard.yml` publishes supply-chain posture from `main` and on a schedule; it
does not run on pull requests.

## Fast-feedback lanes (inside `ci.yml`)

`ci.yml` runs its mandatory work as four **independent** jobs so a failure in one
does not wait behind an unrelated stage, and the fastest actionable signal
arrives first:

- **`compile`** — `python -m compileall src tests`. No dependency install at all,
  so a syntax error fails in seconds. This is the earliest lane.
- **`tests`** — installs the hash-locked runtime + coverage + build closure, then
  runs the whole unit suite under coverage (`coverage run -m unittest discover -s
  tests`) and uploads `coverage.xml`. This job is the single **coverage
  authority**.
- **`audit`** — `pip-audit` over the installed runtime + build + audit-tool
  closure, with a bounded retry for the network-backed advisory service.
- **`content`** — `raes-pack-validate --repo .` and `raes-pack-release check
  --all`.

Because they no longer share a job, a broken test surfaces on the `tests` check
without waiting for the `pip-audit` network lookup, and vice versa.

## The full merge gate: `verify`

Branch protection requires exactly one status context: **`verify`**. It is not a
worker — it is a **fail-closed aggregate**. It `needs` every mandatory job,
runs even when one of them fails (`if: always()`), and is green **only when every
mandatory result is `success`**. A failed, cancelled, or unexpectedly skipped
mandatory job blocks the merge. So the complete pre-merge verification stays
mandatory even though the work now runs in parallel.

Adding a new mandatory check means adding its job to `verify`'s `needs` and to the
result check inside it. `tests/test_ci_topology.py` fails if a mandatory job is
left out of the aggregate.

## Optional analysis: `sonar`

`sonar` is a secret-backed quality gate. It depends **only** on the `tests`
coverage producer, downloads that same-run `coverage.xml`, and runs the
SonarCloud scan — it does **not** re-run the suite. It is skipped for fork and
Dependabot pull requests (which cannot see `SONAR_TOKEN`) and therefore is **not**
part of the universally-required `verify` aggregate; the post-merge push to
`dev`/`main` scans the integrated code with full token access. The assigned
SonarCloud quality gate stays strict (`sonar.qualitygate.wait=true`).

## Shard ownership

The unit suite is **not sharded**. It is a single job (`tests`) that runs one
`unittest discover -s tests`, so every test executes exactly once per run. At 474
tests in about 14 seconds locally, splitting the suite across runners would add
more per-shard install and coverage fan-in overhead than it removes
([ADR 0029](decisions/adrs/0029-parallel-pr-feedback-with-a-complete-merge-gate.md)).
If GitHub-hosted p95 evidence later justifies sharding, the scaling seam is a
single canonical test inventory assigning every test to exactly one
`(shard_index, shard_count)` pair whose manifests are proven disjoint with a
complete union before coverage is combined — never hand-maintained per-shard file
lists.

## Reproduce a failing check locally

Each check maps to a command you can run from the repository root. These mirror
`.github/workflows/ci.yml` (and, for the local loop, `AGENTS.md`), which remain
the source of truth.

| Check | Reproduce locally |
| --- | --- |
| `compile` | `python -m compileall src tests` |
| `tests` | `python -m unittest discover -s tests` (add coverage: `coverage run -m unittest discover -s tests && coverage xml`) |
| `audit` | `python -m pip install -r requirements/pip-audit.txt && pip-audit` |
| `content` | `raes-pack-validate --repo .` then `raes-pack-release check --all` |
| `sonar` | runs in CI only (needs `SONAR_TOKEN`); the coverage input is the `coverage.xml` from `tests` |
| `PR title guard` | `python tools/check_pr_title.py` (reads the PR title from the event) |

## Timing evidence

End-to-end GitHub Actions time, including queueing, measured from event creation
to job completion for a fixed cohort of non-cancelled pull-request `ci.yml` runs.
Median and nearest-rank p95. Push, schedule, and rerun populations are excluded.

**Before** — serial `verify`, then `sonar` re-installing and re-running the whole
suite for coverage.

- Workflow revision: `9af729dc05b07d9aa39577231deb906db3b2e07c` (the pre-change
  `ci.yml`, `sonar` gated by `needs: [verify]`)
- Sample window: 2026-07-28T02:26:20Z – 2026-07-28T17:09:32Z
- Sample count: 15 runs
- p95 method: nearest-rank

| Metric | Median | p95 |
| --- | --- | --- |
| event → `verify` complete (required check) | 42s | 47s |
| event → last check complete (`verify` + `sonar`) | 139s | 149s |

**After** — parallel mandatory jobs behind the `verify` aggregate, with coverage
produced once by `tests` and handed to `sonar`. Measured from this change's own
pull-request `ci.yml` run.

- Workflow revision: `cf8d81fd300a6c1f6618b1e9d07e289a5bfbf78b`
- Sample window: 2026-07-28T18:54:22Z (single pull-request run)
- Sample count: 1 run — the first run of the new workflow, with a **cold pip
  cache**; the first run populates the cache and warms subsequent runs
- p95 method: nearest-rank (n=1, so median = p95)

| Metric | Median | p95 |
| --- | --- | --- |
| event → `verify` complete (required check) | 54s | 54s |
| event → last check complete (`verify` + `sonar`) | 107s | 107s |

Per-job first feedback on that run (event → job complete): `compile` 10s,
`content` 33s, `audit` 35s, `tests` 50s — each an independent check, versus the
before design where the first signal was the unit-test step roughly 30s into the
single serial `verify` job.

What the numbers show, honestly:

- **Total wall-clock** dropped from a 139s median to 107s (~23%): `sonar` overlaps
  the mandatory jobs and no longer re-runs the suite.
- **First actionable feedback** is materially earlier — `compile` at ~10s and the
  independent `audit`/`content` checks by ~35s, rather than one serial job.
- The required **`verify`** gate is roughly flat (54s here vs a 42s before median).
  On this first run the pip cache was cold, and `tests` now carries the coverage
  run plus the artifact upload that feeds `sonar`, which puts it on `verify`'s
  critical path; warm-cache runs recover most of the install time. The change
  trades a flat required-gate time for the total-wall-clock and first-feedback
  wins above. This is a doc-only revision of `cf8d81f`; `ci.yml` is unchanged, so
  the run above is the authority.
