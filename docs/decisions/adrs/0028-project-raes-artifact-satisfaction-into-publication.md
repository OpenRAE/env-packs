# ADR 0028 — Project RAES artifact satisfaction into pack publication

- Status: Accepted
- Date: 2026-07-28
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0010](0010-consume-aces-reusable-asset-trust-policy.md),
  [ADR 0012](0012-pack-content-identity-and-trust-boundary.md), and
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md)
- Upstream contracts: RAES issue 920, `artifact-requirement-v1`,
  `backend-manifest-v2`, `backend-profile/v1`, and
  `associated-artifact-manifest-v1`

## Context

The existing release tool derives participant, operator, oracle/restricted, and
commercial trees from pack-owned visibility boundaries and writes an
unvalidated `release.yaml` summary. It does not yet describe an immutable pack
release, bind each distributed view to exact bytes, or express which
RAES-authored artifact requirements the release can help a backend satisfy.

RAES 2.0.0 publishes the authority this feature must consume. An authored
`ArtifactRequirement` distinguishes exact, constrained, and open requirements;
immutable candidates, locked inputs, and permitted materialization
specifications retain different authority; permitted routes keep acquisition
transport and timing separate from the satisfaction mechanism. Backend
manifests declare mechanism capabilities, and RAES evaluates those capabilities
with trusted availability facts. Associated-artifact manifests bind a semantic
parent and an exact payload set. The realized
`ArtifactSatisfactionDisclosureModel` is a backend/run fact, not release
metadata.

Copying those shapes or reducing them to a local pull-or-bake choice would make
the publication layer a competing semantic authority. Folding mutable channels,
provider locations, or authenticated URLs into release identity would make an
unchanged release acquire a new identity when distribution operations change.

## Decision

### One publication carrier, composed from existing authorities

The existing `release.yaml` emission becomes the single immutable publication
profile carrier. It is advanced to a named, schema-backed pack-domain contract
with a RAES-style `$id` and `schema_version`; the integer
`metadata_schema_version` shape is not silently assigned the new meaning. A
parallel release-summary or second publication manifest is not introduced.

The publication profile composes, rather than merges, the existing authorities:

| Concern | Authority |
| --- | --- |
| Artifact requirement, explicitness, candidates, locked inputs, permitted specifications and routes | RAES SDL and `artifact-requirement-v1` |
| Backend artifact mechanisms and route support | RAES `backend-manifest-v2` and versioned backend profiles |
| Semantic parent and exact payload-set byte binding | RAES `associated-artifact-manifest-v1` |
| Integrity, authenticity, admission and trust evidence | RAES reusable-asset trust contracts |
| Redistribution rights and publication clearance | The pack provenance ledger |
| Participant/operator/restricted/commercial exposure | The compatibility manifest and boundary-split release views |
| Which permitted assets or specifications are supplied with this release, plus their non-secret availability | The publication profile |

The compatibility manifest remains an authored compatibility projection. The
publication profile is a derived release fact and does not grow new runtime,
trust, requirement, or preparation semantics.

Derivation cannot invent which permitted assets an author chose to ship, so the
supply rows themselves are authored through an optional `pack.yaml` pointer,
`publication_supply:`, carrying `publications`, `capability_claims`,
`availability`, and `channels`. That authored input is a compatibility-manifest
style projection, not a second emitted carrier: view structure, identity
binding, and contract facts are still derived, and `release.yaml` remains the one
publication document. An absent pointer means the release publishes nothing,
which is a valid release.

Pack content identity remains opt-in under ADR 0012, while a published claim
requires the binding this decision mandates. Both hold together: a release that
makes no publication or capability claim has nothing to verify and needs no
semantic-parent or associated-artifact-set binding, and any claim requires one.
A release view therefore carries its identity blocks only when the pack has
opted into content identity, and a claim without that binding is refused.

### Immutable release and view identity

One release is identified by its pack id and version together with:

- the canonical RAES semantic parent reference and digest;
- the validated source-pack associated-artifact manifest identity and set
  digest; and
- the associated-artifact manifest identity and set digest of every non-empty
  release view.

