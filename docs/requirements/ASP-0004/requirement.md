---
id: ASP-0004
title: "Verified environment-pack distribution composed from existing authorities"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-08-02T15:04:15.845441Z
updated_at: 2026-08-02T18:57:49.510104Z
---

# ASP-0004 — Verified environment-pack distribution composed from existing authorities

## Statement

Environment-pack distribution tooling shall provide install, update, lock, verify, and publish workflows over OCI-backed pack releases while composing existing authorities without merging their models (ADR 0037). The validator-derived RAES associated-artifact set digest shall be the signed pack-release subject; OCI manifest and layer digests shall remain transport addresses only, and every selector and result shall distinguish a RAES set digest from an OCI manifest digest. Once a pack version is published through any route, content identity shall be mandatory even for a claim-free release. The existing schema-backed release.yaml shall remain the single publication carrier, extended to reference the external SBOM and release provenance rather than introducing a parallel manifest or second canonical release digest; generated SBOM and release attestation shall remain outside the associated-artifact set they describe. The author shall declare the pack-controlled component boundary through the extended publication_supply input, validated as a closed schema-backed contract; a shipped or pinned component that is unmapped or omitted shall fail publication, and external, runtime-selected, opaque, and unresolved components shall remain explicit scope states reconciled against the associated-artifact inventory, raes.lock.json records, materialized-kit component inventory recovered through the immutable kit source and revision, and RAES Source/artifact identities. A standards-backed CycloneDX JSON SBOM shall be generated per published pack version, bound to the exact validated release subject, recording its own digest, and shall neither flatten independently scoped upstream SBOMs nor claim safety, authenticity, realizability, or vulnerability-freedom. Install, update, lock, verify, and publish shall follow the proposal-first convention: a silent library shall produce an immutable inspectable operation record rendered by human, JSON, Hub, and MCP adapters, and no network, billable, credential, signing, registry-write, or local filesystem effect shall occur without explicit authorization of that exact proposal, with mutable tags and channels resolved to immutable digests before any write is confirmed. A distribution result shall keep evidence observations separate from blocking diagnostics and shall keep absent, authority-unavailable, present-but-unverified, failed, and verified states distinct rather than collapsing them into a boolean or exception. Before install or update is accepted, the same staged bytes shall pass shared consumer static validation, full associated-artifact byte binding, release signature/attestation and provenance verification, SBOM digest/schema/subject/coverage verification, RAES lock drift and module resolution/signature verification through public RAES APIs under a caller-supplied trust policy, and applicable publication/compatibility checks; no verified state shall be persisted before all required gates succeed, and promotion shall use staged-directory transactions with no-replace or atomic exchange without deleting or overlaying the live target. Registry endpoints, credentials, signing identities, and policy secrets shall stay outside portable pack content, plans, receipts, logs, and machine output; a local CLI shall not be an authentication or authorization boundary.

## Rationale

Issue #191 and ADR 0037 add environment-pack distribution and release policy that ships as executable enforcement (new schema-backed contracts, validation gates, CLIs, and a signing/publish workflow). Without an anchored requirement these gates would ship with no traceability, and the RAES-subordinate trust boundary they protect would have no contract of record. Extends the publication requirement ASP-0003 to the full verified-distribution boundary while keeping RAES the authority for identity, locks, module signatures, and trust evidence classes.

## Traceability

- IMPLEMENTS → CODE_FILE `src/raes_env_packs/component_boundary.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/sbom.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/release_provenance.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/verify.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/distribution.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/release.py`
- IMPLEMENTS → ADR `docs/decisions/adrs/0037-compose-verified-pack-distribution-from-existing-authorities.md`
- IMPLEMENTS → SPEC `src/raes_env_packs/resources/schemas/publication-supply.schema.yaml`
- IMPLEMENTS → CONFIG `.github/workflows/pack-distribution.yml`
- IMPLEMENTS → GITHUB_ISSUE `191`
- TESTS → TEST `tests/test_component_boundary.py`
- TESTS → TEST `tests/test_sbom.py`
- TESTS → TEST `tests/test_release_provenance.py`
- TESTS → TEST `tests/test_verify.py`
- TESTS → TEST `tests/test_distribution.py`
- TESTS → TEST `tests/test_distribution_archive_safety.py`
- TESTS → TEST `tests/test_release_publish.py`
- TESTS → TEST `tests/test_pack_distribution_workflow.py`
