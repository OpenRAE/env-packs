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

Earlier approaches left a manual release step. These included hatch-vcs tags,
a version literal with `tools/release.py`, and towncrier collation. Someone
had to run a script or assemble the changelog. **Merges only** must produce
a release, with no release script to remember. This is what [release-please](https://github.com/googleapis/release-please) does.

## Decision

Use **release-please** as the release manager.

### 1. Version = a static committed literal, bumped by release-please
`pyproject.toml` has `[project].version = "X.Y.Z"` (no `dynamic`, no hatch-vcs).
release-please rewrites that string on release. `{{IMPORT}}/__init__.py` derives
`__version__ = importlib.metadata.version("{{DIST}}")` so there's one source.

### 2. Changelog = release-please
release-please owns `CHANGELOG.md`. Feature PRs never touch it (no collisions).
The repository no longer uses towncrier or `changelog.d/`.

### 3. Commit contract (what release-please reads)
Squash-merge feature PRs; the PR title is a Conventional Commit:
`feat:`→minor, `fix:`/`perf:`→patch, `feat!:`/`BREAKING CHANGE:`→major;
`docs`/`chore`/`refactor`/`test`/`ci`/`build`→no release.
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
A release PR that uses `GITHUB_TOKEN` does not start the required CI checks.
Use the stored release credential so its checks run. Do not bypass required
checks to merge a release.

## Consequences
- Releases are merge-only; no scripts, no towncrier, no hand-collation.
- The version has one source (`pyproject.toml`), rewritten by release-please;
  `__version__` reads it from metadata.
- Ordering for dependents still applies (publish a dependency before its
  consumer).
