# ADR 0046 — Admit pinned local imports through RAES supplied sources

- Status: Accepted
- Date: 2026-10-31
- Amends: the import-denial clause of
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md) and the
  consumer clause of
  [ADR 0035](0035-compose-catalog-kits-through-raes-and-transactional-pack-projections.md)
- Raises: the RAES floor of [ADR 0043](0043-require-a-minimum-raes-version.md)
- Coordination: OpenRAE/env-packs issue 412, OpenRAE/rae issue 1757

## Context

`raes-pack-kit add` writes a `local:` import with a digest pin into the target
SDL document. It also writes `raes.lock.json` beside that document.
`validate_pack()` denied every SDL import, so it rejected every pack made from kits.

ADR 0013 kept that denial until RAES supplied a resolver-policy seam.
RAES 10.2.0 supplies it as `parse_sdl_sources()` (RAES ADR-119):

- It reads only the bytes that the caller supplies.
  It reads no file, environment variable, network resource, or `raes-trust.yaml`.
- It admits only `local:` imports, at each depth.
- Each import must have a `sha256:` digest pin.
  It must match one agreeing record in the `raes.lock.json` beside its importing document.
- It refuses an import with `SDLImportError`, which carries a stable code.

The kit tool wrote each lock from one target document only.
Two SDL documents in one directory share one lock,
so a kit change to one document removed the records of the other.

## Decision

- The consumer parses each direct `sdl/*.sdl.yaml` document through `parse_sdl_sources()`.
  `validate_pack()`, the catalog projection, `raes-pack-check`, and
  `resolve_pack_artifact()` share this parse.
- The supplied set contains each `*.sdl.yaml` and `raes.lock.json` member below `sdl/`.
  The descriptor-anchored pack reader reads each member one time.
  The set excludes sensitive members.
- The total size of the supplied set must not exceed `limits.sdl.max_composed_bytes`.
- An `SDLImportError` becomes `sdl.imports-denied` at the importing document and import pointer.
  The diagnostic does not copy RAES message text.
- RAES refuses a root that carries `materialization_provenance` with `sdl.import.phase-refused`.
  Such a root has no imports, so the consumer parses it with content-only `parse_sdl()`.
- The consumer does not match exception message text.
- The kit tool writes one lock for each directory.
  The lock holds the records of each SDL document in that directory.
- `raes>=10.2.0` is the RAES floor.
- The author parser and `raes-pack-validate` do not change.

## Consequences

- A pack made with `raes-pack-kit add` passes the consumer check.
- A registry, network, `locked:`, unpinned, or unlocked import fails with `sdl.imports-denied`.
- The consumer check stays inert.
  It starts no subprocess, opens no network connection, and reads no environment variable.
- A pin and a lock record prove that the pack is consistent.
  They do not prove trust or authorization.
- Consumers still stage a pack immutably and promote the same bytes.
