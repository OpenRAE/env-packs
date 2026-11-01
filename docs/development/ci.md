# Continuous integration

This page tells how the repository verifies a pull request, what blocks a
merge, and how to run each check locally. The workflow files in
`.github/workflows/` are the authority, and this page explains their shape.
[ADR 0029](../decisions/adrs/0029-parallel-pr-feedback-with-a-complete-merge-gate.md)
records the design.

## The checks on a pull request

A pull request starts several **independent** GitHub Actions workflows at the
same time:

| Workflow | Checks | Blocks merge? |
| --- | --- | --- |
| `ci.yml` | `compile`, `tests`, `audit`, `content`, `docs`, `go`, `go-lint`, `go-arch`, **`verify`**, `sonar` | only **`verify`** |
| `codeql.yml` | `Analyze (python)`: static security analysis | depends on branch protection |
| `fuzz.yml` | `Fuzz validate_pack`: bounded fuzzing of the untrusted-pack boundary. `Fuzz Go targets`: every native Go fuzz target | depends on branch protection |
| `pr-title.yml` | `PR title guard`: the Conventional Commit shape | depends on branch protection |

`scorecard.yml` publishes the supply-chain posture from `main` and on a
schedule. It does not run on pull requests.

`ci.yml` and `fuzz.yml` run on each pull request, whatever its base branch is. A
pull request of the Go port (ADR 0047) can use an unmerged chunk branch as its
base, and it still shows the full result.

## Fast-feedback lanes in `ci.yml`

`ci.yml` runs its mandatory work as **independent** jobs. A failure in one job
does not wait for an unrelated job, and the fastest signal arrives first.

- **`compile`**: `python -m compileall src tests`. It installs no dependency, so
  a syntax error fails in seconds. This is the earliest lane.
- **`tests`**: installs the hash-locked runtime, coverage, and build closure. It
  then runs the whole unit suite under coverage (`coverage run -m unittest
  discover -s tests`) and uploads `coverage.xml`. This job is the **coverage
  authority** for Python.
- **`audit`**: runs `pip-audit` over the installed runtime, build, and
  audit-tool closure. It retries a bounded number of times, because the
  advisory service is on the network.
- **`content`**: runs the legacy external-catalog checks
  (`raes-pack-validate --repo .` and `raes-pack-release check --all`). It also
  runs `raes-pack-validate --packs-root packs` and
  `raes-pack-release check --packs-root packs` for the first-party packs.
- **`docs`**: builds `docs/public/` with warnings as errors, and checks the
  publication boundary of the built site (ADR 0030).
- **`go`**: `make go-check` builds, vets, and tests every Go package with the
  race detector and in shuffled order. It uploads `coverage-go.out`. This job is
  the **coverage authority** for Go.
- **`go-lint`**: `make go-lint` runs the golangci-lint version that `mise.toml`
  pins and `mise.lock` verifies. It also checks the formatting and the module
  tidiness (see [the Go style map](go-style-map.md)).
- **`go-arch`**: `make go-arch` checks the Go code, the design records, and the
  C4 view against the architecture model (see
  [the design records](designs/README.md)).

The jobs do not share a runner. So a broken test shows on the `tests` check
without a wait for the `pip-audit` network lookup, and the reverse. The Go test
rules are in [the Go test standard](go-test-standard.md).

## The full merge gate: `verify`

Branch protection requires one status context: **`verify`**. It does no work
itself. It is a **fail-closed aggregate**: it `needs` every mandatory job, it
runs when one of them fails (`if: always()`), and it passes **only when every
mandatory result is `success`**. A failed, cancelled, or skipped mandatory job
blocks the merge. So the complete verification stays mandatory, and the work
still runs in parallel.

To add a mandatory check, add its job to the `needs` of `verify` and to the
result check inside it. `tests/test_ci_topology.py` fails when the aggregate
does not include a mandatory job.

## Optional analysis: `sonar`

`sonar` is a quality gate that needs a secret. It depends **only** on the two
coverage producers, `tests` and `go`. It downloads their same-run reports and
runs the SonarCloud scan. It does **not** run the suites again.

GitHub does not give `SONAR_TOKEN` to pull requests from forks or from
Dependabot. So `sonar` skips those pull requests, and it is **not** part of the
`verify` aggregate. The push after a merge into `dev` or `main` scans the
integrated code with full token access. The SonarCloud quality gate stays
strict (`sonar.qualitygate.wait=true`).

## Shard ownership

The Python unit suite is **not sharded**. One job (`tests`) runs one
`unittest discover -s tests`, so each test runs once in each run. When ADR 0029
recorded this decision, the suite had 474 tests and took about 14 seconds
locally. Shards would then add more install and coverage-merge time than they
save
([ADR 0029](../decisions/adrs/0029-parallel-pr-feedback-with-a-complete-merge-gate.md)).

