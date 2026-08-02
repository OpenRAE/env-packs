# ADR 0037 — Compose verified pack distribution from existing authorities

- Status: Accepted
- Date: 2026-08-02
- Extends: [ADR 0004](0004-sbom-and-supply-chain.md),
  [ADR 0010](0010-consume-aces-reusable-asset-trust-policy.md),
  [ADR 0012](0012-pack-content-identity-and-trust-boundary.md),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md),
  [ADR 0028](0028-project-raes-artifact-satisfaction-into-publication.md),
  [ADR 0031](0031-compose-beginner-safe-pack-checks-from-existing-authorities.md),
  [ADR 0033](0033-resolve-pack-artifacts-through-one-bounded-open.md), and
  [ADR 0035](0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md)
- Amends: ADR 0028's allowance for a claim-free published release without a
  content-identity binding
- Coordination: OpenRAE/env-packs issue 191

## Context

Environment packs need install, update, lock, verify, and publish workflows over
OCI-backed releases. A release must expose an exact version, reproducible RAES
module resolution, a standards-backed component inventory, and verifiable
authenticity and provenance without turning transport metadata into a second
pack identity.

Most of the security-critical authorities already exist. RAES owns semantic
scenario identity, associated-artifact set identity and byte binding,
`raes.lock.json`, module resolution and signatures, registry trust policy, the
reusable-asset trust evidence classes, and image-build attestation facts. This
repository owns pack layout, safe pack reads, release views, publication
clearance, deterministic projections, diagnostics, and guarded local mutation.
OCI, CycloneDX, SPDX, in-toto, SLSA, and Sigstore provide the distribution and
evidence formats.

The repository's current release SBOM and attestations describe the
`raes-env-packs` Python distribution. They do not describe an individual
environment-pack release. Likewise, a RAES module signature authenticates one
resolved module and `Source.build.attestation` records facts about one image
build. Neither is a pack-release signature or pack SBOM.

## Decision

### Keep one authority per claim

Verified distribution composes the existing authorities without merging their
models:

| Claim | Authority |
| --- | --- |
| Scenario meaning and semantic identity | RAES SDL and snapshot contracts |
| Exact pack and release-view bytes | RAES `associated-artifact-manifest/v1` and its validator-derived set digest |
| Pack version and release-view projection | `pack.yaml` and the existing publication profile |
| RAES module graph, pins, and module signatures | RAES imports, `raes.lock.json`, module resolver, and `RegistryTrustPolicy` |
| Required integrity, authenticity, and provenance evidence classes | RAES reusable-asset trust policy |
| Pack content origin, redistribution, and safety clearance | Pack provenance ledger |
| Pack-release inventory | CycloneDX JSON by default; preserved upstream CycloneDX or SPDX as separately scoped evidence |
| Pack-release authenticity and build provenance | Standard OCI referrers and in-toto/SLSA/Sigstore-compatible attestations |
| OCI manifest and layer digests | OCI transport and repository addressing only |
| Individual image-build attestation facts | RAES `Source.build.attestation` |

The pack-release attestation subject is the validator-derived RAES associated-
artifact set digest for the released source pack. The attested provenance also
binds the pack id and version, semantic parent, source revision, builder/workflow
identity, exact `raes.lock.json` state, release-view set identities when present,
and the generated SBOM digest. An OCI manifest digest remains visible as the
transport address of the carrier; it is never renamed or promoted into pack
identity. A selector and every result identify whether a supplied digest is a
RAES set digest or an OCI manifest digest rather than guessing from the shared
`sha256:` spelling.

ADR 0028's optional binding remains valid for a local, non-published release
projection. Once a pack version is published through a repository, archive, or
OCI route, content identity is mandatory even when the publication profile
carries no artifact or capability claim. A claim-free release is not an
identity-free release.

The existing schema-backed `release.yaml` remains the single publication
carrier. Its next contract version may reference the external SBOM and the
standard release evidence needed to verify it, but a parallel pack-release
manifest or local canonical release digest is not introduced. Evidence whose
digest depends on the release subject, including the generated SBOM and release
attestation, remains outside the associated-artifact set it describes. An
upstream SBOM that a pack intentionally ships remains an ordinary associated
artifact with its own declared scope and provenance; it is not flattened into
the generated pack SBOM.

