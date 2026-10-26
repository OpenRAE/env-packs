# ADR 0041 — Distribute kits as package resources

- Status: Accepted
- Date: 2026-10-26
- Extends: [ADR 0036](0036-publish-first-party-content-with-env-packs.md)
- Supersedes: ADR 0036's Git-only source revision rule for installed first-party kits
- Coordination: OpenRAE/env-packs issue 415

## Context

The first-party kit collection exists in the repository but is absent from Python distributions.
Consumers therefore require a checkout to use a released kit collection.
The existing package already distributes example packs through Hatchling.
Each kit already has a RAES associated-artifact manifest and set digest.

## Decision

The wheel contains every canonical kit release under `raes_env_packs/resources/kits/`.
The source distribution contains the same bytes under `kits/`.
The build does not rewrite kit files or their manifests.
The existing release workflow remains the publication authority.
Public distribution fails if any release in the canonical collection is not
cleared for redistribution. The kit schema continues to support restricted
content for other catalogs; packaging policy does not narrow that schema.

`bundled_kit_source()` exposes the installed collection through the existing `KitSource` contract.
It resolves package data through the standard package-resource API and accepts
only a filesystem-backed installed resource tree. It does not extract resources
to temporary storage.
The source id is `openrae-env-packs`.
The source revision is `raes-env-packs==<installed-version>` for a normal filesystem installation.
Checkout sources retain explicit source revisions supplied by their callers.
The helper does not fall back to a checkout when installed resources are absent
or not filesystem-backed.

The package version selects the collection.
Each kit retains its independent id, version, and validated RAES set digest.
The source revision label does not prove authenticity or replace content validation.
Consumers admit the acquired distribution using their existing supply-chain policy.

## Consequences

A consumer can pin a kit collection through its Python dependency configuration.
Existing kit discovery, validation, and composition APIs consume the installed resources.
The package helper does not acquire files, grant trust, or execute kit content.
Distribution tests check redistribution eligibility, exact payload equality,
and every installed kit.
No additional publisher, checksum format, or catalog schema is required.
