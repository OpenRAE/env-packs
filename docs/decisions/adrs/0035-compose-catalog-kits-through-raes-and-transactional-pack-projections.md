# ADR 0035 — Compose catalog kits through RAES and transactional pack projections

- Status: Accepted
- Date: 2026-08-01
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0010](0010-consume-aces-reusable-asset-trust-policy.md),
  [ADR 0012](0012-pack-content-identity-and-trust-boundary.md),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md),
  [ADR 0032](0032-derive-catalog-projection-from-existing-authorities.md), and
  [ADR 0034](0034-compose-progressive-scaffolding-from-pack-and-raes-authorities.md)
- Coordination: OpenRAE/env-packs issue 190

## Context

Infrastructure kits let an author add a proven RAES SDL module and its supporting
pack files to an existing environment pack. The operation spans authorities that
must remain separate. RAES owns modules, parameters, exports, namespaces,
composition, resolution, trust, and `raes.lock.json`. This repository owns the
kit carrier, pack-local assets and metadata, diagnostics, and safe file mutation.
Catalog repositories own released kit content. Backends own realization.

ADR 0034 established one deterministic proposal and a staged, atomic create
transaction, but deliberately excluded updates to existing packs until explicit
ownership and conflict handling existed. Treating a kit as another wizard
capability would cross that boundary: capabilities are package-bundled pack
layers, while kits are independently released catalog content with RAES module
identity. Conversely, treating a kit as a plugin, second SDL, dependency lock,
or backend profile would duplicate an existing authority.

## Decision

### A kit is a catalog-owned authoring unit, not a runtime unit

This package defines a closed, independently versioned kit manifest and a
generated kit-catalog projection. The manifest carries only pack-domain facts:
stable kit identity and release version, author value and infrastructure
concern, pointers to the RAES module and kit-associated files, pack-local
materialization declarations, resource/cost estimates, non-RAES prerequisites,
limitations, licensing and redistribution facts, test declarations, and
component-inventory scope.

The manifest references, and inspection derives through public APIs in the exact
RAES pin, the module descriptor, parameters and defaults, exports, imports,
source and artifact identities, versions, digests, signatures, and trust facts.
It does not copy those fields into a local module-shaped object. RAES module
imports remain the dependency graph and `raes.lock.json` remains its only lock.
A kit-to-kit prerequisite may describe an authoring/package prerequisite absent
from RAES; it must not repeat a module import or establish a second resolution
rule.

Kit releases and the initial kit collection live in catalog repositories, not in
this package or its template. The kit-catalog document is a deterministic read
model over validated releases, using the stable source-id plus immutable-revision
boundary from ADR 0032. It has its own schema version; kits are not inserted into
the environment-pack catalog entry schema and no authored card or second
discovery model is introduced.

Component-inventory inputs identify every shipped or immutably pinned software
component at the finest authoritative granularity available and classify
external or unresolved scope explicitly. They reference RAES source/artifact
identities and may preserve an upstream CycloneDX or SPDX document as an
associated artifact. They do not define an SBOM schema, flatten an upstream
dependency graph, guess runtime-selected dependencies, or treat inventory as
trust, safety, or realization evidence.

### Every front end consumes one proposal and diagnostic contract

List, search, inspection, interactive CLI, machine CLI, Hub, and future MCP
adapters consume the same silent library records. Inspection projects RAES facts
from validated RAES models; renderers do not parse module YAML or infer exports,
topology, identities, or dependencies independently.

Add, update, replacement, and removal first produce one immutable proposal over
an immutably staged kit release and pack snapshot. The proposal contains
normalized kit selectors, namespace and parameter inputs, assumptions, exact
file operations, RAES import and lock changes, associated-artifact and component
inventory changes, ownership changes, and ordered diagnostics. Human preview,
machine output, mutation, and tests consume that proposal without recomputing
decisions. Preview is networkless, non-executing, and write-free, including no
RAES cache or lockfile write.

