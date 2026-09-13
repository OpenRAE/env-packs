# ADR 0038 — Ship RAES concept bindings beside pack SDL

- Status: Accepted
- Date: 2026-09-13
- Extends: ADR 0011 (pinned RAES SDL validation),
  [ADR 0013](0013-separate-consumer-static-validation-from-author-ci.md), and
  [ADR 0014](0014-consume-aces-concept-authority.md)
- Coordination: OpenRAE/env-packs issue 347; OpenRAE/rae issue 989

## Context

RAES 4 removed classification fields from SDL, including `vulnerabilities`,
route `vulnerability_refs`, and behaviour-specification tactic refs. A
classification is now an `external-concept-bindings/v1` document. Each binding
names one exact SDL subject, pinned to the SDL's canonical digest, and one
concept in a pinned scheme. RAES resolves bindings only against scheme
snapshots it is given; it never fetches a catalog.

The pack format had no place for these documents. Without one, a pack either
loses its classifications or ships them where no consumer checks them.

## Decision

- `sdl/<name>.bindings.json` holds the bindings for `sdl/<name>.sdl.yaml`.
- `sdl/<name>.schemes.json` is a JSON list of the scheme snapshots those
  bindings resolve against. Bindings without schemes are invalid.
- `validate_pack` parses both through the RAES contract models and admits the
  bindings with `admit_external_concept_bindings` against the parsed SDL. Any
  result other than `resolved-current` fails with
  `sdl.bindings-unresolved`. Malformed, schemeless, and orphaned documents
  fail with `sdl.bindings-invalid`, `sdl.bindings-schemes-missing`, and
  `sdl.bindings-orphan`.
- A scheme snapshot pins a real source by revision, locator, and digest. A
  label string such as `CWE-89` is not a pinned source.
- `tools/refresh_pack_sdl_binding.py` retargets bindings whose subject still
  exists after an SDL edit, then rebinds the manifest. It never retargets a
  binding whose subject is gone.

## Consequences

- Consumers check classifications with the same static check they already run.
- Any semantic SDL edit makes bindings stale until the author runs the refresh
  tool. That is the intended signal: a binding is a claim about one exact SDL.
- TechVault's webapp weaknesses are CWE 4.20 bindings on their routes. Each
  weakness is also described in its route's own description.
