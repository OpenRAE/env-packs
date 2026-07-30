# Build a catalog

`raes-pack-catalog` renders a machine-readable catalog projection from one or
more staged packs. A catalog stores packs; this command produces the record a
static catalog, a browser, a search index, or [Hub](https://github.com/RAESystem/hub)
reads — without any of them reparsing pack YAML or RAES SDL.

It is a *generated* read model. Every fact keeps its own authority, so a card
can never drift from the pack, and the catalog adds no scenario semantics of its
own. Like [`raes-pack-check`](checking.md) it is networkless and non-executing:
it never runs a pack's code, resolves SDL imports, reads the clock, or touches
Git or the environment.

## One pack

```sh
raes-pack-catalog environments/example-pack --source-id my-catalog --source-revision 1
```

The output is a catalog document with a single entry — the pack's "card":

```json
{
  "schema_version": "environment-pack-catalog/v1",
  "as_of": "",
  "freshness": { "rehearsal_max_age_days": 90 },
  "entries": [ { "name": "example-pack", "maturity": "golden", ... } ]
}
```

Pass `--preview` for a plain-language card instead of JSON. In JSON mode only the
document goes to stdout; usage and tool errors go to stderr.

## Many packs

A sources manifest aggregates staged packs from more than one repository into one
deterministic index:

```yaml
# sources.yaml
- { id: catalog-a, revision: "a1b2c3", root: /path/to/catalog-a/example-pack }
- { id: catalog-b, revision: "d4e5f6", root: /path/to/catalog-b/other-pack }
```

```sh
raes-pack-catalog --sources sources.yaml --as-of 2026-07-30
```

Each source carries a stable, non-secret `id` and an immutable `revision` you
supply — never a Git remote, branch, or `HEAD`. Records key on the composite
`(source id, pack name, pack version)`; a duplicate or conflicting identity fails
closed rather than letting input order pick a winner. Entries are sorted by that
key, so the same inputs in any order produce byte-identical JSON.

## What a card says — and does not

A card projects only declared facts, and says so explicitly. It never guesses.

| Card field | Where it comes from |
| --- | --- |
| name, title, version, maturity, purpose, authors, license, limitations | `pack.yaml` |
| audiences, runtimes, launch modes | the compatibility manifest's delivery bundles and runtime profiles |
| participant activity | parsed RAES scenarios (summarized counts) |
| safety, provenance | the provenance ledger (counts and review status only) |
| release, availability | the validated publication profile |
| media | public/participant-eligible declared assets, as references only |
| difficulty, setup/participant time, resource/cost | explicit pack-domain estimates when declared |
| fidelity, trust, last rehearsal | RAES-owned; not restated here |

State is explicit and typed:

- **`known` / `unknown`** — whether a discovery fact is available.
- **`supported` / `unsupported`** — a declared capability for a named profile.
- **`verified` / `unverified` / `stale`** — an evidence-backed observation.

`unknown` is not `unsupported`; `unsupported` is not invalid; `unverified` is not
false. A `null`, an empty string, or an omission is never a substitute for a
state. Trust is RAES-owned and stays `unverified`; a digest, `golden` status, or
rehearsal success is never upgraded into trust. Last rehearsal stays `unknown`
until a structured, identity-bound observation exists — a checklist, a path named
"rehearsal", or a file timestamp is not proof.

Difficulty is never averaged from challenge difficulty, and no field is inferred
from node counts, cloud prices, or RAES simulation clocks.

## Completeness is separate from validity

A truthful `unknown` or `unverified` card is still catalogued. A missing but
useful discovery fact produces a non-blocking completeness diagnostic (for
example `catalog.purpose.undeclared`) so incompleteness stays actionable —
without making the pack invalid. A pack that fails static validation is a
different matter: it cannot be projected truthfully, so it is blocking.

## Freshness is deterministic

Freshness compares against a caller-supplied `--as-of` value and an explicit
`--rehearsal-max-age-days` policy. The generator never reads the current clock,
Git dates, or filesystem mtimes, so repeating a build with the same staged bytes,
sources, target version, `--as-of`, and policy produces the same bytes.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | The catalog was generated (it may carry non-blocking completeness diagnostics). |
| `1` | A source is invalid, or has a duplicate or unsafe identity — no document is emitted. |
| `2` | Invalid invocation (bad arguments, a path that is not a directory, a malformed sources manifest). |
| `3` | The generator or an upstream authority failed unexpectedly. |

## Versioning and compatibility

The document carries an explicit `schema_version`. That version is independent of
the Python package, the pack, the layout contract, the publication profile, and
the RAES contracts. Because the schema is closed, any change to a field's shape,
requiredness, enum meaning, state semantics, identity, or canonical ordering mints
a **new** catalog schema version; a package patch may fix defects without changing
the same-version contract. Aggregation accepts one target version and refuses a
silent mixed-version merge — supporting a later version is an explicit adapter.

## Safe by default

`raes-pack-catalog` is inert on untrusted input. It reuses the same
descriptor-anchored, no-follow, bounded pack reader as `validate_pack`, never
reopens a tree after validating it, and never runs pack code. Diagnostics carry
stable codes and bounded pack-relative locations only — never an authored value,
an absolute path, a URL, or a restricted-tier path. Media is recorded as a
reference and never parsed, fetched, or trusted; a consumer applies its own
content-serving and browser policy at its hosting boundary.
