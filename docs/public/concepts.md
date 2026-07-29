# What an environment pack is

An environment pack is the declarative content for one reference environment,
packaged so it can be shared, validated, and shipped. It is the reusable content
for a scenario — not the engine that runs it, and not a live range.

You author a pack. A catalog stores it. A runtime realizes it. This page explains
those pieces and where each one's authority ends.

## What is in a pack

A pack is a directory with a required core and optional layers.

The core every pack carries:

- **`pack.yaml`** — the pack's identity and metadata: its name, title, version,
  and status, plus pointers to the files below.
- **A scenario start state** — one or more RAES SDL documents under `sdl/`, the
  authored description of the environment.
- **A provenance ledger** — `docs/provenance-ledger.yaml`, the record of where
  the content came from, its licensing, and its content-safety attestations.

Optional layers a pack adds when it needs them: a flag and challenge layer for
capture-the-flag content, a reference triangle (`build/`, `tests/`,
`docs/walkthroughs/`) that proves the environment stands up and behaves as
described, and delivery profiles for different audiences.

The [pack reference](environment-packs.md) walks through each of these. The exact
field-by-field contract ships inside the package, in
`contract/pack-layout.md` — that file is the normative source; the docs explain
it.

## Who owns what

Three parties meet at a pack, and keeping their jobs separate is what makes a
pack portable.

- **RAES owns the meaning.** The scenario language (SDL), its objectives,
  evidence, and participant behavior belong to [RAES](https://github.com/RAESystem/rae).
  This repository consumes them from a pinned `raes` release and adds nothing to
  them.
- **This repository owns the format.** It defines how a pack is laid out,
  authored, validated, and released — and the tools that enforce that. It owns
  the *shape* of a pack, never the content of any particular one.
- **Catalogs own the packs.** Actual packs live in their own catalog
  repositories and consume this format. This repository hosts none.

A fourth party, the runtime, turns a pack into a live environment. The
[ownership boundary](ownership-boundary.md) sets out that full four-way split and
what each side may not decide for the others.

## Why validation matters

A pack is content you receive from somewhere else, so trusting it blindly is a
risk. Validation is how you check a pack matches the contract before you use it.

There are two checks, for two situations:

- **Consuming a pack**, [`validate_pack`](validating.md) reads one staged pack
  and returns bounded, body-free diagnostics. It never runs the pack's code,
  opens a network connection, or writes anything. Use it at an ingest boundary,
  on content you do not yet trust.
- **Authoring a pack**, `raes-pack-validate` runs the fuller author checks in a
  repository you control. It may run the pack's own validators and tests, so it
  is for trusted checkouts only.

Both check the start state through the same pinned `raes` parser, so a
self-contained start state gets the same verdict from either. They are not
identical, though: the consumer boundary runs without a file context and rejects
SDL that imports other files, while the author CLI can resolve those imports. The
consumer boundary is the stricter of the two.

## Next

- [Validate your first pack](quickstart.md)
- [The pack reference](environment-packs.md)
- [What this is and is not](limitations.md)