If p95 measurements of GitHub-hosted runs later justify shards, use one
canonical test inventory. It assigns each test to exactly one
`(shard_index, shard_count)` pair. Before the coverage reports merge, a check
proves that the shard lists are disjoint and that their union is complete. Do
not keep a file list for each shard by hand.

## Run a failing check locally

Each check has a command that you can run from the repository root. The
commands follow `.github/workflows/ci.yml` and, for the local loop, `AGENTS.md`.
Those files stay the authority.

| Check | Run locally |
| --- | --- |
| `compile` | `python -m compileall src tests` |
| `tests` | `python -m unittest discover -s tests` (with coverage: `coverage run -m unittest discover -s tests && coverage xml`) |
| `audit` | `python -m pip install -r requirements/pip-audit.txt && pip-audit` |
| `content` | `raes-pack-validate --repo .` and `raes-pack-release check --all`, then the same gates with `--packs-root packs` |
| `docs` | `python -m sphinx -W -b html docs/public docs/public/_build/html`, then `python tools/check_docs_publication_boundary.py docs/public/_build/html` |
| `go` | `make go-check` |
| `go-lint` | `make go-lint` (after `mise install`) |
| `go-arch` | `make go-arch` (`make go-arch-design` in the design step) |
| `Fuzz Go targets` | `make go-fuzz` (set `FUZZTIME` to change the time for each target) |
| `sonar` | Runs in CI only, because it needs `SONAR_TOKEN`. Its inputs are `coverage.xml` from `tests` and `coverage-go.out` from `go` |
| `PR title guard` | `python tools/check_pr_title.py` (it reads the pull request title from the event) |

## Timing evidence

These numbers give the end-to-end GitHub Actions time, including the queue.
Each time starts at the event and ends when the job completes. The cohort is a
fixed set of pull-request `ci.yml` runs that were not cancelled. The tables give
the median and the nearest-rank p95. They exclude push, schedule, and rerun
runs.

**Before:** a serial `verify` job, then a `sonar` job that installed the
dependencies again and ran the whole suite again for coverage.

- Workflow revision: `9af729dc05b07d9aa39577231deb906db3b2e07c` (the `ci.yml`
  before the change, with `sonar` gated by `needs: [verify]`)
- Sample window: 2026-07-28T02:26:20Z to 2026-07-28T17:09:32Z
- Sample count: 15 runs
- p95 method: nearest rank

| Metric | Median | p95 |
| --- | --- | --- |
| event to `verify` complete (required check) | 42s | 47s |
| event to last check complete (`verify` and `sonar`) | 139s | 149s |

**After:** parallel mandatory jobs behind the `verify` aggregate. `tests`
produces the coverage once and gives it to `sonar`. The runs are the
pull-request `ci.yml` runs of the change itself.

- Workflow revision: `cf8d81fd300a6c1f6618b1e9d07e289a5bfbf78b`. The follow-up
  commits changed only documents, so each run below used the same workflow.
- Sample window: 2026-07-28T18:54:22Z to 2026-07-28T19:01:39Z
- Sample count: 2 pull-request runs. The first had a **cold** pip cache, and the
  second had a **warm** one.
- p95 method: nearest rank

| Metric | Median | p95 |
| --- | --- | --- |
| event to `verify` complete (required check) | 55s | 55s |
| event to last check complete (`verify` and `sonar`) | 105s | 107s |

Time from the event to the end of each job:

- Cold run: `compile` 10s, `content` 33s, `audit` 35s, `tests` 50s, `verify`
  54s, `sonar` 107s.
- Warm run: `compile` 12s, `content` 26s, `audit` 26s, `tests` 51s, `verify`
  55s, `sonar` 103s.

What the numbers show:

- **Total time** fell from a median of 139s to about 105s, about 25% less.
  `sonar` runs at the same time as the mandatory jobs and does not run the
  suite again.
- **The first useful signal** arrives earlier. `compile` finishes at about 10s,
  and `audit` and `content` finish by about 26 to 35s. Before, one serial job
  gave its first signal at the unit-test step, about 30s in.
- **The required `verify` gate** became slower, by about 12s: about 54 to 55s
  in both runs, against a median of 42s before. The cause is the structure, not
  the cache. `tests` now runs under coverage and uploads the artifact for
  `sonar`, so it is the critical path of the aggregate, at about 50s. The pip
  cache mainly speeds up `audit` and `content`, which are not on that path.
- This is the deliberate trade of ADR 0029: coverage runs once. A separate
  coverage producer for `sonar` would take coverage off the critical path of
  `verify`, but the suite would then run twice. ADR 0029 considered that and
  did not choose it.
