# Implementation plan rules

Repo-specific rules the `/implement` workflow MUST follow here, in addition to
the generic workflow. Ground Control injects this file into planning via
`.ground-control.yaml` (`rules.plan_rules`).

## Releases & versioning (ADR 0008 — hard requirement)

- **Never hand-edit the version or changelog.** The version lives in
  `pyproject.toml` (`[project].version`) and is bumped by **release-please** only;
  `__version__` derives from installed metadata. Do **not** edit `[project].version`,
  `__version__`, or `CHANGELOG.md` in a feature PR — release-please owns them. A PR
  that does is wrong; drop that change.
- **The PR title (Conventional Commit) is the release decision** — there are no
  changelog fragments and no scripts to run. Rubric: `feat:`→minor,
  `fix:`/`perf:`→patch, `feat!:`/`BREAKING CHANGE:`→major (pre-1.0 → minor);
  `docs`/`chore`/`refactor`/`test`/`ci`/`build`→no release.
- **PR titles MUST be Conventional Commits** — a required CI check
  (`PR title guard`, `tools/check_pr_title.py`) blocks non-conforming titles and
  bans agent/tool prefixes like `[claude]`/`[codex]`.
- **Do not add ad hoc release/tag/publish paths to ordinary feature work.**
  release-please maintains the `chore(main): release X.Y.Z` PR automatically; a
  human merges it to publish. An issue explicitly changing release architecture
  must keep the logic in the canonical `.github/workflows/release-please.yml`
  and amend the governing ADR rather than add a parallel workflow (ADR 0017).
- **Merge habits:** feature PRs are **squash-merged** (the title becomes the
  Conventional Commit release-please reads). Open `dev`→`main` promotions with
  `make devmain` and merge them with a **merge commit**, never squash or rebase,
  so release-please retains every promoted Conventional Commit subject.

See [ADR 0008](../docs/decisions/adrs/0008-adopt-release-please.md).

## Repository boundary

- This repo **defines and validates** the scenario-pack format; it does not host
  actual scenario packs. Keep changes within that boundary (see
  [`scenario-packs.md`](../docs/scenario-packs.md) and ADR 0001).
