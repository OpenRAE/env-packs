# ADR 0031 — Compose beginner-safe pack checks from existing authorities

- Status: Accepted
- Date: 2026-07-29
- Extends: [ADR 0009](0009-scenario-packs-subordinate-to-aces.md),
  [ADR 0010](0010-consume-aces-reusable-asset-trust-policy.md),
  [ADR 0011](0011-require-pinned-aces-sdl-validation.md),
  [ADR 0012](0012-pack-content-identity-and-trust-boundary.md),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md), and
  [ADR 0028](0028-project-raes-artifact-satisfaction-into-publication.md)

## Context

The public `validate_pack()` boundary safely checks one untrusted pack, while
`raes-pack-validate` is an author-CI workflow that may resolve SDL imports and
execute pack-local validators and tests. The public result currently exposes
compact strings and the author CLI maintains several additional pack-owned
joins. Content identity, publication claims, RAES backend profiles, and
pack-release checks have their own validators and diagnostic shapes.

A consumer-oriented command needs to explain structural, SDL, compatibility,
and trust/provenance failures without creating another pack contract, flattening
those ownership domains into one meaning, or making the author-CI executable
surface look safe for foreign input. Human and JSON output also need to remain
the same result rather than two independently maintained renderings.

The exactly pinned `raes==2.0.0` exposes public SDL parsing and semantic
diagnostics, backend-profile loading, associated-artifact and trust contracts,
and `raes sdl verify-imports`. It does not expose a public scenario compiler or a
compile-diagnostics command. Reconstructing compilation locally would violate
the repository boundary.

## Decision

### One static authority, multiple adapters

`validate_pack()` remains the single static pack-contract authority. A
consumer-oriented CLI is an adapter over that authority, not a wrapper around
the author-CI CLI and not a third validator. The existing author CLI continues
to compose static validation with catalog discovery, leak scanning, pack-local
validators and tests, and release-oriented author gates.

Pack-owned checks that are safe and relevant at ingest move into or become
reusable by the shared static authority. The author adapter must not retain a
second copy. Author-workflow checks stay outside it. In particular:

- pack YAML uses the existing strict, bounded loader and packaged schemas;
- all paths and bytes use `_pack_fs.py`'s descriptor-anchored inventory and
  member reads;
- SDL syntax and meaning use public APIs from the exact RAES pin;
- an opted-in content manifest uses `validate_pack_content_manifest()` and the
  RAES associated-artifact validator rather than another digest model;
- publication and capability claims use
  `validate_publication_document()`, compiled requirement-address helpers, and
  trusted RAES backend-profile loading; and
- RAES lock, resolver, trust, and compilation facts are never reimplemented as
  pack schemas or inferred from filenames, prose, provider labels, or command
  success.

The safe consumer command has its own `raes-pack-check` identity.
`raes-pack-validate` remains visibly documented as trusted author CI. Both are
console adapters over shared authorities; their different names prevent an
existing executable workflow from silently changing meaning.

### One structured diagnostic result

The in-process result is the canonical result for every renderer. It carries
ordered, bounded diagnostic records; the current `errors` strings remain a
derived compatibility view rather than a second source of truth.

Each diagnostic has a stable code, severity, domain, owning authority, safe
location, explanation, reason, safe suggestion, and durable documentation
target. A safe location is a canonical pack-relative member plus a field
pointer and, when RAES supplies it safely, a source range. It never echoes an
authored value merely to be “exact.” Domains distinguish at least `pack`, `sdl`,
`compatibility`, and `trust`; ownership distinguishes this package's pack
contract from RAES-owned SDL, lock, trust, artifact, and backend-profile
contracts. Pack provenance/publication clearance and RAES authenticity/trust
are separate diagnostics and never substitute for each other.

RAES structured codes, pointers, ranges, stages, and severities are adapted,
not replaced by parsing exception prose. A bounded presentation catalog may map
known upstream codes to stable beginner-safe explanations and suggestions; that
catalog is presentation metadata, not a semantic validator. Unknown upstream
codes fail closed with a generic bounded diagnostic and retain only safe
structured upstream identity. Raw upstream messages, exception representations,
SDL/YAML bodies, authored identifiers that may be sensitive, absolute paths,
restricted path values, URI query values, environment values, command lines,
and subprocess output do not enter the public envelope.

The JSON document has an explicit envelope version and is serialized directly
from the canonical result. Human output renders the same records. Parity tests
compare the semantic fields, ordering, counts, blocking verdict, and selected
profile context rather than maintaining human-only decisions. JSON mode writes
only the JSON document to stdout; usage and tool failures use stderr.

