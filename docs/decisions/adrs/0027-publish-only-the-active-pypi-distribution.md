# ADR 0027 — Publish only the active PyPI distribution

- Status: Accepted
- Date: 2026-07-28
- Amends: [ADR 0023](0023-recover-interrupted-signed-releases.md)
- Amends: [ADR 0026](0026-separate-historical-source-from-release-tooling.md)

## Context

The historical `v2.0.2` recovery reached PyPI after its signed tag, build,
provenance attestation, SBOM, and GitHub Release succeeded. PyPI rejected the
artifact because its metadata names the pre-rename distribution while the
repository's trusted publisher is correctly scoped to `raes-env-packs`.

The failed upload prevented the workflow from attaching the already-built
artifacts, completing the merged release PR's label transition, and resuming
release-please. Expanding or replacing the PyPI trusted-publisher binding would
contradict the repository's hard distribution rename.

## Decision

The release workflow parses the distribution name from the checked-out
`pyproject.toml` before creating or reusing the GitHub Release:

- `raes-env-packs` is authorized for PyPI trusted publishing.
- The exact historical `v2.0.2` tag at commit
  `45f39a930625c9de4c44017e8966d00b82f65052` skips PyPI, then continues through
  GitHub asset attachment and the release-please state transition.
- Every other distribution name fails closed before either publication
  destination changes.

The PyPI action consumes the policy step's explicit output rather than
reimplementing the tag exception. Its existing `skip-existing` behavior remains
in place for safe reruns of active-distribution releases.

## Consequences

- The PyPI project identity remains exclusively `raes-env-packs`.
- The retired distribution remains frozen at its last successfully published
  version; recovery does not create another PyPI release under that name.
- The signed historical GitHub Release can still retain its attested wheel,
  sdist, and SBOM and can unblock release-please.
- Future renames or recovery exceptions require an explicit policy and ADR
  change instead of silently publishing whatever name appears in package
  metadata.
