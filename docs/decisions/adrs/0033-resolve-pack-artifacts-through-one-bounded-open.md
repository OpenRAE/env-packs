# ADR 0033 — Resolve pack artifacts through one bounded open

- Status: Accepted
- Date: 2026-07-31
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0012](0012-pack-content-identity-and-trust-boundary.md),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md), and
  [ADR 0031](0031-compose-beginner-safe-pack-checks-from-existing-authorities.md)
- Coordination: OpenRAE/env-packs issue 208

## Context

Consumers can validate a pack and its RAES associated-artifact manifest, but
cannot safely turn one opaque associated-artifact id into bytes. The pack-local
URI, inventory, and descriptor-reader machinery is private. Reimplementing it
downstream would create another pack contract; validating a path and reopening
the target would also reintroduce the mutable-directory race that the
descriptor-anchored filesystem boundary exists to prevent.

RAES already owns the associated-artifact descriptor, checksum and set models,
the byte-binding validator, and `ArtifactIdentity`. This repository owns only
the pack-local resolution and the projection from a declared pack artifact into
that RAES identity.

## Decision

The package exposes one silent, networkless consumer operation that accepts an
immutably staged pack root and either an opaque artifact id or the upstream
associated-artifact descriptor. A supplied descriptor must equal the manifest
entry selected by its id; it is not an alternative source of URI, media type,
size, or checksum claims.

The operation does not trust a prior path-based validation result as a
capability. It opens one pack root descriptor, loads the bounded manifest,
checks the pack/manifest identity and exact safe inventory, and performs the
existing RAES parent, set, size, checksum, and byte-binding validation in that
same lifetime. The selected regular file is opened exactly once. Its bounded
contents are copied into `bytes`; the RAES validator consumes a reader over
those same bytes while other declared artifacts use the existing lazy
descriptor readers. The inventory is checked again before return. No file
descriptor or reader over mutable pack storage escapes the operation.

Direct SDL parent candidates are loaded from bounded descriptor-anchored bytes.
The upstream validator's structured parent/set verdict is used without payload
readers to select exactly one matching parent; no match or an ambiguous match
fails closed. Full payload binding then runs once for that parent. The resolver
must not multiply the total byte budget or reopen sibling payloads by running a
complete byte-binding pass for every candidate.

Callers still run `validate_pack()` at ingest. That gate and artifact resolution
remain different checks: static pack validity does not prove associated-
artifact byte identity, and artifact resolution does not replace provenance,
compatibility, or SDL validation.

The successful result is an immutable record containing the selected bytes and
an upstream `raes.artifact_requirements.ArtifactIdentity`. The identity is
constructed through the pinned upstream model, with this exact projection:

| `ArtifactIdentity` field | Authority |
| --- | --- |
| `artifact_id` | associated-artifact descriptor `artifact_id` |
| `version` | validated string `pack.yaml.version`, equal to the manifest version |
| `media_type` | associated-artifact descriptor `media_type` |
| `digest` | `"sha256:" + descriptor.checksum.value` after successful byte binding |

The projection adds no local identity schema or version rule. A descriptor that
cannot construct the upstream identity fails closed.

Pack metadata, member count, SDL parsing and diagnostic bounds reuse
`PackValidationLimits`; associated-artifact count, selected-byte and total-byte
budgets reuse upstream `AssociatedArtifactValidationLimits`. The two policy
domains remain distinct public parameters rather than overloading an unrelated
limit. Parent SDL bytes are read through `_pack_fs` and the consumer-safe public
RAES parser; the resolver does not use a pathname-based parser or enable SDL
imports.

Expected foreign-input failures reuse `PackDigestError` and the package's
bounded structured diagnostic convention; no resolver-specific exception
hierarchy is added. Upstream diagnostic codes are adapted without exposing raw
upstream messages, authored ids, artifact URIs, restricted paths, absolute
paths, file bodies, environment values, or exception representations.
Unexpected package defects continue to raise normally. The library does not
log.

The internal verified-open boundary keeps selection and identity projection
separate from the final byte collector. A future explicitly designed
large-artifact carrier may reuse that boundary, but it must preserve
verification-before-use and may not expose an unverified stream or a live pack
descriptor. The initial public contract returns `bytes`.

## Consequences

- Consumers use one pack-owned URI and filesystem implementation and one
  RAES-owned descriptor, validator, diagnostic code set, and identity model.
- Returned bytes remain stable even if mutable source storage changes later;
  callers still must supply immutable staging because a directory operation
  cannot provide snapshot isolation.
- Full set validation may read other declared payloads. “Single-open” means the
  selected payload is not reopened between verification and return, not that
  unvalidated manifest siblings are skipped.
- The exact RAES pin remains the compatibility seam. A pin advance requires
  behavior tests for descriptor and `ArtifactIdentity` projection compatibility.

## Non-goals

This decision does not add acquisition, URL fetching, ambient-path fallback,
archives, a registry, catalog persistence, caching, authentication,
authorization, entitlement, signing, trust admission, decryption, execution,
materialization, range placement, telemetry, or RAES scenario semantics. It
does not make mutable storage atomic, expose a general pack filesystem API, or
publish a long-lived validated-pack/file-descriptor capability.
