# ADR 0034 — Compose progressive scaffolding from pack and RAES authorities

- Status: Accepted
- Date: 2026-07-31
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0011](0011-require-pinned-aces-sdl-validation.md),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md), and
  [ADR 0031](0031-compose-beginner-safe-pack-checks-from-existing-authorities.md)

## Context

The bundled template and `raes-new-pack` currently copy a broad, intentionally
incomplete authoring tree. A progressive wizard must instead select the smallest
pack shape that satisfies an author's stated goal, preview it, write it safely,
and immediately run the same static check used later. It also needs deterministic
machine-driven replay for Hub and MCP callers.

Those responsibilities cross two authority boundaries. This package owns pack
layout and pack-aware optional layers. RAES owns SDL construction, semantic
diagnostics, completion, and compilation. The exact `raes==2.0.0` pin exposes
public parsing and validation surfaces, but ADR 0031 records that it exposes no
public scenario compiler or compile-diagnostic API. A local substitute would be
a second SDL implementation.

## Decision

### Routes select pack capabilities, not scenario semantics

Starter routes are named, versioned presentation profiles over pack-owned file
and capability selection. They may choose pack structure, ask ordinary-language
questions, and supply safe UI defaults. They do not define schemas, participant
behaviour, objectives, assurance meaning, backend capability, or other RAES
semantics. Route labels are not persisted as semantic facts unless an owning
pack or RAES contract has a field for that fact. A route requiring offensive or
live-fire content must be explicit; all other routes remain domain-neutral.

SDL questions, choices, defaults, diagnostics, completion, and compilation are
adapted from public APIs or tools in the exact RAES pin. Structured upstream
identities are preserved and safely presented; exception prose is not parsed
into meaning. A missing public RAES authoring capability is an explicit blocked
capability and upstream coordination item, not permission to inspect private
modules, synthesize SDL fragments, or label parse validation as completion or
compilation.

Optional pack layers are a closed, declarative capability inventory whose
entries name their owning packaged resources and prerequisites. The inventory
is the extension seam for a future route or optional layer: adding one must not
require another copy loop or route-specific writer. It must not become a generic
template, plugin, hook, arbitrary path, or executable registry.

### One canonical proposal and replay contract

Interactive prompts and non-interactive input produce the same immutable
proposal: normalized inputs, explicit assumptions and unresolved answers,
selected capability identifiers, and a sorted manifest of intended
pack-relative files. Preview, human rendering, machine output, writing, and
tests consume that proposal; none independently recomputes route decisions.

The replay document is a versioned wizard-input DTO, not a pack schema or a
second representation of generated file contents. It contains no secrets,
credentials, arbitrary output paths, commands, environment values, or copied
RAES models. Unknown versions, keys, routes, capabilities, and invalid types
fail closed. Canonical normalization and ordering make equal inputs plus the
same package and RAES versions yield byte-identical proposals and generated
bytes. Machine-readable mode writes only its versioned document to stdout;
prompts and human progress never contaminate it.

Every question states the consequence of its answer. A safe default may select
only a semantics-neutral pack choice; otherwise the question offers an explicit
`not-sure` state. `not-sure` remains visible in the proposal and may block the
write when an owning contract requires a resolved value. It is never silently
converted into an assurance, compatibility, publication, or RAES semantic
claim.

### Preview is side-effect free; writing is one guarded transaction

Proposal construction and preview are networkless and read-only. They do not
create directories, run pack code, resolve remote SDL imports, probe a backend,
or consult ambient environment configuration. The target is derived from the
validated pack id beneath an explicitly resolved `environments/` root; replay
input cannot supply arbitrary member paths.

Writing renders first into a fresh private staging directory on the target
filesystem, using only canonical relative paths from the selected capability
inventory. Generated members are regular files with fixed safe permissions;
symlinks, hardlinks, special files, non-canonical names, case-fold collisions,
and escapes fail closed. The complete staged result passes public
`validate_pack()` before one atomic publication into an absent target. A failed
render or validation removes only the private staging tree and leaves no partial
pack.

An existing target is never overlaid or replaced by the create operation.
Replaying against one reports a deterministic conflict, even when its contents
appear generated; mutation requires a separately designed, explicit update
contract with ownership metadata and per-file conflict handling. Silent
overwrite, `copytree(..., dirs_exist_ok=True)`, delete-and-recreate, and inferred
ownership from matching bytes are forbidden.

Immediate validation uses `validate_pack()` and its canonical structured
diagnostics. The wizard may add presentation context, but does not copy pack,
schema, compatibility, publication, or SDL checks; does not introduce another
exception hierarchy; and does not turn expected validation findings into tool
failures. Unexpected defects and unavailable RAES tooling remain bounded tool
failures, distinct from invalid author input.

### Security and outer-system boundary

The wizard accepts authoring intent, not credentials. Secrets never belong in
prompts, saved input, argv, generated files, diagnostics, logs, or machine
output. Inputs supplied by automation should use stdin or a bounded file, not a
JSON blob in process argv. The library layer is silent and has no logging,
network, cache, database, Git, authentication, or authorization side effects.
Hub and MCP adapters retain responsibility for authentication, authorization,
tenant isolation, immutable staging, persistence, audit logging, and redaction;
the CLI does not claim those properties for them.

Input documents, strings, question counts, selected capabilities, rendered
member counts, member sizes, and diagnostics are bounded. Public error output
uses stable codes and safe field or pack-relative locations; it never echoes
input documents, authored secret-like values, absolute paths, environment
values, raw exceptions, upstream prose, or generated SDL bodies.

## Consequences

- The broad packaged template can remain documentation/reference material, but
  default generation is manifest-driven and copies only selected resources.
- All front ends share one proposal, deterministic replay format, writer, and
  validation result rather than separate interactive and automation workflows.
- Persona task tests cover the shared workflow through different inputs; persona
  names do not become route semantics or production conditionals.
- Delivering RAES-owned completion or compilation depends on a public upstream
  contract and a reviewed exact-pin advance. Until then the wizard must expose
  that capability as unavailable rather than approximating it.

## Non-goals

This decision does not define another SDL, diagnostic taxonomy, assurance model,
backend profile, compatibility probe, compiler, launcher, pack updater, generic
template engine, plugin system, GUI-only format, catalog persistence model, or
hundreds of route templates. It does not host packs, execute generated pack
code, resolve remote imports by default, acquire credentials, contact a backend,
or claim runtime readiness. Publication support selects and validates existing
pack and RAES contracts; it does not confer approval, provenance, trust, or
backend capability.
