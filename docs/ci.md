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
pull-request `ci.yml` runs (the first runs of the new workflow) and recorded here
during this change's CI monitoring, before the work is finalized, using the same
metadata and p95 method as the before cohort.

- Workflow revision: _head commit of the measured runs (recorded with the cohort)_
- Sample window: _recorded with the cohort_
- Sample count: _recorded with the cohort_

| Metric | Median | p95 |
| --- | --- | --- |
| event → `verify` complete (required check) | _measured on this change's runs_ | _measured on this change's runs_ |
| event → last check complete (`verify` + `sonar`) | _measured on this change's runs_ | _measured on this change's runs_ |

The design reason the numbers should improve: the required `verify` check now
completes near the slowest single mandatory job rather than the sum of the serial
steps, and the full run near `max(verify, sonar)`, because `sonar` no longer waits
for `verify` and no longer re-runs the suite. The measured rows above are the
authority; this paragraph is only the rationale.
