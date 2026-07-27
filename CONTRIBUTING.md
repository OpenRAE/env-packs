# Contributing

Thanks for helping improve the ACES scenario-pack definition and tooling! Please
open a GitHub issue to discuss a change before moving pack contracts, schemas,
templates, examples, or tools into this repository.

When you work on a change:

- Keep it scoped to the linked issue.
- Preserve the repository boundary described in `README.md` and
  `docs/scenario-packs.md` — this repo defines and validates the pack format; it
  does not host packs.
- Run the verification commands in `AGENTS.md` before opening a PR.
- **Never edit `CHANGELOG.md`** — release-please owns it.

## Changelog & releases

Releases are managed by **release-please** (ADR 0008) — merge-driven, nothing
hand-run. Your **PR title is a Conventional Commit** and decides the version:
`feat:`→minor, `fix:`/`perf:`→patch, `feat!:`/`BREAKING CHANGE:`→major (pre-1.0
demotes major→minor); `docs`/`chore`/`refactor`/`test`/`ci`/`build`→no release. A
CI check enforces conventional titles and bans agent-branding prefixes. Feature
PRs are squash-merged, so the title *is* the commit — get it right.

You never bump a version or edit the changelog. As PRs land on `main`,
release-please maintains a `chore(main): release X.Y.Z` PR (version bump +
`CHANGELOG.md`); merging that PR tags and publishes. See
[ADR 0008](docs/decisions/adrs/0008-adopt-release-please.md).

Work reaches `main` by promoting `dev`. Open that pull request with
`make devmain`, which gives it a deterministic `chore: promote dev to main`
title and a body stating the one rule that matters: **merge it with a merge
commit, never a squash or a rebase.** Squashing collapses the promoted Conventional Commit
subjects into one, and the next release loses both its changelog entries and its
version decision. See
[ADR 0019](docs/decisions/adrs/0019-preserve-history-in-dev-main-promotions.md).

Changes to the public contract or schemas should include the rationale, the
compatibility impact, and how you validated them. If you're moving content in
from another repository, note the source repo and paths, and any scrub the
content needs before it lands here.
