# Validate a pack

You have a pack from somewhere else and want to check it before you use it. Call
`validate_pack` on the staged pack directory. It returns a result you can act on
and prints nothing.

```python
from raes_env_packs import validate_pack

result = validate_pack(pack_root)
if not result.ok:
    reject(result.errors)
```

`result.ok` is `True` when `result.errors` is empty. Each error is a short,
bounded code with at most a pack-relative filename and a field path — for example
`provenance.name-mismatch: docs/provenance-ledger.yaml:pack.name`. Errors never
contain file bodies or absolute paths, so you can log them safely.

Prefer a command line? [`raes-pack-check`](checking.md) wraps this same call and
explains each problem in plain language (or JSON), with documented exit codes.

## What it checks

`validate_pack` reads the static contract for one pack:

- the pack's identity in `pack.yaml`, including that the name matches the
  directory;
- the required provenance ledger — its schema, its matching pack name, its
  content-safety attestations, and its review gates;
- the referenced compatibility manifest, if the pack has one;
- every `sdl/*.sdl.yaml` start-state document, parsed through the installed
  `raes`;
- any concept bindings beside an SDL document (`sdl/<name>.bindings.json`),
  resolved against its pinned schemes (`sdl/<name>.schemes.json`). A binding
  that no longer resolves fails with `sdl.bindings-unresolved`; and
- any experiment artifact set in `experiments/`, admitted through RAES and
  joined to its scenario family (see
  [experiments](environment-packs.md#experiments)).

## What it will not do

`validate_pack` is the boundary for content you do not yet trust, so it is
deliberately inert. It does not run the pack's code, start a subprocess, open a
network connection, read environment variables, write a cache, or log.

It admits an SDL import only when all of these are true:

- the import is `local:` and names an `sdl/` file in the pack;
- the import has a `sha256:` digest pin of the module bytes; and
- one matching record is in the `raes.lock.json` beside the importing document.

`raes-pack-kit add` writes imports and locks in this form. Every other import,
such as a registry or network import, fails with `sdl.imports-denied`. The
check never fetches it.

Because it works on files, it cannot make storage atomic for you. Stage the pack
immutably first, validate those exact bytes, then promote the same bytes — and
revalidate before use if your storage does not already guarantee that.

You can bound what it reads:

```python
from raes_env_packs import PackValidationLimits, validate_pack

result = validate_pack(
    pack_root,
    limits=PackValidationLimits(max_metadata_bytes=512 * 1024),
)
```

## Two validation surfaces

There are two checks, and they trust their input differently.

| | `validate_pack` (this page) | `raes-pack-validate` |
| --- | --- | --- |
| For | consuming a pack | authoring a pack |
| Trust | untrusted input | a checkout you control |
| Runs pack code? | never | may run the pack's validators and tests |
| Output | a returned result, silent | a printed CI report |

Use `validate_pack` at an ingest boundary. Use `raes-pack-validate` in your own
catalog CI, where running the pack's tests is safe and expected. Both parse the
start state through the same installed `raes`, so a self-contained start state gets
the same verdict from either. They are not identical: `validate_pack` admits only
pinned and locked local imports, while `raes-pack-validate` can also resolve other
imports. The consumer boundary is the stricter.

## Proving which bytes a pack is

A pack can also carry a content identity, so a consumer can prove which exact
bytes an identity covers. The public API keeps authoring separate from
verification:

```python
from raes_env_packs import (
    derive_pack_content_manifest,   # author/release: record the identity
    validate_pack_content_manifest, # consumer: the shipped manifest agrees with the bytes
    pack_content_digest,            # the validated set digest
    verify_pack_content_digest,     # validate first, then compare to an expected digest
)
```

RAES owns the identity model; this package resolves the pack's files and hands
the bytes to RAES. See the [pack reference](environment-packs.md#content-identity)
for how identity, trust, and scenario meaning stay separate claims.

## Reading one artifact's bytes

Once a pack validates, a consumer can turn a single associated-artifact id into
its bytes plus a canonical identity — without re-implementing URI parsing,
inventory, or checksums:

```python
from raes_env_packs import resolve_pack_artifact

resolved = resolve_pack_artifact(pack_root, "artifact-2")
resolved.data              # the artifact's immutable, digest-verified bytes
resolved.identity          # canonical RAES ArtifactIdentity
resolved.identity.digest   # "sha256:…", provably the identity of resolved.data
```

`resolve_pack_artifact` accepts either an opaque artifact id or the upstream
associated-artifact descriptor (which must match its manifest entry — it cannot
override the recorded uri, size, checksum, or media type). It opens the selected
file once, binds its bytes against the validated manifest, and returns them with
the identity `version` fixed to the pack version — so consumers never choose the
version rule locally. It resolves nothing over the network and never falls back
to an ambient path; failures raise `PackDigestError`.

This is the post-validation byte-open step, not a replacement for it: keep
running `validate_pack()` / `validate_pack_content_manifest()` first, and supply
an immutably staged pack root.

## Loading an experiment

A pack can carry RAES experiment documents in `experiments/`. Load them after
the same static check:

```python
from raes_env_packs import PackExperimentError, load_pack_experiments
from raes_processor.trial_compiler import compile_admitted_trial_plan

try:
    experiments = load_pack_experiments(pack_root)
except PackExperimentError as exc:
    reject(exc.result.errors)

for experiment in experiments:
    request = experiment.compilation_request(
        apparatus=apparatus,
        apparatus_manifests=apparatus_manifests,
        realization_envelope=envelope,
        execution_authority=authority,
        participant_manifests=participant_manifests,
        participant_configuration_validators=validators,
    )
    result = compile_admitted_trial_plan(request)
```

Each `PackExperiment` holds the RAES-validated authoring input, its task, its
capture specifications, and the admitted scenario family. The apparatus
arguments are your trusted context. The RAES trial compiler checks them and
every requested combination. It returns a plan or bounded diagnostics, and one
invalid combination rejects the whole design.