This tuple is represented directly; this repository does not define another
canonicalization or release digest. Reusing a pack id and version for different
parent or set identities is an error, not a replacement release. A builder must
not delete and overwrite an existing immutable release with different bytes;
an idempotent rebuild is acceptable only when all bound identities agree.

The stable publication views are `participant`, `operator`, `restricted`, and
`commercial`. The existing compatibility input label `oracle_only` maps to the
`restricted` publication view and gains no scenario or validation-oracle
meaning. `BOUNDARY_TIERS` remains the one mapping seam from authored boundary
groups to publication views; view selection is not inferred from paths or
provider names.

Every non-empty view has its own RAES associated-artifact manifest because set
identity does not inherit from the source pack or another view. The publication
profile and manifest carrier are outside the set they describe, avoiding
self-reference. An empty view is represented as empty and must not invent a
placeholder artifact to satisfy the RAES manifest's non-empty payload rule.

### Release supply never changes RAES author authority

Publication rows reference compiled RAES requirement addresses and the
corresponding authored ids; they do not copy or reinterpret the requirement.
Relational validation joins every release claim back to the parsed and compiled
RAES scenario:

- an exact requirement can reference only its exact immutable artifact;
- a constrained requirement can advertise zero or more of its declared
  candidates without implying that the advertised set is exhaustive;
- a locked input remains a locked input and retains its associated-artifact and
  trust references;
- a materialization specification is publishable only when the requirement
  explicitly permits that exact id, profile, digest, and locked-input join; and
- an open requirement may reference an applicable backend capability without a
  published artifact, candidate, or materialization specification.

Absence of a supplied artifact or specification is not an unsatisfied,
exhaustive-alternatives, or pull-at-runtime claim. Acquisition transport and
preparation timing remain the RAES route values authored on the requirement;
the publication layer neither guesses nor defaults them.

A compatibility claim against a backend profile proves only what that
versioned profile contract says. A satisfaction claim additionally requires the
concrete, validated backend mechanism declaration (`ArtifactMechanismCapability`)
and the RAES availability facts carried by `ArtifactRequirementAvailability` /
`ArtifactAvailabilityContext`. A bare profile name is not evidence of mechanism
support. The publication profile never emits a realized
`ArtifactSatisfactionDisclosureModel`; only a selected backend at realization
time can produce that disclosure.

A capability claim is therefore bound to a backend profile that resolves in the
trusted RAES profile corpus of the exact pin and requires `backend-manifest-v2`,
the governed contract under which a backend declares its artifact mechanisms. An
unresolvable profile name is refused rather than published: without that binding
a pack author who cannot modify a trusted profile could still name one and
attach a self-constructed capability, and a consumer resolving by profile would
treat an unsupported mechanism as authorized. The concrete per-backend manifest
is a deployment fact absent at release time, so this establishes compatibility
against a real profile contract, never realized satisfaction.

Release identity uses the semantic parent reference **and** its digest. A claim
is refused when the digest is absent, because a parent id alone would let the
same id carry changed semantics without changing release identity.

Compiled requirement addresses must resolve unambiguously. Two SDL documents can
carry the same owner trail; such an address is marked ambiguous and refused
rather than resolved against whichever scenario was parsed last.

### Distribution, origin access, and runtime exposure stay orthogonal

The provenance ledger's redistribution classification, an origin's acquisition
access policy, and a release view's runtime exposure are three independent
axes. No validator infers one from another. Public and authenticated/private
origins use the same availability record shape. Authentication and entitlement
are expressed, at most, by non-secret policy references; credentials, tokens,
signed-URL query values, secret-store coordinates, and environment-variable
names are not pack or publication content.

Channels and provider/location availability are mutable resolution records that
refer to the complete immutable release identity. They are outside every
release-view artifact set and do not contribute to scenario, pack-release, or
view identity. The repository may define and validate their record shape, but
does not define storage, update, credential, entitlement, discovery, or
registry protocols.

### Existing validation and security boundaries remain authoritative

The shared `validate_pack()` / `PackValidationLimits` machinery remains the one
static pack-contract authority. Every standalone release entry point requires
the same successful author-static result used by content CI; it must not assume
another command already ran. The author variant retains its deliberate
file-backed RAES import policy rather than forcing the consumer API's
imports-denied policy onto trusted authoring.

