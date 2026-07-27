# ADR 0020 — No auto-merge; a human merges every pull request

- Status: Accepted
- Date: 2026-07-27
- Supersedes: the auto-merge (option A1) decision of
  [ADR 0016](0016-automate-dependency-updates.md)

## Context

[ADR 0016](0016-automate-dependency-updates.md) adopted auto-merge for GitHub
Actions bumps and non-`aces-sdl` runtime bumps: `.github/workflows/dependabot-auto-merge.yml`
called `gh pr merge --auto --squash` on Dependabot PRs, and GitHub held them
until `dev`'s required `verify` check went green. The stated benefit was removing
the manual-edit toil around routine patching.

The rest of ADR 0016 solved that toil directly and still holds: the pinned
version has one source of truth in `pyproject.toml`, and the tests assert the
exact-pin *invariant* rather than a literal version, so a bump stays green with
no manual test edit. Auto-merge was never what removed the toil — it only removed
the person.

What it added was a merge into `dev` that no human saw. `verify` being green is
evidence the tests passed, not evidence the change was reviewed; a dependency
bump is exactly the class of change where a compromised or malicious upstream
release is green by construction. The saved effort is a few clicks a week
against an unattended write path into the integration branch.

Auto-merge also cannot be disabled by deleting the workflow alone. The repository
setting `allow_auto_merge` is a separate, standing capability: while it is on,
auto-merge can be enabled on any pull request by hand or by any token holding
`pull-requests: write`.

## Decision

**No auto-merge anywhere in this repository. A human merges every pull request.**

Concretely:

1. `.github/workflows/dependabot-auto-merge.yml` is deleted. No workflow enables,
   requests, or completes a merge.
2. The repository setting `allow_auto_merge` is `false`, so the capability is
   absent rather than merely unused.
3. `tests/test_workflow_permissions.py` fails if any workflow reintroduces
   auto-merge — by `gh pr merge --auto`, the `enable-pull-request-auto-merge`
   GraphQL mutation, or an equivalent action. The decision is enforced, not just
   recorded.

Everything else in ADR 0016 is unchanged and still in force: the single source of
truth for the pin, the invariant-not-literal tests, Dependabot's weekly grouped
PRs against `dev`, `fix(deps)` for runtime bumps and `chore` for Actions bumps,
and `aces-sdl`'s ungrouped human-reviewed PR (ADR 0011).

Branch protection on `dev` is unchanged: `verify` stays a required check. That
gate exists to stop broken code and is unrelated to who presses merge. Removing
auto-merge makes merges *more* human-gated, never less.

## Consequences

- Routine dependency patching now costs a human merge per PR. That is the point;
  it is a few clicks a week, and it is the only step at which a person sees what
  is entering `dev`.
- Dependabot PRs may sit longer. They are grouped weekly, so the queue is small,
  and a stale bump PR is a visible backlog rather than a silent merge.
- ADR 0016's note that auto-merging `aces-sdl` itself (option A2) would require
  amending ADR 0011 is now moot: no bump auto-merges, load-bearing or not.
- The `allow_auto_merge` setting is repository configuration, not source, so it
  is not enforced by a test in this repo. The workflow-level guard covers every
  automated path; the setting closes the manual one.
- Re-adopting auto-merge means a new ADR superseding this one, not flipping a
  setting back.
