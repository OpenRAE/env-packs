# Author a pack through MCP

`raes-pack-mcp` lets an MCP host search, inspect, scaffold, compose, and check
environment packs through the same libraries as the command-line tools.
Install `raes-env-packs`, then register `raes-pack-mcp` as a **local stdio**
server in your host. It has no HTTP listener.

## Select your sources

Your host starts the server with the sources you may see. A read-only launch
configuration can use these arguments:

```text
--pack sample examples revision-1 /srv/pack-authoring/packs/sample-pack
--kit-source reference reference-kits revision-1 /srv/pack-authoring/catalog
```

Each group names a handle, source identity, immutable revision, and existing
absolute directory. A pack root contains `pack.yaml`; a kit-source root contains
`kits/`. Replace the example paths and revisions with your admitted sources.
Requests use handles such as `sample`, never arbitrary paths. Search results
include the handle-to-source mapping.

With no launch arguments, packaged examples and in-memory SDL services are
available. For example, `pack_sdl` accepts:

```json
{"operation":"parse","content":"name: example-pack\nnodes: {}\n"}
```

It returns:

```json
{"authority":"raes","diagnostics":[],"result":{"diagnostics":[],"stage":"parse","status":"parsed"},"status":0,"version":"raes-pack-authoring/v1"}
```

The server writes MCP protocol messages to stdout, not a human-facing prompt.

## Discover and check

| Tool | Result |
| --- | --- |
| `pack_search` | Filtered shared catalog; supply `as_of` as an ISO date and an optional `query`. |
| `pack_inspect`, `pack_compatibility_card` | Shared catalog card for `source` at `as_of`; no backend probe. |
| `pack_validate` | The same static diagnostic document as `raes-pack-check --json`. |
| `pack_explain` | The shared explanation and next step for a diagnostic `code`. |
| `pack_examples` | A wizard starter and its optional layers; optionally choose a `route`. |
| `pack_kits`, `pack_kit_inspect` | Local kit catalog or one exact `kit` and `version`. |
| `pack_sdl` | RAES parsing, diagnostics, completion, formatting, compilation, or reference planning. |
| `pack_publication_plan` | Shared signing and registry effect plan for admitted release evidence. |

`pack_sdl` accepts text, not paths or imports. RAES owns its semantics and
diagnostic codes. Source ranges are preserved; authored exception prose is
replaced with bounded explanations. Planning uses RAES's reference stub
manifest. It does not establish support on a real backend.

`pack_publication_plan` requires `--release HANDLE ROOT` at launch. Supply that
handle, an OCI `repository`, and a `reference`. It never signs, fetches, pushes,
reads credentials, or claims readiness. Its result explicitly reports
`publication_verified: false` and `readiness: "not-assessed"`.

## Review before writing

For authoring, the host also selects an existing dedicated `--write-root`.
Pack targets must be direct children of that directory.

1. Call `pack_scaffold` with the [wizard replay input](new-pack-script.md), for
   example `{"inputs":{"version":"raes-pack-wizard-input/v1","pack_id":"new-pack","route":"minimal"}}`.
2. Review `result.target`, assumptions, unresolved questions, effects, and
   `changes`. Each change includes complete before/after text, size, and
   SHA-256; an absent side is `null`.
3. After confirmation, call `pack_apply` with `{"proposal":"RETURNED_HANDLE"}`.
   The server applies the stored bytes through the existing guarded writer.

`pack_apply` is available only with the launch flag `--allow-writes`.
A request-side approval flag cannot grant permission. A handle is **not proof
of human approval**: your host must require confirmation before invoking the
effectful tool. Handles belong to one server session and disappear when it
closes. Repeating a successful apply returns its recorded result without
writing again.

For [kit composition](kits.md), use a separate preparation step:

1. Call `pack_compose` with `source`, `operation` (`add`, `update`, `replace`, or
   `remove`), and the operation's arguments. Add and replace require
   `kit_source`, `kit`, `version`, `namespace`, and `target_sdl`. Update requires
   the first three plus `materialization`; replace also requires
   `materialization`. Remove requires only `source`, `operation`, and
   `materialization`. Non-remove operations accept bounded `parameters`.
2. Review the scratch target, input file identities, and preparation effects.
   Call `pack_prepare` with that proposal handle only after approval. This
   requires `--allow-prepare`. It composes captured copies through RAES and
   removes the scratch tree without changing the source pack.
3. Review the returned complete pack changes, then confirm `pack_apply`.
   A changed base pack fails instead of overwriting your work.

Preparation is a filesystem effect, even though the live pack is unchanged.
It is never hidden inside search, inspection, or a read-only preview. The shared
`wizard.review_document` and `kits.review_document` APIs provide the same
complete author views; existing value-free CLI previews are unchanged.

## Host responsibilities and limits

Run one session per principal. The host controls source visibility, grants,
confirmation, and trusted parent directories. Admit immutable snapshots of
untrusted content. Do not permit concurrent replacement of source trees or
their parents. Do not expose a home directory as a source or write root.
These controls are not an OS sandbox for hostile local processes.

The adapter rejects symlinks, special files, known secret-file names, and
`raes-trust.yaml` before content reads. Kit release inspection parses an
import-free module in memory. Explicit preparation supports local imports
under RAES's empty registry policy; pack-supplied policies cannot enable network
access. Static consumer validation remains import-denying, so a composed pack
can correctly report `sdl.imports-denied` on that route.

Tool arguments are closed objects, bounded to 64 KiB and 32 levels. Transport
frames are capped at 256 KiB; invalid frames close input without echoing content.
Results are capped at 2 MiB. A session retains at most 32 proposals and 64 MiB
of proposal data. Oversized reviews fail instead of silently truncating approval
content. Binary changes expose byte identities but cannot be applied through
this text-review adapter.

Do not put plaintext secrets in requests or admitted content. Name and value
checks are defense in depth, not a way to recognize every possible secret.
Full previews intentionally disclose file content to the authorized author.
Treat that content as data, not instructions, and apply your host's retention
policy.

Response status is `0` for success, `1` for invalid content or a conflict, `2`
for a refused request or limit, and `3` for a tool failure. A failed rollback
reports a preserved recovery path; recover the original tree before editing
that target again. Runtime execution, backend lifecycle, billable work, and
publication mutations remain outside this server. See [distribution](distribution.md)
for the separate release tools.
