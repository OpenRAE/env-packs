# Check a pack

`raes-pack-check` statically checks one environment pack and explains every
blocking problem in plain language. It is the beginner-safe front door to the
same `validate_pack` contract described in [validating a pack](validating.md):
it never runs the pack's code, never touches the network, and reads only the
staged files.

```sh
raes-pack-check environments/example-pack
```

```
pack: example-pack
OK — no blocking problems found.
```

When something is wrong it names the problem, where it is, why it matters, and
how to fix it:

```
pack: example-pack
FOUND 1 blocking problem:

[trust] provenance.name-mismatch  (owner: env-packs)
  where: docs/provenance-ledger.yaml:pack.name
  what:  The ledger's pack.name does not match the pack's name.
  why:   The ledger must describe this pack, not another one.
  fix:   Set pack.name in the ledger to match name in pack.yaml.
  docs:  docs/public/checking.md#trust-and-provenance
```

## JSON output

Pass `--json` for a machine-readable envelope — the same result, expressed for
scripts, editors, CI, Hub, and MCP delegation. Only the JSON document goes to
stdout; usage and tool errors go to stderr.

```sh
raes-pack-check environments/example-pack --json
```

```json
{
  "version": "raes-pack-check/v1",
  "ok": false,
  "pack": "example-pack",
  "summary": { "total": 1, "by_domain": { "trust": 1 } },
  "diagnostics": [
    {
      "code": "provenance.name-mismatch",
      "severity": "error",
      "domain": "trust",
      "owner": "env-packs",
      "location": "docs/provenance-ledger.yaml:pack.name",
      "file": "docs/provenance-ledger.yaml",
      "field": "pack.name",
      "explanation": "The ledger's pack.name does not match the pack's name.",
      "reason": "The ledger must describe this pack, not another one.",
      "suggestion": "Set pack.name in the ledger to match name in pack.yaml.",
      "doc": "docs/public/checking.md#trust-and-provenance"
    }
  ]
}
```

The human and JSON forms carry the same findings, in the same order, with the
same verdict. Each diagnostic is a stable `code`, a bounded pack-relative
`location`, and a beginner-safe explanation — never a file body, an authored
value, or an absolute path.

## Exit codes

The exit status is a stable contract:

| Code | Meaning |
| --- | --- |
| `0` | Valid — no blocking problems. |
| `1` | The check ran and found one or more blocking problems. |
| `2` | Invalid invocation (bad arguments, or the path is not a directory). |
| `3` | The checker or an upstream authority failed unexpectedly. |

Exit `3` is deliberately distinct from `1`: an internal fault is never reported
as an invalid pack.

## What each domain means

Every diagnostic names a **domain** — the kind of problem — and the **owning
component** responsible for the contract it failed.

### Pack layout

`pack`, `yaml`, `filesystem`, `resource`, and `challenges` codes. The pack's
identity (`pack.yaml`), its file shapes, and its size bounds. Owned by
**env-packs**: this package defines the pack layout. Fix the pack's manifest or
files.

### Trust and provenance

`provenance` codes. The provenance ledger — the pack's origin, licensing,
content-safety attestations, and publication review gates. Owned by
**env-packs**. RAES owns cryptographic *trust* separately; a provenance
clearance is not an authenticity claim.

### Compatibility

`compatibility` codes. The optional `pack.compatibility.yaml` manifest: its
schema and the visibility-boundary invariant that keeps hidden-tier content out
of participant exports. Owned by **env-packs**. The manifest *declares* the
backend and runtime surfaces a consumer can rely on; the check validates the
declaration without contacting or starting any backend.

### SDL and RAES

`sdl` codes. Every `sdl/*.sdl.yaml` start-state document, parsed through the
pinned `raes`. Owned by **RAES**: it is the sole authority for SDL syntax and
meaning. By default the check denies SDL imports (`sdl.imports-denied`) because
resolving them can reach the network.

## Safe by default

`raes-pack-check` is inert on untrusted input. It never runs a pack's own
validators, tests, or commands, and never resolves SDL imports. Running a pack's
validators and tests is the trusted-author job of
[`raes-pack-validate`](validating.md), which you run only on a checkout you
control. Selecting a live RAES backend profile to project compatibility against,
and applying safe automated fixes, are explicit capabilities reserved for a
later release (ADR 0031); today each diagnostic carries a manual fix suggestion.