### Derive the SBOM, but require an accountable boundary

The author declares the pack-controlled component boundary through the existing
`publication_supply` authoring input. That input is extended rather than adding
an `sbom.yaml`, second lock, or component graph to `pack.yaml`. Release-time
work makes the input a closed, schema-backed pack contract through the existing
schema loader and relational-validation gate; unknown fields or an unmapped
shipped/pinned component fail instead of being ignored. Derivation reconciles
this declaration with all of the following incumbents:

- the exact associated-artifact inventory and release views;
- RAES `Source` and artifact identities recovered from validated SDL models;
- every `raes.lock.json` record and its exact module/artifact pins;
- materialized-kit provenance and the kit release's deterministic
  `component_inventory` inputs; and
- executable files, container images, OS or language packages, models, and
  other software that the pack distributes or content-addressably pins.

A shipped or pinned component cannot disappear behind an author-declared
boundary. Every such item must map to the finest authoritative identity,
version, digest, license, and provenance available. External, runtime-selected,
opaque, and unresolved items remain explicit scope states; the generator does
not invent their dependency closure. Independently scoped upstream SBOMs retain
their native documents, digests, subject identities, and provenance. The
release SBOM may reference them but does not merge them into a falsely complete
graph.

SBOM schema validation, subject/version agreement, digest verification, and
coverage reconciliation are publication and consumer gates. Vulnerability
results are separate time-sensitive evidence and never alter the SBOM or an
authenticity verdict. An SBOM proves inventory only; it is not a safety,
realizability, authenticity, or vulnerability-free claim.

### Use one proposal-first workflow and one result discipline

Install, update, lock, verify, and publish follow the proposal-first convention
already used by kit authoring. A silent library produces an immutable,
inspectable operation record; human, JSON, Hub, and MCP adapters render that
same record. The record exposes the requested selector, resolved version and
digests, repository route, module and lock changes, trust-policy result, SBOM
scope changes, compatibility changes, and classified effects.

Network access, billable work, credential use, signing, registry writes, and
local filesystem writes are explicit effects. No effect occurs merely because
a plan was requested. An interactive confirmation or explicit non-interactive
authorization covers the exact effect-bearing proposal; apply rechecks its
remote and local preconditions before acting. A remote selector is resolved to
immutable digests before a write proposal is confirmed. Mutable tags and
channels are discovery inputs, never installed identity.

Expected invalid input, policy refusal, conflict, missing evidence, or failed
verification uses the existing bounded `Diagnostic` convention and stable
`0`/`1`/`2`/`3` outcome meanings. Libraries do not print or log. A distribution
result carries evidence observations separately from blocking diagnostics and
keeps these states distinct:

- evidence absent or not published;
- verifier, registry, or policy authority unavailable;
- evidence present but not verified;
- verification attempted and failed; and
- verified under the named policy and subject.

These are workflow observations, not new RAES trust evidence classes. A single
boolean, `unknown`, or caught exception must not collapse them. Unexpected
programming defects remain tool failures rather than being relabeled as an
untrusted pack.

### Verify before promotion

Acquisition stages into a private bounded scratch area. OCI manifest/layer
digests are checked as transport integrity. Archive ingestion rejects absolute
or escaping paths, symlinks, hardlinks, special files, duplicate normalized
members, unsafe names, oversized members, member-count excesses, and excessive
compressed or expanded totals before materialization. Exported archives use
stable ordering, timestamps, ownership, and fixed safe modes so the repository
route and archive route reproduce the same associated-artifact bytes.

Before install or update is accepted, the same staged bytes pass all applicable
gates:

- shared consumer static validation through `validate_pack()`;
- full RAES associated-artifact inventory, checksum, size, parent, and set-digest
  binding through `validate_pack_content_manifest()`;
- release signature/attestation subject and signer-policy verification;
- release provenance binding for version, source, builder, set, lock, views, and
  SBOM;
