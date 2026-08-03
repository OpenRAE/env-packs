---
id: ASP-0003
title: "Environment-pack publication profile bound to RAES artifact authority"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-07-28T17:15:31.596222Z
updated_at: 2026-07-28T17:15:37.252979Z
---

# ASP-0003 — Environment-pack publication profile bound to RAES artifact authority

## Statement

Release tooling shall emit and validate one immutable, schema-backed publication profile per environment-pack release, describing the release views it distributes. The profile shall consume the RAES artifact-requirement contract rather than redefine it: author posture, mechanism vocabulary, acquisition, timing, permitted routes, and trust references shall remain RAES-owned and be validated through the exactly pinned upstream models. Every published claim shall be joined to the authored requirement by compiled RAES address, and refused when it substitutes an exact artifact, exceeds an open requirement's authority, names a backend profile that does not resolve in the trusted RAES corpus, resolves ambiguously, or lacks a validated semantic-parent and associated-artifact-set binding. Immutable release identity shall be separate from mutable provider, location, and channel records; a published release shall not be overwritten with different bound identities; and credentials, tokens, signed-URL values, and entitlement shall never be publication content.

## Rationale

Environment Packs owns release packaging while RAES owns artifact-requirement semantics (ADR 0028, RAES ADR-098). Without an anchored requirement the publication gate would ship as an executable enforcement layer with no traceability, and the boundary it protects would have no contract of record.

## Traceability

- IMPLEMENTS → CODE_FILE `src/raes_env_packs/publication.py` (Publication profile authority validator)
- IMPLEMENTS → SPEC `src/raes_env_packs/resources/schemas/publication-profile.schema.yaml` (environment-pack-publication/v1 schema)
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/release.py` (Release emission, view binding and immutability enforcement)
- IMPLEMENTS → ADR `docs/decisions/adrs/0028-project-raes-artifact-satisfaction-into-publication.md` (ADR 0028 — Project RAES artifact satisfaction into pack publication)
- TESTS → TEST `tests/test_publication.py` (Publication profile authority and identity tests)
- TESTS → TEST `tests/test_release.py` (Release emission, immutability and staging-safety tests)
- IMPLEMENTS → GITHUB_ISSUE `141` (Define the environment-pack publication profile for artifact satisfaction)
- IMPLEMENTS → PULL_REQUEST `184` (feat: define the environment-pack publication profile for artifact satisfaction)
