# ADR 0023 — Recover interrupted signed releases

- Status: Accepted
- Date: 2026-07-28
- Amends: [ADR 0017](0017-sign-release-tags-with-keyless-sigstore.md)

## Context

Release Please runs in PR-only mode. After a release PR merges, the repository's
workflow signs and verifies the tag, builds and attests the distribution,
publishes it to PyPI, creates the GitHub Release, and then advances the Release
Please label from `autorelease: pending` to `autorelease: tagged`.

The `2.0.2` release stopped during immediate transparency-log verification.
No tag or distribution was published, the release PR remained pending, and
Release Please treated every later main push as a successful no-op because an
untagged merged release PR was outstanding. Rerunning the historical workflow
after the repository transfer would also bind signing verification to the old
repository identity.

## Decision

The canonical release workflow supports an explicit `workflow_dispatch`
recovery input naming the interrupted release PR. Recovery is accepted only
when GitHub reports that PR as merged into `main`; its labels still pass through
the same `autorelease: pending` authorization gate, and its version and manifest
transition pass through the same parser-backed validation as a normal release.
The workflow derives both parent and target commits from that PR and builds,
tags, attests, and publishes the target commit—not the dispatch branch head.

Sigstore verification retries five times with bounded delay to tolerate
transparency-log propagation. It remains fail-closed after the final attempt,
and tag identity verification still occurs before any tag push or artifact
publication.

Publication steps are rerun-safe. Existing verified tags and GitHub Releases are
reused, PyPI skips an already-uploaded immutable version, and release assets are
uploaded with replacement semantics. The release PR is relabeled
`autorelease: tagged` only after every publication destination succeeds. Until
then, the pending label deliberately blocks later release PRs and authorizes
another recovery attempt.

## Consequences

- An interrupted release can be resumed without forging labels, changing a
  version, deleting a tag, force-pushing, or weakening signer identity.
- A manually dispatched run cannot publish an arbitrary branch or commit.
- A permanently invalid signature, mismatched tag target, malformed version,
  non-main PR, or missing Release Please authorization still fails closed.
- Operators can distinguish a completed release from a blocked one by the
  release PR label, tag, GitHub Release, and PyPI version agreeing.
