# ADR 0008 — Adopt release-please

- Status: Accepted
- Date: 2026-07-06
- Supersedes: the versioning + release mechanism of
  [ADR 0007](0007-changelog-driven-versioning.md) (and 0006). ADR 0004 (SBOM),
  PyPI OIDC, and the PR-title guard still hold.

> **Reusable blueprint.** Per-repo variables: `{{DIST}}` = PyPI name,
> `{{IMPORT}}` = import package, `{{REPO}}` = `owner/repo`. Here:
> `aces-scenario-packs`, `aces_scenario_packs`, `Brad-Edwards/aces-scenario-packs`.

## Context

Every home-grown approach so far (hatch-vcs tags, a committed literal + a custom
`tools/release.py`, towncrier collation) left a manual step: someone had to run a
script or hand-collate the changelog to cut a release. The requirement is that a
release is produced by **merges only** — no scripts to remember. That is exactly
what [release-please](https://github.com/googleapis/release-please) does.

## Decision

Use **release-please** as the release manager.

### 1. Version = a static committed literal, bumped by release-please
`pyproject.toml` has `[project].version = "X.Y.Z"` (no `dynamic`, no hatch-vcs).
release-please rewrites that string on release. `{{IMPORT}}/__init__.py` derives
`__version__ = importlib.metadata.version("{{DIST}}")` so there's one source.

### 2. Changelog = release-please
release-please owns `CHANGELOG.md`. Feature PRs never touch it (no collisions).
towncrier and `changelog.d/` are removed.

### 3. Commit contract (what release-please reads)
Squash-merge feature PRs; the PR title is a Conventional Commit:
`feat:`→minor, `fix:`/`perf:`→patch, `feat!:`/`BREAKING CHANGE:`→major (pre-1.0
demotes major→minor); `docs`/`chore`/`refactor`/`test`/`ci`/`build`→no release.
The required PR-title guard keeps this enforced on `dev` and `main`.

### 4. Config
- `.release-please-manifest.json`: `{ ".": "X.Y.Z" }` (current released version;
  `0.0.0` until the first release).
- `release-please-config.json`: `release-type: python`, `package-name: {{DIST}}`.
- `.github/workflows/release-please.yml` (`on: push: [main]`):
  - job **release-please** (`googleapis/release-please-action`, SHA-pinned) →
    outputs `release_created`, `tag_name`.
  - job **publish** (`needs: release-please`, `if: release_created == 'true'`,
    `environment: pypi`, `id-token: write`): build → CycloneDX SBOM (ADR 0004) →
    `pypa/gh-action-pypi-publish` (OIDC) → attach dist + SBOM to the release.
  - All third-party actions SHA-pinned.

### 5. PyPI (one-time, per repo)
Register a pending trusted publisher: project `{{DIST}}`, owner, repo, workflow
**`release-please.yml`**, environment `pypi`.

## Flow
Features land on `main` (via `dev`). release-please auto-maintains a
`chore(main): release X.Y.Z` PR with the version bump + `CHANGELOG.md`. **Merge
that PR → it tags and publishes.** Nothing is hand-run; feature PRs never edit
`CHANGELOG.md`.

## Caveat
The release PR is opened by `GITHUB_TOKEN`, so required CI checks don't auto-run
on it — **admin-merge it**, or give release-please a stored PAT so its checks run.

## Consequences
- Releases are merge-only; no scripts, no towncrier, no hand-collation.
- The version has one source (`pyproject.toml`), rewritten by release-please;
  `__version__` reads it from metadata.
- Ordering for dependents still applies (publish a dependency before its
  consumer).