The emitted publication profile is checked through one validation helper that
reuses `validation.py`'s packaged-schema loader, strict bounded YAML handling,
diagnostic collector, and relational-check pattern. The emitter and any future
consumer adapter call that helper; neither re-parses pack, provenance,
compatibility, or SDL contracts. RAES-owned values are parsed and checked through public APIs from the exact
`raes` pin:

- `raes.parse_sdl_file()` / `raes.parse_sdl()` for the authored scenario, which
  is also where authored `Source.artifact_requirement` values are recovered;
- `raes_contracts.addressing.render_compiled_address()` and
  `require_compiled_address()` for compiled requirement addresses;
- the models, invariant validators
  (`validate_artifact_requirement_invariants()`,
  `artifact_requirement_invariant_violations()`) and availability carriers in
  `raes_contracts.artifact_requirements`;
- `raes_contracts.backend_profiles.load_backend_profile()` /
  `BackendProfileModel` / `BACKEND_SUPPORTED_CONTRACT_IDS`; and
- `raes_contracts.associated_artifacts` with
  `AssociatedArtifactValidationLimits`.

The pinned release publishes no scenario runtime-model compiler and no
artifact-requirement planner-diagnostics entry point, so this repository binds
release claims to the authored requirement and the public availability
carriers rather than re-deriving planner admission. No RAES schema, enum,
address grammar, mechanism list, trust model, exception hierarchy, or semantic
validator is copied into this package; advancing the exact pin is the seam that
adopts any future upstream compiler or diagnostics surface.

All pack-controlled reads and view copies reuse `_pack_fs.py`'s
descriptor-anchored, no-follow, bounded inventory and member access. Passing a
path-based validation gate and reopening it with `open()`/`shutil.copy2()` is
not sufficient across a mutable-directory race. Symlinks, hardlinks, special
files, non-canonical names, duplicate YAML keys, invalid UTF-8, member/byte
budget violations, and inventory changes fail closed. Generated views use
fixed safe file modes rather than inheriting ownership, ACLs, extended
attributes, set-id bits, or other source metadata.

Associated artifacts reuse `AssociatedArtifactValidationLimits`. Publication
metadata uses the existing YAML structural and diagnostic bounds. The release
tool remains static and local: it does not fetch availability locations,
resolve channels, contact a backend, execute a materialization specification,
read environment configuration, or add caches or databases.

The library surface remains silent. Expected pack/profile defects join the
existing bounded `ValidationResult` or release failure adapter; RAES set-binding
failures retain `PackDigestError`. Diagnostics expose stable codes and bounded
field or pack-relative locations, never artifact names supplied as secrets,
restricted paths, raw upstream exceptions, URI query values, credentials,
environment values, or file bodies. CLI/subprocess arguments remain argv-based,
and no credential or publication document is placed in process arguments.

Before promotion, the staged views, their RAES manifests, the emitted
publication profile, boundary disjointness, and the participant leak scan all
describe the same bytes. Promotion retains the existing scratch-directory
cleanup discipline but treats an already-published release as immutable.

## Consequences

- `release.yaml` becomes a consumer contract rather than an informational
  summary, so its schema, generated examples, validator, release emitter,
  contract prose, and tests must move together.
- A publication cannot be emitted for a pack that lacks a validated RAES
  semantic-parent and associated-artifact-set binding.
- Each distributed view is independently verifiable; the source-pack set digest
  is not incorrectly reused as the participant, operator, restricted, or
  commercial view digest.
- Provider kinds and locations remain data, not a closed product enum. A future
  provider adds an availability row; a future view adds one deliberate
  boundary-to-view mapping. Neither requires a new artifact-requirement model.
- The exact RAES dependency pin is the compatibility seam while these upstream
  contracts remain draft. Advancing it requires contract and behavior
  compatibility tests, not a vendored compatibility schema.

## Non-goals

This decision does not operate a registry or catalog, publish or acquire bytes,
select a backend, execute a build or materialization specification, define
preparation timing, mint credentials or entitlements, expose private content,
or persist mutable channel state. It does not add product-specific vocabulary,
host an environment pack, define a generic registry/build protocol, or alter
RAES SDL, artifact requirement, realization, trust, associated-artifact, or
backend semantics.
