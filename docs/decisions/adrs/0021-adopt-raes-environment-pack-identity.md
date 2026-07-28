# ADR 0021 — Adopt the RAES environment-pack identity as a hard cut

- Status: Accepted
- Date: 2026-07-28
- Supersedes: the identity-specific portions of
  [ADR 0002](0002-distribute-as-installable-package.md),
  [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0011](0011-require-pinned-aces-sdl-validation.md), and
  [ADR 0014](0014-consume-aces-concept-authority.md)

## Context

The repository now lives at `RAESystem/env-packs`, and upstream ACES has become
the Reproducible Agentic Environments System (RAES). The published
`raes==1.1.0` distribution is a hard package/import cut: this repository cannot
move to it while retaining imports from `aces_sdl` or `aces_contracts`.

Three local identities deliberately differ:

| Surface | Current identity |
|---|---|
| GitHub repository | `RAESystem/env-packs` |
| PyPI distribution | `raes-env-packs` |
| Python import package | `raes_env_packs` |

The vocabulary cut is narrower than a text replacement. This repository owns
environment **packs**, but RAES still owns the SDL `Scenario` concept. Pack-owned
contract identifiers need the environment-pack name; RAES-owned scenario,
schema, trust, and resolver identifiers must match the exactly pinned RAES
release even when a retained identifier contains historical ACES spelling.

The retired `aces-scenario-packs` distribution has published consumers, and the
SonarCloud project still has an external identity independent of the GitHub
repository transfer. Both need explicit treatment rather than inference from
the new repository slug.

## Decision

### One current package identity

The maintained package has one distribution, import tree, and CLI family:
`raes-env-packs`, `raes_env_packs`, and `raes-pack-*` / `raes-new-pack`.
There is no compatibility import package, fallback import, dual-read path,
console-script alias, or shim distribution.

The old PyPI distribution receives one final metadata-only patch release whose
long description points to `raes-env-packs` and the migration guidance. It does
not depend on the new distribution, install placeholder modules, or change
runtime behavior. It is frozen after that release; historical artifacts remain
available. The maintained distribution then continues the same semantic
lineage as a breaking major release. Release Please remains the only version and
changelog writer.

The final old-name publication and the new-name publication both use the
existing protected `pypi` environment and short-lived OIDC trusted publishing.
The `raes-env-packs` PyPI project already has its trusted-publisher binding for
`RAESystem/env-packs`, `release-please.yml`, and environment `pypi`; no API
token or second publishing workflow is introduced.

### Pack vocabulary and RAES vocabulary stay separate

Pack-owned names use “environment pack.” This includes current prose, the
authoring/catalog root (`environments/<pack-id>/`), documentation names, schema
and contract type identifiers, the pack-local associated-artifact locator
scheme, template source labels, and author-facing diagnostics. Generic public
API names such as `PackValidationLimits`, `ValidationResult`, and
`PackDigestError` remain valid; “pack” is not the retired concept.

Changing a published pack-owned identifier mints a new contract identity rather
than silently changing the old one:

- provenance advances from `scenario-pack-provenance/v2` to
  `environment-pack-provenance/v3`;
- compatibility advances from `scenario-pack-compatibility/v1` to
  `environment-pack-compatibility/v2`;
- the environment-pack layout contract advances from content version 3 to 4;
- `aces-scenario-pack:/` is replaced by the pack-owned
  `raes-environment-pack:/` locator scheme.

The schema `$id` and `schema_version` stay paired under the repository's existing
schema-convention guard. Old instances are not accepted through aliases or
rewritten in place.

RAES-owned scenario names do **not** change. `sdl/`, `*.sdl.yaml`, `Scenario`,
scenario scopes and parent references, `reusable_scenario`, parser return
objects, and prose that actually describes authored SDL scenario meaning stay
scenario-named. The exactly pinned `raes==1.1.0` corpus is also authoritative for
its contract identifiers. In particular, that release still publishes
`https://aces.dev/schemas/`, `aces.lock.json`, and
`sdl/.aces/module-cache`; this repository retains those spellings until a
separately reviewed RAES pin advances the owning upstream contract. Current
upstream-main or anticipated RAES 2.0 spellings must not be mixed into a
RAES 1.1.0 integration.

