# ADR 0039 — Demote breaking changes to minor releases

- Status: Accepted
- Date: 2026-10-19
- Amends: [ADR 0008](0008-adopt-release-please.md) (commit contract)

## Context

ADR 0008 lets release-please bump the major version for each `feat!:`,
`fix!:`, `BREAKING CHANGE:`, or `BREAKING-CHANGE:` commit. The package is at
6.x, and the major version increases quickly. The maintainer wants a major
release only by a deliberate decision.

Release-please has no setting that demotes a breaking change to a minor bump
after 1.0. The `bump-minor-pre-major` option applies only to 0.x versions.

## Decision

- A breaking change uses `feat:` and gets a minor release. The PR body
  describes the break in prose.
- The required PR title guard (`tools/check_pr_title.py`) rejects every marker
  that release-please reads as breaking:
  - a `!` after the type in the PR title;
  - a `BREAKING CHANGE` or `BREAKING-CHANGE` token in the PR body or in a PR
    commit message;
  - a `<type>!:` line in the PR body or in a PR commit message.
- The guard checks the commit messages because the squash commit body holds
  them (`squash_merge_commit_message: COMMIT_MESSAGES`).
- A major release is a deliberate act. Add a commit with a
  `Release-As: X.0.0` footer to the PR branch, for example:

  ```sh
  git commit --allow-empty -m "chore: release 7.0.0" -m "Release-As: 7.0.0"
  ```

## Consequences

- Release-please does not make a major release unless a `Release-As` footer
  tells it to.
- The changelog has no "Breaking changes" section. Readers find a break in the
  `feat` entry and its PR.
- A maintainer who edits the squash message at merge time can still add a
  breaking marker. The guard does not see that edit.
