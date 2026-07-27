# ADR 0019 — Preserve history in dev-to-main promotions

- Status: Accepted
- Date: 2026-07-27
- Amends: [ADR 0008](0008-adopt-release-please.md)

## Context

Release-please reads the Conventional Commit history on `main` to decide the
version bump and build `CHANGELOG.md`. Feature PRs are squash-merged into `dev`,
where each PR title becomes one release-decision commit. A squashed `dev` to
`main` promotion would collapse that batch and discard those individual
subjects.

Promotion PRs have also been opened with GitHub's default `Dev` title and blank
pull-request-template boilerplate. The feature PR-title guard intentionally
targets `dev`, not promotion PRs whose base is `main`, so it is not the right
control for this workflow.

## Decision

Use the repository's `make devmain` helper as the canonical way to open a
`dev` to `main` promotion PR. It supplies a deterministic, non-releasing
`chore: promote dev to main` title and a complete body that tells the human
merger to use a **merge commit**, never squash or rebase, and explains the
release-please history requirement.

The helper opens only the PR. GitHub remains the authorization and duplicate-PR
boundary, and the existing approving-review and `verify` requirements remain
the merge gate. An already-open promotion is a visible failure, not a successful
no-op. The Makefile must have a safe, non-mutating default target so a bare
`make` cannot open a PR accidentally.

Do not extend the feature PR-title workflow to `main`, add another release
workflow, or automate approval or merging as part of this helper.

## Consequences

- Individual release-driving commits remain visible to release-please on
  `main`.
- Promotion PRs are recognizable and cannot collide with release-please's
  `chore(main): release X.Y.Z` PR.
- Opening a promotion still requires an authenticated GitHub CLI, and merging
  remains an explicit human action.
