# ADR 0047 — Merge dev pull requests through a merge queue

- Status: Accepted
- Date: 2026-11-11
- Amends: the human-merge rule of [ADR 0020](0020-no-auto-merge.md) for `dev` only
- Extends: [ADR 0029](0029-parallel-pr-feedback-with-a-complete-merge-gate.md)
- Coordination: OpenRAE/env-packs issue 678

## Context

ADR 0020 makes a person merge each pull request.
Each merge into `dev` makes the other open pull requests out of date.
Each update runs the full CI again.

A GitHub merge queue tests each pull request against the latest `dev`, and then merges it.
The queue runs the required checks on a merge group.
A merge group contains `dev`, the pull requests in front of it, and the pull request.
GitHub reports a required check on a merge group only when its producer runs on the `merge_group` event.
If a required check does not report, the queue does not merge the pull request.

`verify` is the only required context on `dev` and on `main`.
The `ci.yml` workflow produces it.

The GitGuardian App posts its check on pull request commits only.
A merge group commit has no pull request, so the App check does not report on a merge group.

## Decision

- `dev` uses a merge queue. `main` does not use a merge queue, and its merges stay manual.
- The `merge-policy-dev` ruleset holds the queue.
  The queue builds merge groups that contain more than one pull request.
- The queue squash-merges.
  The repository squash title is the pull request title, so the title stays the release decision (ADR 0008).
- `ci.yml` runs on `merge_group` events for `dev`.
  `verify` and each job that it gates run on each merge group, with no condition that can skip them.
- The prose check diffs a merge group against the merge group base.
- A ggshield job in `gitguardian.yml` produces the `GitGuardian secret scan` context on `pull_request` and `merge_group` events.
  It scans each commit in the range of the event.
  `dev` requires the context. The GitGuardian App stays installed.
- The ggshield job fails when the API key is not available, for example on a pull request from a fork.
  It also fails when the event has no valid commit range.
- `requirements/ggshield.txt` pins ggshield with hashes.
  `requirements/ggshield.overrides` raises oauthlib to a version without known vulnerabilities.
- SonarCloud scans a merge group.
  It runs the pull request analysis of the queued pull request against `dev`.
  It fails closed when the merge group ref does not name a pull request that targets `dev`.
- `dev` does not use strict status checks. `main` keeps strict status checks.
- The maintainer authorizes the `/implement` and `/quickfix` readiness step to add a pull request that targets `dev` to the queue.
  Readiness adds it after it records the Phase E handoff, so the pull request cannot merge before readiness.
- The maintainer adds each other pull request to the queue.
- No workflow merges a pull request or adds one to the queue.
  The repository setting `allow_auto_merge` stays `false`.
- The main to dev back-merge keeps its merge commit.
  The release procedure merges it through the existing bypass for the repository admin role.
  Readiness never uses that bypass.

## Enforcement

- `tests/test_ci_topology.py` fails when `ci.yml` has no `merge_group` trigger for `dev`.
  It also fails when a job that `verify` gates has a job-level condition.
- `tests/test_gitguardian_workflow.py` fails when the ggshield job has no `merge_group` trigger for `dev`.
  It also fails when a condition can skip the scan, or an option can downgrade a finding.
- `tests/test_workflow_permissions.py` fails when a workflow merges a pull request, turns on auto-merge, or adds a pull request to the queue.
- The queue, the strict setting, and the bypass are repository configuration.
  No test in this repository reads them, as ADR 0020 records for `allow_auto_merge`.

## Consequences

- A pull request that readiness hands off merges when its merge group passes the required checks, with no manual step.
- A failed check on a merge group removes the pull request from the queue, and the pull request does not merge.
- A new required context on `dev` needs a producer with a `merge_group` trigger, or the queue stops.
- The diff of a merge group also contains the pull requests in front of it.
- Dependency update pull requests still need a person to add them to the queue (ADR 0020).