Diagnostic documentation is keyed by stable code. Renaming prose or moving a
heading must not break its durable target. Representative first-time failure
tasks form a checked corpus, and the actionable-correction acceptance ratio is
computed from that corpus rather than asserted informally.

### Safe by default; capabilities are explicit

The default check is silent at the library layer, networkless, non-executing,
read-only, and free of Git, environment configuration, caches, databases, or
other persistence. It does not import or call `content_ci.main()`, `release`
commands, pack-supplied commands, or pack-supplied Python.

SDL imports remain denied in the default consumer mode until RAES exposes a
resolver policy that can prove lock and trust conformance without network or
cache writes. Lockfile shape may be reported only through a public RAES loader;
shape alone must not be reported as resolved, trusted, or semantically valid.
Network-enabled import resolution is a separate explicit capability from
trusting pack-local code.

Pack-local validators, tests, and manifest-declared commands run only after an
explicit trusted-author request and a successful static filesystem gate. That
mode reuses the existing closed discovery roots, descriptor-anchored execution
snapshot, argv-only process runner, process-group deadline, and hard output
budget. It is not a sandbox. The runner's execution context must make ambient
environment inheritance an explicit policy; the safe default is a minimal
environment, and secret values or document bodies are never placed in argv or
diagnostics. Raw child output is not part of the machine-readable diagnostic
contract.

Safe fixes are a separate explicit write capability. A fix is offered only for
a stable diagnostic code when the edit is deterministic, semantics-neutral, and
does not assert author intent, provenance approval, trust, compatibility, or
RAES meaning. Fixes use the same no-follow containment and resource boundaries,
verify the original member identity before replacement, write with fixed safe
permissions, and re-run the complete check over the resulting bytes. An unsafe
inventory, ambiguous edit, changed member, or failed recheck stops the write
path. A generic plugin, hook, command, or arbitrary patch facility is not
introduced.

### Compatibility is projection, not probing

A selected RAES backend profile is resolved only from the trusted profile corpus
shipped by the exact pin. Selection is an identifier, never an arbitrary file
path or executable. The check projects only declared and evidenced facts:
RAES-authored artifact requirements, publication capability claims, profile
required contracts, and pack-owned compatibility rows. It never contacts or
starts a backend or adapter, inspects the host, or treats a profile name as
evidence of a concrete capability.

Pack-local `runtime_profiles[].profile_id` values and RAES backend-profile ids
are different namespaces. They are not joined by equal spelling. A relationship
exists only when a canonical declaration explicitly supplies it. An absent
declaration is reported as unknown/not declared, not inferred as compatible or
incompatible.

Compilation diagnostics may be added only through a public RAES API or tool.
Because the pinned release has no such surface, the pack checker must not ship a
local compiler, inspect private RAES modules, or label parsing as compilation.
The extension seam is a reviewed exact-pin advance plus a narrow adapter over
the new public upstream result.

### Stable process contract

The command uses these exit statuses:

- `0`: the requested static checks completed with no blocking diagnostic;
- `1`: the check completed and found one or more blocking authoring problems;
- `2`: invalid invocation, selector, output option, or disallowed capability;
  and
- `3`: the checker or an owning upstream authority was unavailable or failed
  unexpectedly.

Warnings do not change a successful status. Trusted-author failures are ordinary
blocking diagnostics only when that mode was requested. Unexpected programming
defects are not mislabeled as invalid pack content; the CLI returns the tool
failure status with a bounded, payload-free message.

## Consequences

- Editors, CI, Hub, and MCP adapters can consume one deterministic result without
  scraping console text. Those outer systems retain their own authentication,
  authorization, immutable staging, and persistence boundaries.
- Existing public callers retain the compact `errors` view while richer clients
  consume structured diagnostics.
- Static validation grows by composition from current validators. It does not
  absorb release building, catalog workflow, or pack execution.
- A clean-install test must exercise the installed command and packaged
  resources against the canonical quickstart pack. The normal unittest,
  content/release, compile, schema-convention, package-metadata, and CLI-coverage
  gates remain the repository verification path.
- Full compilation diagnostics are blocked on a public RAES surface. That gap is
  raised upstream rather than hidden behind local semantic code.

## Non-goals

This decision does not add acquisition, archive extraction, authentication,
authorization, registry or catalog persistence, backend discovery, host
inspection, port or credential checks, runtime readiness, lifecycle control,
launch, teardown, materialization, cost-incurring work, or telemetry. It does
not prove a concrete backend is healthy or capable, infer undeclared
compatibility, execute pack code by default, make arbitrary pack code safe,
define a generic validator/plugin API, host a pack, or extend RAES SDL,
compilation, artifact, trust, lock, backend, or diagnostic semantics.