The target SDL composition root is explicit when a pack has more than one direct
SDL document; the tool never guesses from a filename or treats independent SDL
variants as fragments to concatenate. Diagnostics distinguish namespace,
exported-symbol, version, dependency, path, visibility, parameter, inventory,
and author-modification conflicts without exposing the conflicting values.

The existing `Diagnostic` shape and stable `0`/`1`/`2`/`3` CLI outcome convention
remain the error envelope. Expected validation and composition conflicts are
bounded diagnostics, invalid invocation remains distinct, and unexpected
package or RAES defects remain tool failures. Libraries do not log or print.
Front ends may add safe presentation and their own authenticated audit events,
but do not create another composition or mutation service.

If the exact RAES pin does not expose a public, side-effect-free operation needed
to inspect a descriptor, validate parameter values, compose imports, detect
export/namespace conflicts, or preview lock changes, that capability is blocked
on an upstream RAES contract. The implementation must not use RAES private
members, parse exception prose, edit SDL as generic YAML, or recreate a module
resolver or composer locally.

The non-executing authoring validation surface reuses the static core behind
`validate_pack()` with RAES file-backed composition enabled. The public consumer
`validate_pack()` remains import-denying and networkless, while `content_ci`
remains the trusted workflow that may execute pack-local validators and tests.
Kit authoring must not call the consumer API and misclassify a valid module
import as `sdl.imports-denied`, nor call the trusted CLI merely to obtain static
library validation.

### Materialization records provenance and explicit ownership, not a lock

A completed pack records a closed, versioned materialization ledger. Each record
names the exact kit identity/version, selected namespace, normalized non-secret
authoring inputs, and the explicit pack-relative files the materialization owns.
It may retain a baseline digest for each owned file solely to detect later author
modification. This ledger is inert authoring provenance and file ownership: it
does not participate in runtime resolution, replace `raes.lock.json`, restate the
RAES module descriptor, or establish artifact trust.

The ledger is optional, but when present it is part of the canonical static pack
contract. `validate_pack()`, author CI, and release validation all enforce its
closed schema, identity/namespace agreement, exact dependencies, member
existence, unique artifact ownership, and materialization-to-file ownership
joins. A later kit operation is not the first time a malformed ledger is found.

Ownership selects which files update or removal may consider; current filename
or byte equality never infers ownership. A baseline digest may identify an
author-modified owned file, but may not silently authorize overwriting or
deleting it. By default, update, replacement, and removal preserve such a file
and return an exact conflict. Any explicit resolution is represented in the
proposal and machine document. Replacement is one remove-plus-add composition
transaction and is permitted only when RAES validates the resulting imports and
references; kit tooling defines no parallel interface-compatibility taxonomy.

Files not owned by the selected materialization are never changed merely because
they resemble generated output. Shared files carry explicit multi-owner state or
the proposal fails; last-owner removal is what makes a shared file eligible for
deletion. Removing a materialization also removes only its RAES import and lock
records through RAES-owned operations. Dependency reachability, exported-symbol
use, visibility, and associated-artifact coverage are revalidated before any
commit.

### Existing packs are changed through one guarded transaction

The implementation factors and extends ADR 0034's proposal/staging machinery
rather than adding a kit-specific writer. It opens the existing pack through
`_pack_fs`, captures one bounded safe inventory, and stages a complete successor
beside the target on the same filesystem. Kit files are regular, verified
members; declarative materialization may only copy or render declared files from
normalized namespace and parameter values through a closed, context-aware
escaping policy. Parameters cannot select a renderer or destination path. There
are no executable hooks, arbitrary destination paths, ambient templates, shell
commands, or backend operations.

Every source and destination path is canonical and pack-relative. Symlinks,
hardlinks, special files, escapes, Unicode/case-fold collisions, duplicate YAML
keys, unexpected inventory changes, and resource-limit excesses fail closed.
The writer uses fixed safe modes and does not preserve source ownership, ACLs,
extended attributes, set-id bits, or world-writable permissions.

