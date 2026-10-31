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
- **Never hand-edit a pack version.** Every pack under `packs/` carries the
  package version. The `sync-pack-versions` release job writes it and refreshes
  the pack digests (ADR 0045).
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

## Go port (ADR 0047)

- **Pull requests for the port target `go-cutover`.** A pull request that needs
  an unmerged chunk uses the branch of that chunk as its base. `dev` keeps the
  Python product until one pull request merges `go-cutover` into `dev`.
- **A pull request for the port uses a type that does not release:** `build`,
  `ci`, `docs`, `refactor`, `test`, or `chore`. Only the chunk that removes the
  Python implementation has a breaking-change title.
- **Python changes on `dev` are limited to fixes, security updates, and RAES
  dependency updates.** A sync pull request brings `dev` into `go-cutover`. When
  a `dev` change alters a contract, the sync pull request also changes the
  conformance corpus.

## Repository boundary

- This repo **defines and validates** the environment-pack format, publishes
  first-party infrastructure kits under `kits/`, and publishes major example
  packs under `packs/`. Co-location gives those packs no runtime role and no
  authority over RAES semantics. Keep changes within that boundary (see
  [`environment-packs.md`](../docs/public/environment-packs.md), ADR 0009, and
  ADR 0036).
