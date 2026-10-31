# ADR 0045 — Version packs with the package

- Status: Accepted
- Date: 2026-10-31
- Extends: [ADR 0008](0008-adopt-release-please.md)
- Coordination: OpenRAE/env-packs issue 536

## Context

Each pack under `packs/` had its own version, and authors bumped it by hand.
These packs ship only in the `raes-env-packs` distribution.
The package version already identifies their content, so the pack versions duplicated it.

A pack writes its version in four places: `pack.yaml`, `pack.compatibility.yaml`,
the associated-artifact `manifest_version`, and each pack-local exact-artifact reference in its SDL.
RAES requires the manifest and artifact versions.
The pack checksums its own files, so a version change also changes its digests.
Release Please can replace version text, but it cannot recompute checksums.

## Decision

- Every pack under `packs/` carries the `[project].version` from `pyproject.toml`.
- `tools/sync_pack_versions.py` writes that version into the four places.
  It then refreshes the pack digests with `tools/refresh_pack_sdl_binding.py`.
- The `sync-pack-versions` job in `.github/workflows/release-please.yml` runs the tool on the open release PR.
  It runs after each Release Please update and pushes one `chore:` commit to the release PR branch.
- A repository test requires every pack to carry the package version.
- Do not edit a pack version by hand.
- The pack format keeps its required `version` field.
  A pack outside this repository keeps its own version.

## Consequences

- One version identifies the package and every pack in it.
- Every release changes each pack's version and digests.
- The release PR contains one commit from `github-actions[bot]`.
  Release Please replaces its branch on each update, and the job then adds the commit again.
- The job holds only `contents: write` and `pull-requests: read`. It writes only to the release PR branch.
- No new release workflow, publisher, or identity format is added.