Catalog assets may target only the closed non-executable pack surfaces
`assets/briefing/`, `assets/content/`, `assets/kits/`, and `docs/kits/`.
Admission and materialization both enforce that boundary; a kit cannot create a
validator, test, hook, workflow, or other automatically executed pack member.

Before atomic replacement, the staged successor must pass the shared pack
contract, RAES authoring/composition validation, `raes.lock.json` validation,
kit validation, and exact associated-artifact coverage and byte binding. The
shared library never executes kit or pack code. Trusted catalog CI continues to
run `raes-pack-validate` for pack-local validators and tests under ADR 0013; that
execution is not imported into Hub or MCP mutation paths. A failed proposal,
render, resolution, validation, or concurrent-change check leaves the original
pack untouched. The commit swaps the complete validated successor into place
atomically; it does not overlay the live tree file by file. Callers still provide
an immutable pack snapshot or serialize edits: a directory API cannot make
arbitrary concurrent editor writes transactional.

If the commit-time exchange succeeds but its recovery exchange fails, the tool
does not delete the exchanged-out original. It raises a distinct recovery error
and preserves that tree in the reported private staging location for manual
recovery.

Associated-artifact set identity is recomputed for the complete successor under
ADR 0012. The materializer may project verified kit artifacts into the new
pack-local manifest through RAES models, but does not invent checksums,
canonicalization, parent identity, or descriptor semantics. The exact
materialization ledger and component-inventory inputs are ordinary pack files
and therefore part of the final inventory.

### Security and outer-system boundary

Kit discovery and preview accept staged, non-secret authoring inputs. Raw
credentials, tokens, private keys, secret values, signed URLs, secret-store
coordinates, environment-variable names, or unredacted configuration do not
belong in kit parameters, manifests, materialization records, argv, diagnostics,
logs, or machine output. Automation supplies bounded documents through stdin or
a contained file, not a JSON payload in process arguments. Access endpoints and
identity declarations are environment structure; credential brokering remains a
backend concern.

The local library owns no acquisition, authentication, authorization, tenancy,
database, cache, registry, Git operation, network policy, or audit log. Hub and
MCP adapters authenticate and authorize the actor, enforce tenant/path scope,
immutably stage admitted releases and packs, and record redacted audit events
before calling the same proposal/mutation contract. A CLI run is a trusted local
author workflow and does not claim those controls.

The deliberate extension seams are the closed kit-manifest version, the distinct
kit-catalog projection version, the RAES exact pin/public adapter, the bounded
materialization operation vocabulary, resource-limit policies, and the
materialization-ledger version. A future kit kind, source provider, Hub adapter,
or large-artifact carrier extends one of those seams; it does not add product or
backend vocabulary to the pack contract.

## Consequences

- Kit content remains independently releasable and inspectable without making
  this repository a catalog or runtime.
- Authors can review deterministic ordinary-file changes and retain safe
  ownership for later update, replacement, and removal.
- Exact pack inventory, RAES module resolution, trust, and semantic validation
  continue to have one authority each.
- The existing create-only writer remains valid; existing-pack mutation lands
  only through the stronger transaction defined here.
- Cross-contract tests must hold the kit schema, catalog projection, RAES pin,
  pack validator, content identity, release gate, CLI envelopes, and synthetic
  catalog fixtures in agreement. Actual kits are tested in their owning catalog
  repositories, never copied into this repository as fixtures.

## Non-goals

This decision does not define SDL semantics, a module descriptor, a dependency
lock, an SBOM or signing format, trust evidence, backend profiles, capability
verdicts, runtime plugins, realization, launch, readiness, rollback, teardown,
runtime evidence, credential brokering, agents, actions, injects, objectives,
success conditions, scenario narratives, or a marketplace.

It does not admit opaque generators, executable kit hooks, arbitrary template
engines, filename- or byte-inferred ownership, silent three-way merges, unbounded
module trees, automatic conversion of arbitrary content, or a GUI-only source of
truth. Downstream realization qualification begins only after stable kit releases
exist and is not part of pack materialization.
