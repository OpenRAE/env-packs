# ADR 0044 — Restore breaking changes to major releases

- Status: Accepted
- Date: 2026-10-30
- Supersedes: [ADR 0039](0039-demote-breaking-changes-to-minor-releases.md)
- Restores: the commit contract of [ADR 0008](0008-adopt-release-please.md)

## Context

[ADR 0039](0039-demote-breaking-changes-to-minor-releases.md) stopped a
breaking change from bumping the major version. It made a breaking change use
`feat:` for a minor release. The PR title guard rejected every breaking marker.
Only a `Release-As: X.0.0` footer made a major release.

The maintainer wants the default behaviour back. A breaking change must bump the
major version on its own, as release-please reads it. This restores the commit
contract that [ADR 0008](0008-adopt-release-please.md) set.

## Decision

- A breaking change uses `feat!:`, `fix!:`, or a `BREAKING CHANGE:` /
  `BREAKING-CHANGE:` footer. Release-please bumps the major version for it
  (pre-1.0 demotes a major to a minor).
- The PR title guard (`tools/check_pr_title.py`) does not reject breaking
  markers. It keeps the Conventional Commit shape check and the agent-brand
  prefix ban.
- The PR title workflow (`.github/workflows/pr-title.yml`) does not fetch the PR
  commit messages or read the PR body for breaking markers.
- The `Release-As: X.0.0` footer stays available for a deliberate major release,
  as [ADR 0008](0008-adopt-release-please.md) describes.

## Consequences

- Release-please bumps the major version for a breaking change again.
- The guard is simpler. It checks the PR title only, not the body or the
  commits. The workflow needs no `pull-requests: read` permission.
- [ADR 0039](0039-demote-breaking-changes-to-minor-releases.md) is superseded.
  The commit contract of [ADR 0008](0008-adopt-release-please.md) is in force.