All public upstream imports move together. The SDL parser symbols come from
`raes`, and associated-artifact, diagnostic, model, corpus, and
controlled-vocabulary APIs come from `raes_contracts`. No private upstream
package path, copied schema, second SDL parser, or parallel exception hierarchy
is introduced.

### Existing validation and security boundaries remain authoritative

The rename does not create a new validation layer. `validate_pack()` remains the
one shared static pack-contract authority; author CI delegates its overlapping
checks to it. Pack-owned YAML continues through the packaged schemas and strict,
bounded loader, while SDL and RAES-governed concepts continue through the
public APIs of the exact `raes` pin.

Descriptor-anchored, no-follow filesystem reads in `_pack_fs.py`, bounded
`ValidationResult` diagnostics, structured `PackDigestError` diagnostics,
author-CI subprocess budgets, participant-token redaction, and release
containment/leak checks retain their existing roles. The consumer API remains
silent, import resolution remains denied there, and only the trusted author-CI
surface may execute pack-local code. The rename adds no authentication,
environment binding, network resolution, cache, database, or other persistence
surface.

The issue-skeleton helper keeps dry-run as its default and keeps GitHub payloads
on stdin to `gh`; changing its default repository does not move credentials
into argv or output. Release and CI retain read-only top-level workflow
permissions, SHA-pinned actions, bounded job-level writes, Sigstore identity
verification, build provenance, the SBOM, and PyPI OIDC.

### External project identities are explicit inputs

The Git remote and Sigstore certificate identity already use
`RAESystem/env-packs`. OpenSSF Scorecard derives the repository from the GitHub
workflow context, so only its badge/viewer links carry the repository slug.

SonarCloud stays on its existing externally bound identity: organization
`brad-edwards` and project key `Brad-Edwards_aces-scenario-packs`.
`sonar-project.properties` and `.ground-control.yaml` must agree with that exact
key. The repository and distribution rename does not imply that the externally
managed SonarCloud key can change.

Ground Control is a separately managed application whose project identifier
remains `aces-scenario-packs`; this rename does not migrate that application's
content. Requirement UIDs and `short_code: ASP` are likewise stable. Repository
paths, workflow references, and architecture vocabulary that identify source
locations or environment packs do move.

## Consequences

- The package/import/CLI rename is intentionally breaking and atomic. A wheel
  contains only `raes_env_packs`; keeping both source trees would create two
  resource and validation authorities.
- The `raes` dependency remains one exact pin in `pyproject.toml`, and
  `requirements/runtime.txt` remains its hash-locked generated closure. Exact
  dependency matching must distinguish `raes` from `raes-env-packs` and other
  `raes_*` packages.
- Clean-environment verification must exercise wheel contents, metadata,
  public imports, package resources, and every new console entry point. Unit
  tests and the content/release gates remain the compatibility corpus for the
  RAES pin.
- Historical changelog entries, immutable pre-cut ADRs, old tag-verification
  identities, and the deliberate PyPI retirement note remain historical
  records. The automated old-name guard exempts only those enumerated records
  and exact externally bound identity lines.
- The removed Dependabot auto-merge workflow is not recreated. ADR 0020 still
  requires a human to merge every dependency update; the relevant invariant is
  the exact `raes` pin plus the no-auto-merge workflow guard, not a renamed
  auto-merge substring check.

## Non-goals

This decision does not rename RAES SDL scenario concepts, alter SDL semantics,
adopt RAES 2.0 contract identities, add backward-compatible readers, migrate
downstream catalog content in place, rewrite persisted manifests, delete old
PyPI artifacts, migrate or rename the Ground Control project, change Ground
Control UIDs, move or rename the SonarCloud project, or change authentication,
authorization, acquisition, storage, runtime, or deployment behavior.
