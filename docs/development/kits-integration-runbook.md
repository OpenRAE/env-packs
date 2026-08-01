# Infrastructure-kit integration runbook

End-to-end author proof for infrastructure kits (`raes-pack-kit`, issue #190).
The unit suite covers schema admission, discovery, proposal construction,
conflict diagnostics, ownership, atomic mutation, and failure recovery. This
runbook drives the real shipped command modules against the released kit
collection in an explicitly staged local catalog checkout.

The harness is deliberately outside `tests/`, so normal CI does not require a
second repository. It does not acquire content, call a registry, execute kit
code, or touch a backend.

## What it proves

- A minimal pack can list, search, and inspect the complete initial 38-kit
  collection.
- Preview is side-effect free and exposes ordinary files, topology, assumptions,
  dependencies, and RAES lock changes without parameter values.
- Five identity, endpoint, network, application, and data kits compose into one
  ordinary pack with exact materialization provenance, a RAES lock, and a
  RAES-validated associated-artifact set.
- Trusted author validation passes after composition.
- Parameter update, remove-plus-add replacement, and explicit-ownership removal
  each commit one complete successor.
- The final editable pack passes author and release validation without an
  interactive interface or kit runtime.

## Run it

Check out the admitted kit catalog locally, then from this repository root run:

```sh
.venv/bin/python tests_integration/kit_author_walkthrough.py \
  --catalog ../reference-packs
```

The harness derives the current catalog commit as its immutable source revision.
For an archive or other immutable staging directory without Git metadata, pass
the admitted revision explicitly:

```sh
.venv/bin/python tests_integration/kit_author_walkthrough.py \
  --catalog /staging/reference-packs \
  --source-revision sha256:0123456789abcdef
```

Expected tail:

```text
25 passed, 0 failed
```

Exit status is zero only when every command and invariant passes. The harness
sets `PYTHONPATH` to the working tree's `src/`, so it exercises the current
implementation without reinstalling it.

## What it does not prove

This is authoring and static composition evidence. It does not provision a host,
start a service, qualify a backend, generate runtime evidence, or claim that a
particular realization can satisfy a kit-derived RAES scenario.
