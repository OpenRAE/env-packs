# Scaffold a pack

`raes-pack-new` is a progressive wizard. It scaffolds a new pack into the
`environments/` tree of your catalog repo, generating only the files your goal
needs, previewing them first, and validating the result with the same static
check consumers run — so you reach a valid pack without reading the template
doctrine first.

Run it from your catalog root and pick a starter route:

```sh
raes-pack-new example-pack --route minimal --yes
```

```
created environments/example-pack
validated with the static pack check (minimal route)
```

## Starter routes

Each route is a preset over pack-file selection — not a scenario type. Defaults
stay domain-neutral; only a route that genuinely needs it adds offensive or
live-fire content.

| Route | Adds beyond the minimal required files |
|---|---|
| `minimal` | Nothing — identity, a start state, and the docs to understand it. |
| `runnable-local` | Reference triangle: build, tests, and matching walkthrough. |
| `ai-agent-eval` | Delivery bundles for an agent-benchmark contract. |
| `security-exercise` | Flags, challenges, and a reference CTFd loader. |
| `dr-recovery` | Reference triangle to build and rehearse a recovery drill. |
| `product-integration` | A compatibility projection for product/backend consumers. |
| `publication-ready` | The compatibility projection needed to package a release. |

Add an optional layer to any route with `--with` (repeatable):

```sh
raes-pack-new example-pack --route minimal --with compatibility --yes
```

## Preview first

Preview shows the exact file set and the assumptions the wizard made. It is
side-effect free — it creates nothing:

```sh
raes-pack-new example-pack --route security-exercise --preview
```

## Answer the questions

Run without `--yes` for the interactive flow. Every question states the
consequence of its answer and offers a safe default or an explicit "not sure".
A "not sure" stays visible and, where an owning contract needs a resolved value
(for example, confirming a publication-ready pack is cleared to publish), it
blocks the write rather than asserting a claim you did not make.

Answer a question non-interactively with `--answer key=value` (repeatable). For
example, a publication-ready pack needs its clearance confirmed:

```sh
raes-pack-new example-pack --route publication-ready \
  --answer publication_cleared=yes --yes
```

## Automation (Hub, MCP, CI)

Drive the wizard non-interactively with a versioned wizard-input document on
stdin, and read the machine result on stdout:

```sh
echo '{"version":"raes-pack-wizard-input/v1","pack_id":"example-pack","route":"minimal"}' \
  | raes-pack-new --replay - --json
```

Equal inputs plus the same package and RAES versions produce byte-identical
packs. The wizard writes into an **absent** target only — it never overwrites,
merges into, or deletes an existing pack.

## What the wizard delegates

The wizard owns pack **structure and identity**, not scenario semantics. The
start state it generates carries only the scenario name (equal to the pack id),
formatted and validated by RAES itself — the wizard invents no nodes, node
types, or topology, and defines no second SDL schema. Author the environment's
nodes and behaviour afterward with the RAES SDL tools; RAES-owned scenario
completion and compilation are likewise not part of the wizard.

After scaffolding, edit the generated `pack.yaml`, replace the placeholder prose
in `docs/`, author the SDL start state, and grow the pack with the optional
layers above.