- SBOM digest, schema, subject, and declared-boundary coverage;
- RAES lock drift and module resolution/signature verification through public
  RAES APIs under the caller-supplied trust policy; and
- publication-profile and compatibility checks relevant to the selected view.

No verified state is persisted before all required gates succeed. Promotion
uses the existing staged-directory transaction primitives with no-replace or
atomic exchange and a concurrent-change recheck. It never deletes the live
target before replacement, overlays files into it, follows links, preserves
unsafe source modes, or treats the current `release.py` scratch-directory
cleanup as an install transaction. A consumer-local receipt may retain the
resolved repository reference, RAES release identity, lock state, evidence
digests, and verification observations for drift detection and rollback
guidance; it is outside pack files and is not a portable pack schema or lock.

Publication applies the author-CI and release gates before any signing or
registry effect, then signs and pushes exactly the locally validated subject.
Failure to produce complete provenance, component coverage, safe content,
identity binding, SBOM binding, or a supported trust result refuses publication
rather than emitting a partial release.

### Keep credentials and policy outside portable content

Registry endpoints, mirrors, authentication, signing identities, private keys,
tokens, entitlement, tenant scope, and credential-store bindings are operator
configuration, not pack semantics or release evidence. Portable files and
plans may carry an opaque non-secret policy/profile reference, never secret
values, environment-variable names, signed URLs, userinfo, private registry
credentials, or secret-store coordinates.

Credentials are supplied through an OS credential helper or another protected,
non-argv channel. They never enter pack files, generated archives, OCI
annotations, process arguments, temporary release trees, receipts, logs,
diagnostics, stdout, or JSON output. External tool output is bounded and adapted
to stable codes; raw subprocess commands, URLs, headers, and exception prose are
not forwarded. A local CLI is not an authentication or authorization boundary.
Hub and MCP adapters authenticate the actor, authorize repository and target
scope, and emit their own redacted audit events before invoking the same silent
library contract.

### Preserve explicit extension seams

The seam between deterministic release/evidence derivation and distribution
transport accepts a selected OCI or repository/archive route plus bounded
resource and credential-provider policies. A new registry provider, mirror, or
archive destination extends that seam without changing pack schemas or release
identity. CycloneDX and SPDX readers are format adapters behind one scoped
component-evidence boundary; adding another standard does not alter the
canonical generated CycloneDX representation or flatten upstream scope.

The exact RAES pin and its public policy, model, resolver, lock, and validation
APIs remain the semantic/trust seam. If the pin cannot verify a locked module
graph under an explicitly supplied policy without ambient configuration or
private APIs, the feature is blocked on a public RAES seam. This repository does
not copy the resolver, parse RAES exception prose, monkeypatch the parser, or
weaken verification to proceed.

## Consequences

- Consumers can see repository identity, OCI transport identity, RAES content
  identity, module identities, and evidence digests without conflating them.
- Generated SBOMs and attestations remain non-recursive external evidence bound
  to the exact validated release.
- Install and update remain fail-closed, inspectable, and recoverable without
  turning a mutable live directory into the verification boundary.
- The Python-distribution release SBOM/signing workflow, pack-release evidence,
  module signatures, and image-build attestations stay independently verifiable.
- Contract tests must keep the publication carrier, associated-artifact binding,
  pack and kit component inputs, RAES lock/trust APIs, result envelope, archive
  safety, transaction behavior, dependency locks, and workflow permissions in
  agreement.

## Non-goals

This decision does not define RAES SDL, semantic or snapshot identity, a pack
digest, module descriptor or lock, trust evidence class, signature scheme,
cryptography, registry trust policy, image-build attestation, vulnerability
policy, runtime realization, backend lifecycle, billing, rankings, marketplace
authority, or Hub ownership of pack bytes.

It does not make an SBOM proof of safety or authenticity, flatten independently
scoped SBOMs, guess opaque transitive dependencies, put generated evidence into
the set it describes, accept mutable tags as installed identity, execute pack
code at a consumer boundary, store credentials in portable content, or make
rollback an automatic backend lifecycle operation.
